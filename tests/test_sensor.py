"""Wrapped's own counting sensors, in a running Home Assistant."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.homelab_wrapped.const import CONF_INSTALLED, DOMAIN, TITLE
from custom_components.homelab_wrapped.core.cards import Year
from custom_components.homelab_wrapped.history import async_card_inputs
from custom_components.homelab_wrapped.inventory import source_name
from custom_components.homelab_wrapped.sensor import (
    NEW_PLAYER_DELAY,
    CountingSensors,
    RestartsSensor,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util

from .conftest import INSTALLED, Panel

BOOT = datetime(2026, 10, 1, 8, tzinfo=UTC)
STORE = "homelab_wrapped.tally"


async def start(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title=TITLE, data={CONF_INSTALLED: INSTALLED})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def uptime_timestamp(hass: HomeAssistant, unique_id: str = "vm-uptime") -> er.RegistryEntry:
    """A Proxmox guest's uptime sensor that reports its boot time."""
    proxmox = MockConfigEntry(domain="proxmoxve")
    proxmox.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=proxmox.entry_id, identifiers={("proxmoxve", unique_id)}, name="haos"
    )
    return er.async_get(hass).async_get_or_create(
        "sensor",
        "proxmoxve",
        unique_id,
        device_id=device.id,
        translation_key="uptime",
        original_device_class="timestamp",
    )


def set_boot(hass: HomeAssistant, entity_id: str, boot: datetime) -> None:
    hass.states.async_set(entity_id, boot.isoformat(), {"device_class": "timestamp"})


