"""Wrapped's own sensors: what HA doesn't keep, as totals HA keeps forever.

- one "restarts" sensor per uptime sensor (a counter or a last-boot timestamp),
  and per Docker container (when it last started);
- one "blocked DNS queries" sensor per AdGuard Home or Pi-hole blocked count;
- one "playback" sensor (hours) per media server, over all its players;
- one "power cuts" sensor per UPS: the times it switched to battery.

They are ``total_increasing``, so HA's long-term statistics keep their history
after the recorder has forgotten the events. They hang off one "Homelab Wrapped"
service device and are hidden from auto-generated dashboards. What the recorder
still had from before a sensor was created is looked back for once (``backfill``).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.media_player import MediaPlayerState
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    EntityCategory,
    UnitOfTime,
)
from homeassistant.core import (
    CALLBACK_TYPE,
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_change,
    async_track_time_interval,
)
from homeassistant.helpers.start import async_at_started
from homeassistant.util import dt as dt_util

from .backfill import SETTLE, Backfiller, Request
from .const import DNS_READ_AT, DOMAIN, TITLE
from .core.model import Inventory
from .core.sources import Signal, find_signals
from .core.tally import (
    FOLLOW_GAP,
    DailyTotal,
    PlaybackClock,
    PowerCuts,
    RestartCounter,
    media_title,
    on_battery,
    read_uptime,
)
from .inventory import as_text, read_devices, read_entities, source_name
from .runtime import WrappedConfigEntry
from .storage import TallyStore

RESCAN_INTERVAL = timedelta(minutes=15)
"""How often to look for new things to count (a new VM, a new media player)."""
FLUSH_INTERVAL = timedelta(minutes=5)
"""How often ongoing playback is added to the total."""
LATE_LIMIT = RESCAN_INTERVAL + timedelta(minutes=5)
"""A player the rescan finds already playing (a new Jellyfin session) counts from when it
began, but never from further back than a rescan can miss."""
NEW_PLAYER_DELAY = timedelta(seconds=2)
"""How soon after a new media player appears to look again: Jellyfin makes one per app or
TV the first time it connects, and its first minutes would be lost until the rescan.
Players added together (a new integration) make one scan."""


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WrappedConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a sensor for everything there is to count, and keep looking."""
    sensors = CountingSensors(hass, entry, async_add_entities)
    sensors.async_scan()
    entry.async_on_unload(async_track_time_interval(hass, sensors.async_scan, RESCAN_INTERVAL))
    entry.async_on_unload(
        hass.bus.async_listen(
            er.EVENT_ENTITY_REGISTRY_UPDATED,
            sensors.async_scan_soon,
            event_filter=_is_new_player,
        )
    )
    entry.async_on_unload(sensors.async_stop)

    @callback
    def _started(hass: HomeAssistant) -> None:
        entry.async_on_unload(async_call_later(hass, SETTLE, sensors.async_look_back))

    entry.async_on_unload(async_at_started(hass, _started))


@callback
def _is_new_player(data: er.EventEntityRegistryUpdatedData) -> bool:
    return data["action"] == "create" and data["entity_id"].startswith("media_player.")


