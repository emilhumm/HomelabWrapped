"""Reads what Home Assistant has into the core's plain data.

Everything is read through HA's own APIs (registries, states, the recorder's
statistics API, the Energy dashboard's preferences), never from the database
file, so it works the same on SQLite, MariaDB and PostgreSQL. Statistics
queries run in the recorder's executor, never in the event loop.
"""

from __future__ import annotations

import asyncio
from collections.abc import Collection, Iterable, Mapping
from dataclasses import replace
from datetime import UTC, date, datetime
from typing import Any

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import (
    async_list_statistic_ids,
    statistics_during_period,
)
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_UNIT_OF_MEASUREMENT, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.storage import Store
from homeassistant.loader import IntegrationNotLoaded, async_get_loaded_integration
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .core.backfill import Backfilled
from .core.model import Device, EnergyPrefs, Entity, Inventory, Statistic
from .core.sources import ADAPTERS, Signal, find_signals

ATTR_STATE_CLASS = "state_class"
STORAGE_VERSION = 1
HISTORY_START = datetime(2000, 1, 1, tzinfo=UTC)
DATED_SIGNALS = (
    Signal.UPTIME,
    Signal.CONTAINER_UPTIME,
    Signal.NETWORK_UPTIME,
    Signal.SERVICE,
)
"""Signals whose cards are read from the source's own long-term statistics, so its first day
says how far back they go (plus the lab meters). Not Blocked or Media: those are read from
Wrapped's own sensors and the look-back, whatever statistics the source has."""


def integration_name(hass: HomeAssistant, domain: str) -> str:
    """An integration's name ("Shelly" for shelly); the domain while it isn't loaded."""
    try:
        return async_get_loaded_integration(hass, domain).name
    except IntegrationNotLoaded:
        return domain


async def async_build_inventory(
    hass: HomeAssistant,
    first_days: FirstDays,
    lab_meters: Iterable[str] = (),
    left_out: Collection[str] = (),
    backfilled: Mapping[str, Backfilled] | None = None,
) -> Inventory:
    """Everything the coverage check and the cards start from.

    ``lab_meters`` are the energy meters the user picked for the Power card;
    ``backfilled`` is what the look-back found, by Wrapped's sensor. First days are
    looked up only for statistics an adapter or the Power card uses.
    """
    statistics = {
        item["statistic_id"]: Statistic(
            item["statistic_id"], unit=item.get("statistics_unit_of_measurement")
        )
        for item in await async_list_statistic_ids(hass)
    }
    entities = read_entities(hass, left_out)
    meters = tuple(lab_meters)
    inventory = Inventory(
        entities=entities,
        devices=read_devices(hass, left_out),
        statistics=statistics,
        energy=await read_energy(hass),
        lab_meters=meters,
        integration_names={
            entity.platform: integration_name(hass, entity.platform)
            for entity in entities
            if entity.entity_id in meters
        },
        backfilled=backfilled_days(hass, backfilled or {}),
    )
    # Finding a first day reads that statistic's whole history (once; it's stored), so
    # only look it up for what a card says "since" about, not every meter in the house.
    found = find_signals(inventory)
    used = {
        item.entity_id
        for signal in DATED_SIGNALS
        for item in found.get(signal, [])
        if item.entity_id is not None and item.entity_id in statistics
    } | {meter for meter in inventory.lab_meters if meter in statistics}
    days = await first_days.async_get(used, existing=statistics.keys())
    return replace(
        inventory,
        statistics={
            statistic_id: replace(statistic, first=days.get(statistic_id))
            for statistic_id, statistic in statistics.items()
        },
    )


def read_entities(hass: HomeAssistant, left_out: Collection[str] = ()) -> tuple[Entity, ...]:
    """Enabled entities in the entity registry, by what they are.

    Entities of devices in ``left_out`` (the user's Leave out option) are skipped.
    """
    entities = []
    for entry in er.async_get(hass).entities.values():
        if entry.disabled_by is not None or (entry.device_id and entry.device_id in left_out):
            continue
        state = hass.states.get(entry.entity_id)
        live = state is not None and state.state != STATE_UNAVAILABLE
        attributes: Mapping[str, Any] = state.attributes if live and state else {}
        capabilities: Mapping[str, Any] = entry.capabilities or {}
        entities.append(
            Entity(
                entity_id=entry.entity_id,
                domain=entry.domain,
                platform=entry.platform,
                device_id=entry.device_id,
                device_class=as_text(attributes.get(ATTR_DEVICE_CLASS))
                or entry.device_class
                or entry.original_device_class,
                unit=as_text(attributes.get(ATTR_UNIT_OF_MEASUREMENT)) or entry.unit_of_measurement,
                state_class=as_text(
                    attributes.get(ATTR_STATE_CLASS) if live else capabilities.get(ATTR_STATE_CLASS)
                ),
                translation_key=entry.translation_key,
                unique_id=entry.unique_id,
                # HA marks the entities nothing provides any more (a removed container's)
                # unavailable when it starts; no state yet just means not loaded yet.
                available=state is None or state.state != STATE_UNAVAILABLE,
            )
        )
    return tuple(entities)


