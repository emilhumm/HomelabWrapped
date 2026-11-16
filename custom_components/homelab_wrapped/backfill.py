"""Looking back over the recorder's states when Wrapped starts counting something.

Each of Wrapped's sensors is looked back for once (see ``core.backfill``): the
recorder's states of its sources, from as far back as the recorder keeps them up
to when the sensor was created. What is found is kept in
``.storage/homelab_wrapped.backfill`` by the sensor's unique id, and the cards add
it to what the sensor counted itself.

Kept light on a live HA:

- it starts a minute after HA has started, as a background task cancelled on unload;
- one source and one week at a time, in the recorder's executor, reading value
  changes only (no attributes, except a media player's: what it played); the
  states are made sense of there too;
- uptime counters HA keeps long-term statistics for aren't read: the cards have
  their whole history already;
- what was found is saved once, when the look-back is done;
- a failure is logged and tried again after the next start, never raised, and a
  damaged file only means looking back again.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import partial
import logging
from typing import Any

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.history import state_changes_during_period
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import CoreState, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DNS_READ_AT, DOMAIN
from .core.backfill import Backfilled, CutFinder, DailyReader, PlayTimer, RestartFinder, combine

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
SETTLE = timedelta(minutes=1)
"""How long after HA has started the look-back begins."""
CHUNK = timedelta(days=7)
"""How much of one source's history is read at a time."""
MAX_DAYS = 366
"""The furthest back it looks, however long the recorder keeps states."""

type Feed = Callable[[datetime, str, Mapping[str, Any] | None], None]
"""A finder's ``feed``: when, the state, and its attributes if they were read."""


@dataclass(frozen=True, slots=True)
class Request:
    """One of Wrapped's sensors to look back for."""

    key: str
    """The sensor's unique id."""
    kind: str
    """"restarts", "blocked", "playback" or "power_cuts"."""
    sources: tuple[str, ...]
    until: datetime
    """When the sensor was created: it counted everything after."""
    exact: bool = False
    """Restarts from a start time to the second (a Docker container's)."""


class BackfillStore:
    """What was found for each sensor, by unique id; a sensor in here was looked back for."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Nothing is read until ``async_load``."""
        self._store: Store[dict[str, dict[str, Any]]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.backfill"
        )
        self._found: dict[str, Backfilled] = {}

    async def async_load(self) -> None:
        """Read what was saved; what can't be read is looked back for again."""
        try:
            data = await self._store.async_load() or {}
        except Exception:
            _LOGGER.warning("Couldn't read %s; looking back again", self._store.path, exc_info=True)
            data = {}
        self._found = {}
        for key, value in data.items() if isinstance(data, dict) else ():
            try:
                self._found[key] = Backfilled.from_dict(value)
            except (AttributeError, KeyError, TypeError, ValueError):
                _LOGGER.warning("Couldn't read what was found for %s; looking back again", key)

    @property
    def found(self) -> Mapping[str, Backfilled]:
        """Everything found so far."""
        return self._found

    def set(self, key: str, found: Backfilled) -> None:
        """Keep what was found for one sensor (saved by ``async_save``)."""
        self._found[key] = found

    async def async_save(self) -> None:
        """Save everything found."""
        await self._store.async_save({key: item.as_dict() for key, item in self._found.items()})