class CountingSensors:
    """Finds what to count and keeps one sensor for each."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: WrappedConfigEntry,
        async_add_entities: AddConfigEntryEntitiesCallback,
    ) -> None:
        """Nothing is added until the first scan."""
        self._hass = hass
        self._entry = entry
        self._add = async_add_entities
        self._sensors: dict[str, CountingSensor] = {}
        self._soon: CALLBACK_TYPE | None = None
        runtime = entry.runtime_data
        self._backfiller = Backfiller(hass, entry, runtime.backfill, runtime.forget_cards)

    @callback
    def async_scan(self, now: datetime | None = None) -> None:
        """Add sensors for new sources; point existing ones at renamed entities."""
        hass = self._hass
        left_out = self._entry.runtime_data.left_out
        found = find_signals(Inventory(read_entities(hass, left_out), read_devices(hass, left_out)))
        registry = er.async_get(hass)
        wanted: dict[str, tuple[type[CountingSensor], str, list[str], str]] = {}

        # The last item: what kind of machine (Kind's value) a restarts sensor counts for.
        per_entity: tuple[tuple[Signal, type[CountingSensor], str], ...] = (
            (Signal.UPTIME, RestartsSensor, "server"),
            (Signal.CONTAINER_UPTIME, RestartsSensor, "container"),
            (Signal.NETWORK_UPTIME, RestartsSensor, "network"),
            (Signal.DNS_BLOCKED, BlockedSensor, ""),
            (Signal.UPS, PowerCutsSensor, ""),
        )
        for signal, kind, machine in per_entity:
            for item in found.get(signal, []):
                if item.entity_id and (entry := registry.async_get(item.entity_id)):
                    # The registry id survives renames, so the history does too.
                    key = f"{kind.KIND}_{entry.id}"
                    name = source_name(hass, item.entity_id)
                    wanted[key] = (kind, name, [item.entity_id], machine)

        for item in found.get(Signal.MEDIA, []):
            if item.entity_id:
                key = f"{PlaybackSensor.KIND}_{item.adapter}"
                media = wanted.setdefault(key, (PlaybackSensor, item.source, [], ""))
                media[2].append(item.entity_id)

        # What isn't wanted any more (left out, or gone) stops counting but keeps its history.
        for key, existing in self._sensors.items():
            if key not in wanted:
                existing.follow([])

        new: list[CountingSensor] = []
        for key, (kind, name, sources, machine) in wanted.items():
            if (sensor := self._sensors.get(key)) is not None:
                sensor.follow(sources)
                continue
            sensor = kind(
                self._entry.runtime_data.tally,
                self._entry.entry_id,
                key,
                name,
                sources,
                machine=machine,
            )
            self._sensors[key] = sensor
            new.append(sensor)
        if new:
            self._add(new)
        self.async_look_back()

    @callback
    def async_scan_soon(self, event: Event[er.EventEntityRegistryUpdatedData]) -> None:
        """A media player was added: scan in a moment, once for players added together."""
        if self._soon is None:
            self._soon = async_call_later(self._hass, NEW_PLAYER_DELAY, self._scan_soon)

    @callback
    def _scan_soon(self, now: datetime) -> None:
        self._soon = None
        self.async_scan()

    @callback
    def async_stop(self) -> None:
        """No scan after the entry is unloaded."""
        if self._soon is not None:
            self._soon()
            self._soon = None

    @callback
    def async_look_back(self, now: datetime | None = None) -> None:
        """Look back over the recorder's history for sensors that haven't been yet.

        Only for sensors already in the entity registry: when they were created
        there is where the look-back ends.
        """
        self._backfiller.async_request(
            Request(
                key,
                sensor.KIND,
                tuple(sensor.sources),
                sensor.registry_entry.created_at,
                exact=sensor.exact,
            )
            for key, sensor in self._sensors.items()
            if sensor.registry_entry is not None
        )


class CountingSensor(SensorEntity):
    """A total that only grows, kept in Wrapped's own storage."""

    KIND = ""
    FOLLOWS_CHANGES = True
    """Whether the sources' state changes are fed to ``_on_state``."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_visible_default = False

    def __init__(
        self,
        store: TallyStore,
        entry_id: str,
        key: str,
        name: str,
        sources: list[str],
        *,
        machine: str = "",
    ) -> None:
        """Pick up the saved count; ``sources`` are the entities it reads; ``machine`` is
        the kind of machine a restarts sensor counts for (server, container, network)."""
        self._store = store
        self._key = key
        self._name = name
        self._machine = machine
        self._sources = list(sources)
        self._unsub_sources: CALLBACK_TYPE | None = None
        self._commit_lock = asyncio.Lock()
        self._removed = False
        self._attr_unique_id = key
        self._attr_translation_placeholders = {"source": name}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)}, name=TITLE, entry_type=DeviceEntryType.SERVICE
        )
        self._load(store.get(key))
        self._attr_native_value = self._value()

    @property
    def sources(self) -> list[str]:
        """The entities it reads."""
        return list(self._sources)

    @property
    def exact(self) -> bool:
        """It reads a start time to the second: a Docker container's (Portainer)."""
        return self._machine == "container"

    def _record(self) -> dict[str, Any]:
        """What is saved: the count, and the source's name and kind of machine, so the cards
        still show it once the source is gone (a retired server, a replaced DNS blocker)."""
        record = self._dump() | {"name": self._name}
        if self._machine:
            record["machine"] = self._machine
        return record

    def _load(self, data: dict[str, Any] | None) -> None:
        raise NotImplementedError

    def _dump(self) -> dict[str, Any]:
        raise NotImplementedError

    def _value(self) -> float:
        raise NotImplementedError

    def _on_state(self, state: State) -> None:
        """A source changed (or this is its state when the sensor starts)."""

    async def async_added_to_hass(self) -> None:
        """Start following the sources."""
        self._follow()
        self.async_on_remove(self._unfollow)

    async def async_will_remove_from_hass(self) -> None:
        """A commit still saving must not write the state of a removed sensor."""
        self._removed = True

    @callback
    def follow(self, sources: list[str]) -> None:
        """Read these entities from now on: one was renamed, or a player was added."""
        if sorted(sources) == sorted(self._sources):
            return
        self._sources = list(sources)
        if self._unsub_sources is not None:
            self._unfollow()
            self._follow()

    @callback
    def _follow(self) -> None:
        if not self.FOLLOWS_CHANGES:
            return
        self._unsub_sources = async_track_state_change_event(
            self.hass, self._sources, self._on_change
        )
        for entity_id in self._sources:
            if (state := self.hass.states.get(entity_id)) is not None:
                self._on_state(state)

    @callback
    def _unfollow(self) -> None:
        if self._unsub_sources is not None:
            self._unsub_sources()
            self._unsub_sources = None

    @callback
    def _on_change(self, event: Event[EventStateChangedData]) -> None:
        if (state := event.data["new_state"]) is not None:
            self._on_state(state)
        else:
            self._on_gone(event.data["entity_id"])

    def _on_gone(self, entity_id: str) -> None:
        """A source's state was removed (its integration unloaded, or it was deleted)."""

    @callback
    def _commit(self) -> None:
        """Save the count, then show it (see TallyStore)."""
        self.hass.async_create_task(self._async_commit(), eager_start=True)

    async def _async_commit(self) -> None:
        async with self._commit_lock:  # one at a time, so the sensor never shows a lower count
            value = self._value()
            await self._store.async_commit(self._key, self._record())
            if self._removed:
                return
            self._attr_native_value = value
            self.async_write_ha_state()