def read_devices(hass: HomeAssistant, left_out: Collection[str] = ()) -> tuple[Device, ...]:
    """Enabled devices, with the integrations behind them, except those in ``left_out``."""
    devices = []
    for device in dr.async_get(hass).devices:
        if device.disabled_by is not None or device.id in left_out:
            continue
        # A device belongs to one config entry (DeviceEntry.config_entries is deprecated).
        entry = hass.config_entries.async_get_entry(device.config_entry_id)
        integrations = frozenset({entry.domain}) if entry is not None else frozenset()
        devices.append(Device(device.id, integrations, device.via_device_id))
    return tuple(devices)


async def read_energy(hass: HomeAssistant) -> EnergyPrefs:
    """Grid import meters and prices from the Energy dashboard, in old and new formats."""
    if "energy" not in hass.config.components:
        return EnergyPrefs()
    from homeassistant.components.energy.data import async_get_manager  # noqa: PLC0415

    prefs: Mapping[str, Any] = (await async_get_manager(hass)).data or {}
    grid_import: list[str] = []
    prices: list[str] = []
    fixed_price: float | None = None
    for source in prefs.get("energy_sources", []):
        if source.get("type") != "grid":
            continue
        # The older (legacy) format keeps a list of meters in one grid source; the
        # newer one has one meter per grid source.
        for meter in source.get("flow_from") or [source]:
            if statistic_id := meter.get("stat_energy_from"):
                grid_import.append(statistic_id)
            if price := meter.get("entity_energy_price"):
                prices.append(price)
            if (number := meter.get("number_energy_price")) is not None:
                fixed_price = float(number)
    return EnergyPrefs(tuple(grid_import), tuple(dict.fromkeys(prices)), fixed_price)


COUNTER_KINDS = ("restarts", "blocked", "playback", "power_cuts")
"""The kinds of Wrapped's sensors; a unique id is the kind, "_", then the source."""


def split_unique_id(unique_id: str) -> tuple[str, str]:
    """A Wrapped sensor's unique id as (kind, source): the source's registry id, or the
    media server's adapter for playback. ("", unique_id) for one of no known kind."""
    for kind in COUNTER_KINDS:
        if unique_id.startswith(f"{kind}_"):
            return kind, unique_id.removeprefix(f"{kind}_")
    return "", unique_id


def backfilled_days(hass: HomeAssistant, found: Mapping[str, Backfilled]) -> dict[str, date]:
    """Source entity id -> the first day the look-back found for it.

    ``found`` is keyed by Wrapped's sensors' unique ids (``split_unique_id``).
    """
    registry = er.async_get(hass)
    integrations = {adapter.key: adapter.integrations for adapter in ADAPTERS}
    days: dict[str, date] = {}
    for key, item in found.items():
        if item.start is None:
            continue
        day = dt_util.as_local(item.start).date()
        kind, rest = split_unique_id(key)
        if kind == "playback":
            for player in registry.entities.values():
                if player.domain == "media_player" and player.platform in integrations.get(
                    rest, ()
                ):
                    days[player.entity_id] = day
        elif (source := registry.async_get(rest)) is not None:
            days[source.entity_id] = day
    return days


def source_name(hass: HomeAssistant, entity_id: str) -> str:
    """What to call the thing counted: its device's name, else the entity's."""
    entry = er.async_get(hass).async_get(entity_id)
    device = dr.async_get(hass).async_get(entry.device_id) if entry and entry.device_id else None
    if device and (name := device.name_by_user or device.name):
        return name
    if entry and (name := entry.name or entry.original_name):
        return name
    if state := hass.states.get(entity_id):
        return state.name
    return entity_id


def as_text(value: Any) -> str | None:
    return value if isinstance(value, str) else None


class FirstDays:
    """The first day of each statistic's long-term history, stored between restarts.

    Finding it means reading the statistic's whole history once, so the answer
    is kept. A statistic that disappears (the user deleted it) is forgotten, in
    case it comes back with a later start.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Set up the store; nothing is read until it is needed."""
        self._hass = hass
        self._store: Store[dict[str, str]] = Store(hass, STORAGE_VERSION, f"{DOMAIN}.first_days")
        self._days: dict[str, str] | None = None
        self._lock = asyncio.Lock()

    async def async_get(
        self, statistic_ids: Iterable[str], *, existing: Iterable[str]
    ) -> dict[str, date]:
        """First days of ``statistic_ids``; ``existing`` is every statistic HA has now."""
        wanted = set(statistic_ids)
        async with self._lock:
            if self._days is None:
                self._days = await self._store.async_load() or {}
            days = self._days
            gone = days.keys() - set(existing)
            for statistic_id in gone:
                del days[statistic_id]
            found: dict[str, date] = {}
            if missing := wanted - days.keys():
                found = await get_instance(self._hass).async_add_executor_job(
                    _first_days, self._hass, missing
                )
                days.update({key: day.isoformat() for key, day in found.items()})
            if gone or found:
                await self._store.async_save(days)
            return {key: date.fromisoformat(days[key]) for key in wanted if key in days}


def _first_days(hass: HomeAssistant, statistic_ids: set[str]) -> dict[str, date]:
    """Runs in the recorder's executor: one statistic at a time, to keep memory low."""
    found: dict[str, date] = {}
    for statistic_id in statistic_ids:
        rows = statistics_during_period(
            hass, HISTORY_START, None, {statistic_id}, "day", None, {"max", "sum"}
        ).get(statistic_id)
        if rows:
            start = dt_util.utc_from_timestamp(rows[0]["start"])
            found[statistic_id] = dt_util.as_local(start).date()
    return found