def ours(hass: HomeAssistant, kind: str, key: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{kind}_{key}")
    assert entity_id is not None
    return entity_id


def value(hass: HomeAssistant, entity_id: str) -> float:
    state = hass.states.get(entity_id)
    assert state is not None
    return float(state.state)


def saved(hass_storage: dict[str, Any], key: str) -> dict[str, Any]:
    data: dict[str, Any] = hass_storage[STORE]["data"][key]
    return data


async def test_restarts_from_a_boot_timestamp(
    deps: Panel, hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    source = uptime_timestamp(hass)
    set_boot(hass, source.entity_id, BOOT)
    await start(hass)

    restarts = ours(hass, "restarts", source.id)
    state = hass.states.get(restarts)
    assert state is not None
    assert state.state == "0"
    assert state.name == "Homelab Wrapped haos restarts"
    assert state.attributes["state_class"] == "total_increasing"
    assert state.attributes["last_boot"] == BOOT.isoformat()
    registry_entry = er.async_get(hass).async_get(restarts)
    assert registry_entry is not None
    assert registry_entry.hidden_by is er.RegistryEntryHider.INTEGRATION
    assert registry_entry.entity_category == "diagnostic"

    set_boot(hass, source.entity_id, BOOT + timedelta(seconds=2))  # wobble
    hass.states.async_set(source.entity_id, "unavailable")  # the VM is off
    later = BOOT + timedelta(days=3)
    set_boot(hass, source.entity_id, later)
    await hass.async_block_till_done()

    assert value(hass, restarts) == 1
    state = hass.states.get(restarts)
    assert state is not None
    assert state.attributes["last_boot"] == later.isoformat()
    assert saved(hass_storage, f"restarts_{source.id}")["count"] == 1


async def test_restart_while_home_assistant_was_down(
    deps: Panel, hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    source = uptime_timestamp(hass)
    hass_storage[STORE] = {
        "version": 1,
        "key": STORE,
        "data": {
            f"restarts_{source.id}": {
                "count": 4,
                "last_boot": BOOT.isoformat(),
                "last_seconds": None,
            }
        },
    }
    set_boot(hass, source.entity_id, BOOT + timedelta(days=10))
    await start(hass)
    assert value(hass, ours(hass, "restarts", source.id)) == 5


async def test_restarts_from_a_counter(deps: Panel, hass: HomeAssistant) -> None:
    source = er.async_get(hass).async_get_or_create(
        "sensor", "asuswrt", "router-uptime", translation_key="uptime"
    )
    attributes = {"device_class": "duration", "unit_of_measurement": "s"}
    hass.states.async_set(source.entity_id, "100000", attributes)
    await start(hass)
    restarts = ours(hass, "restarts", source.id)

    hass.states.async_set(source.entity_id, "100060", attributes)
    hass.states.async_set(source.entity_id, "15", attributes)
    await hass.async_block_till_done()
    assert value(hass, restarts) == 1


@pytest.mark.freeze_time("2026-11-11T12:00:00+00:00")  # 04:00 in the tests' US/Pacific
async def test_blocked_queries_read_once_a_day(
    deps: Panel,
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    freezer: FrozenDateTimeFactory,
) -> None:
    source = er.async_get(hass).async_get_or_create(
        "sensor", "adguard", "blocked", translation_key="dns_queries_blocked"
    )
    hass.states.async_set(source.entity_id, "1234")
    await start(hass)
    blocked = ours(hass, "blocked", source.id)
    assert value(hass, blocked) == 0

    local = dt_util.get_default_time_zone()
    for day, count in ((11, "1234"), (11, "1300"), (12, "unavailable"), (13, "100"), (14, None)):
        if count is None:
            hass.states.async_remove(source.entity_id)  # the integration was removed
        else:
            hass.states.async_set(source.entity_id, count)
        moment = datetime(2026, 11, day, 23, 55, tzinfo=local)
        freezer.move_to(moment)
        async_fire_time_changed(hass, moment)
        await hass.async_block_till_done()

    assert value(hass, blocked) == 1334
    # The source's name is kept with the count: the card shows a replaced blocker's year too.
    assert saved(hass_storage, f"blocked_{source.id}") == {
        "total": 1334,
        "last_day": "2026-11-13",
        "name": "adguard blocked",
    }


@pytest.mark.freeze_time("2026-11-11T20:00:00+00:00")
async def test_playback_hours(
    deps: Panel, hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    registry = er.async_get(hass)
    tv = registry.async_get_or_create("media_player", "jellyfin", "tv")
    phone = registry.async_get_or_create("media_player", "jellyfin", "phone")
    hass.states.async_set(tv.entity_id, "playing")
    hass.states.async_set(phone.entity_id, "idle")
    await start(hass)
    playback = ours(hass, "playback", "jellyfin")
    state = hass.states.get(playback)
    assert state is not None
    assert state.name == "Homelab Wrapped Jellyfin playback"
    assert state.attributes["unit_of_measurement"] == "h"

    freezer.tick(timedelta(minutes=30))
    hass.states.async_set(phone.entity_id, "playing")
    await hass.async_block_till_done()
    freezer.tick(timedelta(minutes=6))
    async_fire_time_changed(hass)  # the flush adds ongoing playback
    await hass.async_block_till_done()
    assert value(hass, playback) == pytest.approx(0.7, abs=0.01)  # 36 + 6 minutes

    freezer.tick(timedelta(minutes=24))
    hass.states.async_set(tv.entity_id, "paused")
    hass.states.async_set(phone.entity_id, "off")
    await hass.async_block_till_done()
    assert value(hass, playback) == pytest.approx(1.5, abs=0.01)  # 60 + 30 minutes


async def test_new_and_renamed_sources_are_picked_up(
    deps: Panel, hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    registry = er.async_get(hass)
    tv = registry.async_get_or_create("media_player", "jellyfin", "tv")
    await start(hass)
    playback = ours(hass, "playback", "jellyfin")

    source = uptime_timestamp(hass, "new-vm")
    set_boot(hass, source.entity_id, BOOT)
    renamed = registry.async_update_entity(tv.entity_id, new_entity_id="media_player.living_room")
    freezer.tick(timedelta(minutes=15))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    restarts = ours(hass, "restarts", source.id)
    set_boot(hass, source.entity_id, BOOT + timedelta(days=1))
    hass.states.async_set(renamed.entity_id, "playing")
    freezer.tick(timedelta(minutes=10))
    hass.states.async_set(renamed.entity_id, "idle")
    await hass.async_block_till_done()
    assert value(hass, restarts) == 1
    assert value(hass, playback) == pytest.approx(10 / 60, abs=0.01)

    # The renamed source is found again on the next scan: nothing changes.
    freezer.tick(timedelta(minutes=15))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert value(hass, playback) == pytest.approx(10 / 60, abs=0.01)


async def test_details_saved_on_unload_and_stop(
    deps: Panel, hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    source = er.async_get(hass).async_get_or_create(
        "sensor", "asuswrt", "router-uptime", translation_key="uptime"
    )
    attributes = {"device_class": "duration", "unit_of_measurement": "s"}
    hass.states.async_set(source.entity_id, "1000", attributes)
    entry = await start(hass)
    key = f"restarts_{source.id}"

    hass.states.async_set(source.entity_id, "1060", attributes)  # not a restart: not saved yet
    await hass.async_block_till_done()
    assert saved(hass_storage, key)["last_seconds"] == 1000

    hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
    await hass.async_block_till_done()
    assert saved(hass_storage, key)["last_seconds"] == 1060

    hass.states.async_set(source.entity_id, "1120", attributes)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert saved(hass_storage, key)["last_seconds"] == 1120


async def test_a_removed_player_stops_counting(
    deps: Panel, hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    registry = er.async_get(hass)
    tv = registry.async_get_or_create("media_player", "plex", "tv")
    phone = registry.async_get_or_create("media_player", "plex", "phone")
    hass.states.async_set(tv.entity_id, "playing")
    hass.states.async_set(phone.entity_id, "idle")
    await start(hass)
    playback = ours(hass, "playback", "plex")

    freezer.tick(timedelta(minutes=12))
    registry.async_remove(tv.entity_id)
    freezer.tick(timedelta(minutes=3))
    async_fire_time_changed(hass)  # the scan drops the TV: its 15 minutes count
    await hass.async_block_till_done()
    freezer.tick(timedelta(minutes=60))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert value(hass, playback) == pytest.approx(0.25, abs=0.01)


async def test_source_names(deps: Panel, hass: HomeAssistant) -> None:
    registry = er.async_get(hass)
    named = registry.async_get_or_create("sensor", "glances", "a", original_name="NAS uptime")
    plain = registry.async_get_or_create("sensor", "glances", "b")
    hass.states.async_set(plain.entity_id, "1", {"friendly_name": "Box uptime"})
    source = uptime_timestamp(hass)
    dr.async_get(hass).async_update_device(source.device_id or "", name_by_user="Home Assistant")

    assert source_name(hass, source.entity_id) == "Home Assistant"
    assert source_name(hass, named.entity_id) == "NAS uptime"
    assert source_name(hass, plain.entity_id) == "Box uptime"
    assert source_name(hass, "sensor.gone") == "sensor.gone"


async def test_no_state_written_after_removal() -> None:
    """A count still being saved when the integration unloads doesn't touch the removed sensor."""
    store = MagicMock(get=MagicMock(return_value=None), async_commit=AsyncMock())
    sensor = RestartsSensor(store, "entry", "restarts_x", "nas", ["sensor.nas_uptime"])
    sensor.async_write_ha_state = MagicMock()  # type: ignore[method-assign]
    await sensor.async_will_remove_from_hass()
    await sensor._async_commit()
    store.async_commit.assert_awaited_once()  # the count is still saved
    sensor.async_write_ha_state.assert_not_called()


async def test_position_updates_dont_rewrite_the_store(
    deps: Panel, hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Jellyfin reports the position every 10 s; only starting or stopping is saved."""
    tv = er.async_get(hass).async_get_or_create("media_player", "jellyfin", "tv")
    hass.states.async_set(tv.entity_id, "idle")
    entry = await start(hass)
    tally = entry.runtime_data.tally
    commits = AsyncMock(wraps=tally.async_commit)
    tally.async_commit = commits  # type: ignore[method-assign]

    hass.states.async_set(tv.entity_id, "playing", {"media_position": 0})
    for second in range(10, 240, 10):  # four minutes: before the 5-minute flush
        freezer.tick(timedelta(seconds=10))
        hass.states.async_set(tv.entity_id, "playing", {"media_position": second})
    await hass.async_block_till_done()
    commits.assert_not_awaited()

    hass.states.async_set(tv.entity_id, "paused", {"media_position": 240})
    await hass.async_block_till_done()
    commits.assert_awaited_once()
    played = 230 / 3600  # 23 updates, 10 seconds apart
    assert value(hass, ours(hass, "playback", "jellyfin")) == pytest.approx(played, abs=0.001)


@pytest.mark.freeze_time("2026-11-11T20:00:00+00:00")
async def test_hours_per_title(
    deps: Panel, hass: HomeAssistant, freezer: FrozenDateTimeFactory, hass_storage: dict[str, Any]
) -> None:
    """The series of an episode, else the title; a new episode of the same series changes nothing."""
    tv = er.async_get(hass).async_get_or_create("media_player", "jellyfin", "tv")
    episode = {"media_series_title": "Severance", "media_title": "Good News About Hell"}
    hass.states.async_set(tv.entity_id, "playing", episode | {"media_position": 0})
    entry = await start(hass)
    freezer.tick(timedelta(minutes=50))
    hass.states.async_set(
        tv.entity_id, "playing", episode | {"media_title": "Half Loop", "media_position": 3}
    )
    await hass.async_block_till_done()
    freezer.tick(timedelta(minutes=10))
    playback = ours(hass, "playback", "jellyfin")
    shown = value(hass, playback)
    hass.states.async_set(tv.entity_id, "playing", {"media_title": "Dune", "media_position": 0})
    await hass.async_block_till_done()
    assert value(hass, playback) == shown  # a new title isn't a write; the flush shows it
    freezer.tick(timedelta(minutes=30))
    hass.states.async_set(tv.entity_id, "idle")
    await hass.async_block_till_done()
    assert saved(hass_storage, "playback_jellyfin")["titles"] == {
        "2026": {"Severance": 3600.0, "Dune": 1800.0}
    }
    # The Media card's titles come from there (HA's statistics keep only the total).
    year = Year.of(2026, now=dt_util.now(), tz=dt_util.get_default_time_zone())
    inputs = await async_card_inputs(hass, entry.entry_id, year, tally=entry.runtime_data.tally)
    assert inputs.titles == {"Severance": 1.0, "Dune": 0.5}


@pytest.mark.freeze_time("2026-11-11T20:00:00+00:00")
async def test_a_player_found_playing_counts_from_when_it_began(
    deps: Panel, hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A new Jellyfin session is found by the next rescan; what it played until then counts."""
    registry = er.async_get(hass)
    registry.async_get_or_create("media_player", "jellyfin", "tv")
    await start(hass)
    playback = ours(hass, "playback", "jellyfin")
    freezer.tick(timedelta(minutes=1))
    phone = registry.async_get_or_create("media_player", "jellyfin", "phone")
    hass.states.async_set(phone.entity_id, "playing")
    freezer.tick(timedelta(minutes=14))
    async_fire_time_changed(hass)  # the rescan finds it, 14 minutes in
    await hass.async_block_till_done()
    freezer.tick(timedelta(minutes=6))
    hass.states.async_set(phone.entity_id, "idle")
    await hass.async_block_till_done()
    assert value(hass, playback) == pytest.approx(20 / 60, abs=0.01)


@pytest.mark.freeze_time("2026-11-11T20:00:00+00:00")
async def test_a_stopped_guest_isnt_up_right_now(
    deps: Panel, hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Proxmox VE's uptime class for a stopped VM: uptime 0, so HA writes a boot time of
    about now every minute or two, while a running machine's is held. The stop counts once,
    the cards don't show it as up, and once it runs again (nothing more is written) the
    sensor finds out by itself."""
    source = uptime_timestamp(hass)

    def boot(moment: datetime) -> None:
        hass.states.async_set(source.entity_id, moment.isoformat(), {"device_class": "uptime"})

    boot(BOOT)
    entry = await start(hass)
    restarts = ours(hass, "restarts", source.id)
    freezer.tick(timedelta(minutes=1))
    boot(dt_util.utcnow())  # stopped: like a reboot so far
    await hass.async_block_till_done()
    assert value(hass, restarts) == 1
    freezer.tick(timedelta(minutes=2))
    boot(dt_util.utcnow())  # the boot time follows the clock: not running
    await hass.async_block_till_done()
    state = hass.states.get(restarts)
    assert state is not None
    assert (state.attributes["running"], state.attributes["last_boot"]) == (False, None)

    year = Year.of(2026, now=dt_util.now(), tz=dt_util.get_default_time_zone())
    inputs = await async_card_inputs(hass, entry.entry_id, year, tally=entry.runtime_data.tally)
    (machine,) = inputs.machines
    assert machine.down[-1][1] is None  # stopped still

    freezer.tick(timedelta(minutes=30))  # still stopped, HA was down meanwhile
    boot(dt_util.utcnow())
    await hass.async_block_till_done()
    freezer.tick(timedelta(minutes=2))
    boot(dt_util.utcnow())
    await hass.async_block_till_done()
    freezer.tick(timedelta(minutes=2))
    started = dt_util.utcnow()
    boot(started)  # started again; HA holds this boot time from now on
    await hass.async_block_till_done()
    freezer.tick(timedelta(minutes=6))
    async_fire_time_changed(hass)  # no reading since: it's running
    await hass.async_block_till_done()
    assert value(hass, restarts) == 1
    state = hass.states.get(restarts)
    assert state is not None
    assert state.attributes["running"] is True
    saved_downs = entry.runtime_data.tally.get(f"restarts_{source.id}")["downs"]  # type: ignore[index]
    assert len(saved_downs) == 1  # one stop, across HA's outage
    assert saved_downs[0][1] == started.isoformat()


@pytest.mark.freeze_time("2026-11-11T20:00:00+00:00")
async def test_reboots_seen_live_all_count(
    deps: Panel, hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A reboot's new boot time is written once, a minute after it, then held: the machine
    runs, and the next reboot counts too; one that's unavailable now isn't up right now."""
    source = uptime_timestamp(hass)

    def boot(moment: datetime) -> None:
        hass.states.async_set(source.entity_id, moment.isoformat(), {"device_class": "uptime"})

    boot(BOOT)
    entry = await start(hass)
    restarts = ours(hass, "restarts", source.id)
    for _ in range(2):
        freezer.tick(timedelta(hours=1))
        boot(dt_util.utcnow() - timedelta(seconds=50))  # rebooted 50 s ago
        await hass.async_block_till_done()
        freezer.tick(timedelta(minutes=6))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
    assert value(hass, restarts) == 2
    state = hass.states.get(restarts)
    assert state is not None
    assert state.attributes["running"] is True

    hass.states.async_set(source.entity_id, "unavailable")  # deleted in Proxmox VE
    await hass.async_block_till_done()
    year = Year.of(2026, now=dt_util.now(), tz=dt_util.get_default_time_zone())
    inputs = await async_card_inputs(hass, entry.entry_id, year, tally=entry.runtime_data.tally)
    (machine,) = inputs.machines
    assert machine.down == ((dt_util.utcnow(), None),)

    boot(dt_util.utcnow())  # back, just booted: a check is pending when Wrapped unloads
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.freeze_time("2026-11-11T20:00:00+00:00")
async def test_unavailable_while_its_integration_loads_is_still_up(
    deps: Panel, hass: HomeAssistant
) -> None:
    """While HA starts, a source whose integration hasn't loaded yet is unavailable: the
    machine isn't gone. Once it has loaded, unavailable is (a VM deleted in Proxmox VE)."""
    source = uptime_timestamp(hass)
    proxmox = MockConfigEntry(domain="proxmoxve")
    proxmox.add_to_hass(hass)
    er.async_get(hass).async_update_entity(source.entity_id, config_entry_id=proxmox.entry_id)
    hass.states.async_set(source.entity_id, BOOT.isoformat(), {"device_class": "uptime"})
    entry = await start(hass)
    hass.states.async_set(source.entity_id, "unavailable", {"restored": True})
    await hass.async_block_till_done()
    year = Year.of(2026, now=dt_util.now(), tz=dt_util.get_default_time_zone())

    inputs = await async_card_inputs(hass, entry.entry_id, year, tally=entry.runtime_data.tally)
    (machine,) = inputs.machines
    assert machine.down == ()

    proxmox.mock_state(hass, ConfigEntryState.LOADED)
    inputs = await async_card_inputs(hass, entry.entry_id, year, tally=entry.runtime_data.tally)
    proxmox.mock_state(hass, ConfigEntryState.NOT_LOADED)  # nothing of Proxmox VE to unload
    (machine,) = inputs.machines
    assert machine.down == ((dt_util.utcnow(), None),)


@pytest.mark.freeze_time("2026-11-11T20:00:00+00:00")
async def test_a_player_removed_while_playing_stops(
    deps: Panel, hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Jellyfin reloaded mid-play removes its players' states: they stopped playing."""
    tv = er.async_get(hass).async_get_or_create("media_player", "jellyfin", "tv")
    hass.states.async_set(tv.entity_id, "playing")
    await start(hass)
    playback = ours(hass, "playback", "jellyfin")
    freezer.tick(timedelta(minutes=30))
    hass.states.async_remove(tv.entity_id)
    await hass.async_block_till_done()
    freezer.tick(timedelta(hours=3))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert value(hass, playback) == 0.5


@pytest.mark.freeze_time("2026-11-11T20:00:00+00:00")
async def test_a_new_player_is_followed_at_once(
    deps: Panel, hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A TV opening Jellyfin for the first time gets a new player: what it plays before the
    next rescan counts too (on the first real lab, a short play was lost)."""
    registry = er.async_get(hass)
    registry.async_get_or_create("media_player", "jellyfin", "chrome")
    entry = await start(hass)
    playback = ours(hass, "playback", "jellyfin")
    scan = CountingSensors.async_scan
    with patch.object(CountingSensors, "async_scan", autospec=True, side_effect=scan) as scans:
        freezer.tick(timedelta(minutes=2))
        tv = registry.async_get_or_create("media_player", "jellyfin", "tv")
        registry.async_get_or_create("media_player", "jellyfin", "tv-remote")  # with it
        registry.async_get_or_create("sensor", "jellyfin", "clients")  # not a player
        hass.states.async_set(tv.entity_id, "idle")
        freezer.tick(NEW_PLAYER_DELAY)
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
        assert scans.call_count == 1  # players added together, one scan

        freezer.tick(timedelta(minutes=5))  # long before the rescan
        hass.states.async_set(tv.entity_id, "playing", {"media_title": "Dune"})
        await hass.async_block_till_done()
        freezer.tick(timedelta(minutes=3))
        hass.states.async_set(tv.entity_id, "idle")
        await hass.async_block_till_done()
        assert value(hass, playback) == pytest.approx(3 / 60, abs=0.001)

        # A scan still waiting when Wrapped unloads never runs.
        registry.async_get_or_create("media_player", "jellyfin", "phone")
        await hass.async_block_till_done()
        assert await hass.config_entries.async_unload(entry.entry_id)
        freezer.tick(NEW_PLAYER_DELAY)
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
        assert scans.call_count == 1


@pytest.mark.freeze_time("2026-11-11T20:00:00+00:00")
async def test_power_cuts(
    deps: Panel, hass: HomeAssistant, freezer: FrozenDateTimeFactory, hass_storage: dict[str, Any]
) -> None:
    """Each switch to battery counts once, even across a restart of Wrapped in the middle of it."""
    ups = er.async_get(hass).async_get_or_create(
        "sensor", "nut", "ups-status", translation_key="ups_status"
    )
    hass.states.async_set(ups.entity_id, "OL")
    entry = await start(hass)
    cuts = ours(hass, "power_cuts", ups.id)
    assert hass.states.get(cuts).name.endswith(" power cuts")  # type: ignore[union-attr]
    assert value(hass, cuts) == 0

    freezer.tick(timedelta(hours=1))
    hass.states.async_set(ups.entity_id, "OB DISCHRG")
    await hass.async_block_till_done()
    assert value(hass, cuts) == 1
    assert await hass.config_entries.async_reload(entry.entry_id)  # in the middle of the cut
    await hass.async_block_till_done()
    hass.states.async_set(ups.entity_id, "OB DISCHRG LB")
    freezer.tick(timedelta(minutes=7))
    hass.states.async_set(ups.entity_id, "OL CHRG")
    hass.states.async_set(ups.entity_id, "unavailable")
    await hass.async_block_till_done()
    assert value(hass, cuts) == 1
    # How long it lasted is kept now and saved with the next write, not written at once.
    assert saved(hass_storage, f"power_cuts_{ups.id}")["cuts"] == []
    assert entry.runtime_data.tally.get(f"power_cuts_{ups.id}")["cuts"] == [  # type: ignore[index]
        ["2026-11-11T21:00:00+00:00", 420.0]
    ]

    # The Power card has them, though no meter is picked yet.
    freezer.tick(timedelta(hours=1))
    hass.states.async_set(ups.entity_id, "OB")
    await hass.async_block_till_done()
    freezer.tick(timedelta(minutes=2))
    year = Year.of(2026, now=dt_util.now(), tz=dt_util.get_default_time_zone())
    inputs = await async_card_inputs(hass, entry.entry_id, year, tally=entry.runtime_data.tally)
    (unit,) = inputs.ups
    assert unit.cuts == (
        (datetime(2026, 11, 11, 21, tzinfo=UTC), 420.0),
        (datetime(2026, 11, 11, 22, 7, tzinfo=UTC), 120.0),  # still going on
    )


@pytest.mark.freeze_time("2026-11-11T20:00:00+00:00")
async def test_a_renamed_player_isnt_counted_twice(
    deps: Panel, hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Renamed while playing: the rescan sees one player go and one come; nothing is backdated."""
    registry = er.async_get(hass)
    tv = registry.async_get_or_create("media_player", "jellyfin", "tv")
    hass.states.async_set(tv.entity_id, "playing")
    await start(hass)
    playback = ours(hass, "playback", "jellyfin")
    freezer.tick(timedelta(minutes=10))
    renamed = registry.async_update_entity(tv.entity_id, new_entity_id="media_player.living_room")
    hass.states.async_set(renamed.entity_id, "playing")
    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(hass)  # the rescan, 15 minutes in
    await hass.async_block_till_done()
    freezer.tick(timedelta(minutes=5))
    hass.states.async_set(renamed.entity_id, "idle")
    await hass.async_block_till_done()
    assert value(hass, playback) == pytest.approx(20 / 60, abs=0.01)