class RestartsSensor(CountingSensor):
    """Restarts of one machine, from its uptime sensor."""

    KIND = "restarts"
    _attr_translation_key = "restarts"

    def _load(self, data: dict[str, Any] | None) -> None:
        self._counter = RestartCounter.from_dict(data)

    def _dump(self) -> dict[str, Any]:
        return self._counter.as_dict()

    def _value(self) -> float:
        return self._counter.count

    _settle_unsub: CALLBACK_TYPE | None = None

    async def async_will_remove_from_hass(self) -> None:
        """No settling after removal."""
        await super().async_will_remove_from_hass()
        if self._settle_unsub is not None:
            self._settle_unsub()
            self._settle_unsub = None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """When the machine last booted (the current streak started then), unless it isn't
        running: a stopped guest's boot time only follows the clock."""
        boot = None if self._counter.stopped else self._counter.last_boot
        return {
            "last_boot": boot.isoformat() if boot else None,
            "running": not self._counter.stopped,
        }

    def _on_state(self, state: State) -> None:
        reading = read_uptime(
            state.state,
            device_class=as_text(state.attributes.get(ATTR_DEVICE_CLASS)),
            unit=as_text(state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)),
            at=state.last_updated,
            exact=self.exact,
        )
        if reading is None:
            return
        first = self._counter.last_boot is None
        was_stopped = self._counter.stopped
        if self._counter.observe(reading) or first:
            self._commit()
        else:
            self._store.update(self._key, self._record())
            if self._counter.stopped != was_stopped:
                self.async_write_ha_state()  # only the attributes change
        if self._counter.fresh or self._counter.stopped:
            # A guest that stopped keeps writing its boot time; one that runs doesn't. If
            # nothing comes, it's running: check after the gap.
            if self._settle_unsub is not None:
                self._settle_unsub()
            self._settle_unsub = async_call_later(
                self.hass, FOLLOW_GAP + timedelta(seconds=30), self._settle
            )

    @callback
    def _settle(self, now: datetime) -> None:
        self._settle_unsub = None
        changed = self._counter.settle(dt_util.utcnow())
        self._store.update(self._key, self._record())  # saved with the next write
        if changed:
            self.async_write_ha_state()