class Backfiller:
    """Looks back for the sensors that haven't been yet, one at a time."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry[Any],
        store: BackfillStore,
        on_found: Callable[[], None],
    ) -> None:
        """``on_found`` is called when a look-back is done."""
        self._hass = hass
        self._entry = entry
        self._store = store
        self._on_found = on_found
        self._tried: set[str] = set()
        self._running = False

    @callback
    def async_request(self, requests: Iterable[Request]) -> None:
        """Look back for these, unless done already or a look-back is under way."""
        # Not while HA is starting (hass.is_running is true then too).
        if self._running or self._hass.state is not CoreState.running:
            return
        todo = [
            request
            for request in requests
            if request.sources
            and request.key not in self._store.found
            and request.key not in self._tried
        ]
        if not todo:
            return
        self._running = True
        self._entry.async_create_background_task(
            self._hass, self._async_run(todo), f"{DOMAIN} look-back"
        )

    async def _async_run(self, todo: list[Request]) -> None:
        try:
            for request in todo:
                self._tried.add(request.key)  # once per start, even if it fails
                try:
                    found = await self._async_look_back(request)
                except Exception:
                    _LOGGER.warning(
                        "Couldn't read the recorder's history for %s; trying again after "
                        "the next restart",
                        request.key,
                        exc_info=True,
                    )
                    continue
                self._store.set(request.key, found)
            await self._store.async_save()
            self._on_found()
        finally:
            self._running = False

    async def _async_look_back(self, request: Request) -> Backfilled:
        hass = self._hass
        until = request.until
        start = until - timedelta(days=min(get_instance(hass).keep_days, MAX_DAYS) + 1)
        tz = dt_util.get_default_time_zone()
        if request.kind == "restarts":
            source = request.sources[0]
            device_class, unit, state_class = _describe(hass, source)
            if state_class is not None:
                return Backfilled()  # HA keeps its long-term statistics
            finder = RestartFinder(device_class=device_class, unit=unit, exact=request.exact)
            await self._async_feed(source, start, until, finder.feed)
            return finder.result()
        if request.kind == "power_cuts":
            cuts = CutFinder()
            await self._async_feed(request.sources[0], start, until, cuts.feed)
            return cuts.result()
        if request.kind == "blocked":
            reader = DailyReader(read_at=DNS_READ_AT, tz=tz, before=until)
            await self._async_feed(request.sources[0], start, until, reader.feed)
            return reader.result()
        found = []
        for player in request.sources:
            timer = PlayTimer(tz=tz, end=until)
            await self._async_feed(player, start, until, timer.feed, attributes=True)
            found.append(timer.result())
        return combine(found)

    async def _async_feed(
        self,
        entity_id: str,
        start: datetime,
        end: datetime,
        feed: Feed,
        *,
        attributes: bool = False,
    ) -> None:
        """Feed one entity's state changes from ``start`` to ``end`` in time order."""
        recorder = get_instance(self._hass)
        chunk_start, first = start, True
        while chunk_start < end:
            chunk_end = min(chunk_start + CHUNK, end)
            await recorder.async_add_executor_job(
                partial(
                    _changes,
                    self._hass,
                    entity_id,
                    chunk_start,
                    chunk_end,
                    with_start=first,
                    feed=feed,
                    attributes=attributes,
                )
            )
            chunk_start, first = chunk_end, False


def _changes(
    hass: HomeAssistant,
    entity_id: str,
    start: datetime,
    end: datetime,
    *,
    with_start: bool,
    feed: Feed,
    attributes: bool,
) -> None:
    """Runs in the recorder's executor: value changes only, fed in order.

    ``with_start`` also gives the state at ``start``, for the first chunk;
    ``attributes`` reads the states' attributes too. The finders fed are this
    look-back's alone, and fed one job at a time.
    """
    states = state_changes_during_period(
        hass,
        start,
        end,
        entity_id,
        no_attributes=not attributes,
        include_start_time_state=with_start,
    ).get(entity_id, [])
    for state in states:
        feed(state.last_updated, state.state, state.attributes if attributes else None)


def _describe(hass: HomeAssistant, entity_id: str) -> tuple[str | None, str | None, str | None]:
    """The source's device class, unit and state class, which its old states don't carry."""
    entry = er.async_get(hass).async_get(entity_id)
    state = hass.states.get(entity_id)
    attributes = state.attributes if state else {}
    capabilities = (entry.capabilities if entry else None) or {}
    device_class = attributes.get(ATTR_DEVICE_CLASS) or (
        entry and (entry.device_class or entry.original_device_class)
    )
    unit = attributes.get(ATTR_UNIT_OF_MEASUREMENT) or (entry and entry.unit_of_measurement)
    state_class = attributes.get("state_class") or capabilities.get("state_class")
    return _text(device_class), _text(unit), _text(state_class)


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) else None