class BlockedSensor(CountingSensor):
    """Blocked DNS queries, from a rolling 24-hour count read once a day."""

    KIND = "blocked"
    FOLLOWS_CHANGES = False
    _attr_translation_key = "blocked"

    def _load(self, data: dict[str, Any] | None) -> None:
        self._total = DailyTotal.from_dict(data)

    def _dump(self) -> dict[str, Any]:
        return self._total.as_dict()

    def _value(self) -> float:
        return self._total.total

    async def async_added_to_hass(self) -> None:
        """Read the count every day at 23:55."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_change(
                self.hass, self._read, hour=DNS_READ_AT.hour, minute=DNS_READ_AT.minute, second=0
            )
        )

    @callback
    def _read(self, now: datetime) -> None:
        if not self._sources:
            return  # left out
        state = self.hass.states.get(self._sources[0])
        if state is None:
            return
        try:
            value = float(state.state)
        except ValueError:
            return
        if self._total.take(value, dt_util.as_local(now).date()):
            self._commit()


class PowerCutsSensor(CountingSensor):
    """The times one UPS switched to battery; when and for how long is kept in storage."""

    KIND = "power_cuts"
    _attr_translation_key = "power_cuts"

    def _load(self, data: dict[str, Any] | None) -> None:
        self._cuts = PowerCuts.from_dict(data)

    def _dump(self) -> dict[str, Any]:
        return self._cuts.as_dict()

    def _value(self) -> float:
        return self._cuts.count

    def _on_state(self, state: State) -> None:
        battery = on_battery(state.state)
        count = self._cuts.count
        if battery is None or not self._cuts.observe(battery, dt_util.utcnow()):
            return
        if self._cuts.count != count:
            self._commit()  # a new cut: the count the sensor shows changes
        else:
            # A cut ended: how long it lasted is saved with the next write (a cut still
            # open after a crash ends when HA sees mains again, and isn't counted twice).
            self._store.update(self._key, self._record())


class PlaybackSensor(CountingSensor):
    """Hours played on one media server, over all its players, and per title."""

    KIND = "playback"
    _attr_translation_key = "playback"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_suggested_display_precision = 1

    def _load(self, data: dict[str, Any] | None) -> None:
        self._clock = PlaybackClock.from_dict(data)
        self._late: set[str] = set()

    def _dump(self) -> dict[str, Any]:
        return self._clock.as_dict()

    def _value(self) -> float:
        return round(self._clock.seconds / 3600, 4)

    async def async_added_to_hass(self) -> None:
        """Add ongoing playback to the total every few minutes."""
        await super().async_added_to_hass()
        self.async_on_remove(async_track_time_interval(self.hass, self._flush, FLUSH_INTERVAL))

    @callback
    def follow(self, sources: list[str]) -> None:
        """Players no longer followed stop counting; new ones may be playing already."""
        now = dt_util.utcnow()
        for player in set(self._clock.playing_since) - set(sources):
            self._clock.update(player, False, now, year=_year(now))
        added, gone = set(sources) - set(self._sources), set(self._sources) - set(sources)
        # One player gone and another new in the same rescan is most likely a rename: its
        # playing so far was counted under the old name.
        self._late = added if not gone else set()
        super().follow(sources)
        self._late = set()

    def _on_gone(self, entity_id: str) -> None:
        """Jellyfin unloaded or reloaded mid-play: the player is gone, so it stopped."""
        if entity_id in self._clock.playing_since:
            moment = dt_util.utcnow()
            if self._clock.update(entity_id, False, moment, year=_year(moment)) > 0:
                self._commit()

    def _on_state(self, state: State) -> None:
        player = state.entity_id
        playing = state.state == MediaPlayerState.PLAYING
        was_playing = player in self._clock.playing_since
        title = media_title(state.attributes) if playing else None
        if playing == was_playing and (
            not playing or title == self._clock.playing_title.get(player)
        ):
            # Only the position or the volume changed (Jellyfin reports the position every
            # 10 seconds): ongoing playback is added up by the flush, not here, so the
            # store isn't rewritten on every update.
            return
        at = dt_util.utcnow()
        if playing and not was_playing and player in self._late:
            at = max(state.last_changed, at - LATE_LIMIT)
        added = self._clock.update(player, playing, at, title=title, year=_year(at))
        if playing and was_playing:
            # Only the title changed (music: every track). Its time is counted, but shown
            # and saved with the next flush, so a track change doesn't rewrite the store.
            self._store.update(self._key, self._record())
        elif added > 0:
            self._commit()

    @callback
    def _flush(self, now: datetime) -> None:
        moment = dt_util.utcnow()
        if self._clock.settle(moment, year=_year(moment)) > 0:
            self._commit()


def _year(moment: datetime) -> int:
    """The local year a moment of playing counts for."""
    return dt_util.as_local(moment).year
