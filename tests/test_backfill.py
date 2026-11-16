"""Looking back over the recorder's history when Wrapped starts counting."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.homelab_wrapped.backfill import SETTLE, BackfillStore
from custom_components.homelab_wrapped.const import DOMAIN
from homeassistant.auth.models import User
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util

from .conftest import Panel


def local(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 11, day, hour, minute, tzinfo=dt_util.get_default_time_zone())


def build_lab(hass: HomeAssistant) -> dict[str, er.RegistryEntry]:
    """AdGuard, a Portainer container, a Jellyfin player, a Glances uptime counter and a UPS."""
    devices = dr.async_get(hass)
    registry = er.async_get(hass)
    portainer = MockConfigEntry(domain="portainer")
    portainer.add_to_hass(hass)
    endpoint = devices.async_get_or_create(
        config_entry_id=portainer.entry_id, identifiers={("portainer", "endpoint")}, name="docker"
    )
    web = devices.async_get_or_create(
        config_entry_id=portainer.entry_id,
        identifiers={("portainer", "web")},
        via_device_id=endpoint.id,
        name="web",
    )
    return {
        "blocked": registry.async_get_or_create(
            "sensor", "adguard", "blocked", translation_key="dns_queries_blocked"
        ),
        "started": registry.async_get_or_create(
            "sensor",
            "portainer",
            "web-started",
            device_id=web.id,
            translation_key="container_started_at",
            original_device_class="timestamp",
        ),
        "player": registry.async_get_or_create("media_player", "jellyfin", "tv"),
        "counter": registry.async_get_or_create(
            "sensor",
            "glances",
            "uptime",
            translation_key="uptime",
            original_device_class="duration",
        ),
        "ups": registry.async_get_or_create(
            "sensor", "nut", "ups-status", translation_key="ups_status"
        ),
    }


async def write_history(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, lab: dict[str, er.RegistryEntry]
) -> None:
    """Eight days of states, from 1 November."""
    timestamp = {"device_class": "timestamp"}
    changes: list[tuple[datetime, str, str, dict[str, Any]]] = [
        (local(1, 9), "started", local(1, 8, 30).isoformat(), timestamp),
        (local(4, 13), "started", local(4, 12, 59).isoformat(), timestamp),  # redeployed
        (local(4, 13, 20), "started", local(4, 13, 19).isoformat(), timestamp),  # and again
        (local(2, 20), "player", "playing", {"media_series_title": "Severance"}),
        (local(2, 22), "player", "idle", {}),
        (local(1, 9), "ups", "OL", {}),
        (local(6, 3, 10), "ups", "OB DISCHRG", {}),  # a power cut in the night
        (local(6, 3, 25), "ups", "OL CHRG", {}),
        (
            local(1, 9),
            "counter",
            "1000",
            {"device_class": "duration", "unit_of_measurement": "s", "state_class": "measurement"},
        ),
    ]
    for day in range(1, 9):
        changes.append((local(day, 12), "blocked", str(500 * day), {}))
        changes.append((local(day, 23, 50), "blocked", str(1000 * day), {}))
    for moment, key, state, attributes in sorted(changes, key=lambda change: change[0]):
        freezer.move_to(moment)
        hass.states.async_set(lab[key].entity_id, state, attributes)
    await async_wait_recording_done(hass)


async def install(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> MockConfigEntry:
    """Wrapped installed on 9 November, and the look-back a minute later."""
    freezer.move_to(local(9, 10))
    entry = MockConfigEntry(domain=DOMAIN, data={"installed": "2026-11-09"})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    freezer.tick(SETTLE + timedelta(seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)
    return entry


async def ws(
    hass_ws_client: WebSocketGenerator, hass: HomeAssistant, user: User, command: str
) -> Any:
    """Logged in now: the tests' own token was made on the frozen 1 November and has expired."""
    refresh = await hass.auth.async_create_refresh_token(user, "https://example.com/app")
    client = await hass_ws_client(hass, hass.auth.async_create_access_token(refresh))
    await client.send_json_auto_id({"type": command})
    response = await client.receive_json()
    assert response["success"], response
    return response["result"]


@pytest.mark.freeze_time("2026-11-01T00:00:00+00:00")
async def test_the_cards_start_with_what_the_recorder_still_had(
    deps: Panel,
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    hass_ws_client: WebSocketGenerator,
    hass_admin_user: User,
) -> None:
    lab = build_lab(hass)
    await write_history(hass, freezer, lab)
    entry = await install(hass, freezer)

    found = entry.runtime_data.backfill.found
    key = {name: lab[name].id for name in ("blocked", "started", "counter", "ups")}
    assert found[f"blocked_{key['blocked']}"].days == {
        local(day, 0).date(): 1000.0 * day for day in range(1, 9)
    }
    assert found[f"restarts_{key['started']}"].restarts == (local(4, 13), local(4, 13, 20))
    assert found["playback_jellyfin"].days == {local(2, 0).date(): 2.0}
    assert found[f"power_cuts_{key['ups']}"].cuts == ((local(6, 3, 10), 900.0),)
    # HA keeps the counter's long-term statistics: nothing to look back for.
    assert found[f"restarts_{key['counter']}"].start is None
    saved = BackfillStore(hass)
    await saved.async_load()
    assert saved.found == found

    coverage = await ws(hass_ws_client, hass, hass_admin_user, "homelab_wrapped/coverage")
    states = {card["card"]: (card["state"], card["since"]) for card in coverage["cards"]}
    assert states["blocked"] == ("ready", "2026-11-01")
    assert states["power"] == ("ready", "2026-11-01")  # the UPS's look-back counts too
    assert states["media"] == ("ready", "2026-11-02")
    assert coverage["signals"]["container"] == 1

    story = await ws(hass_ws_client, hass, hass_admin_user, "homelab_wrapped/cards")
    cards = {card["card"]: card for card in story["cards"]}
    assert cards["blocked"]["total"] == 36_000
    assert cards["blocked"]["best_day"] == {"date": "2026-11-08", "blocked": 8000}
    assert cards["restarts"]["containers"]["top"] == [{"name": "web", "restarts": 2}]
    assert cards["media"]["hours"] == 2.0
    assert cards["media"]["titles"] == [{"title": "Severance", "hours": 2.0}]
    assert cards["intro"]["machines"] == 1  # the Glances host; the container isn't a machine
    assert cards["power"]["power_cuts"] == {
        "count": 1,
        "minutes": 15,
        "longest_minutes": 15.0,
        "seconds": 900,
        "longest_seconds": 900,
        "since": "2026-11-01",
    }

    # Done once: a reload doesn't read the recorder again.
    with patch("custom_components.homelab_wrapped.backfill._changes") as changes:
        await hass.config_entries.async_reload(entry.entry_id)
        freezer.tick(SETTLE + timedelta(seconds=1))
        async_fire_time_changed(hass)
        await hass.async_block_till_done(wait_background_tasks=True)
    changes.assert_not_called()

    report = await ws(hass_ws_client, hass, hass_admin_user, "homelab_wrapped/diagnostics")
    assert report["looked_back"] == {"sensors": 5, "with_history": 4}


@pytest.mark.freeze_time("2026-11-01T00:00:00+00:00")
async def test_a_failing_look_back_is_logged_and_tried_after_the_next_start(
    deps: Panel,
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    build_lab(hass)
    with patch(
        "custom_components.homelab_wrapped.backfill._changes", side_effect=RuntimeError("gone")
    ):
        entry = await install(hass, freezer)
        assert "Couldn't read the recorder's history" in caplog.text
        assert dict(entry.runtime_data.backfill.found) == {
            key: value
            for key, value in entry.runtime_data.backfill.found.items()
            if value.start is None
        }  # only the counter, which wasn't read
        # Not again until the next start, though the 15-minute rescan asks.
        caplog.clear()
        freezer.tick(timedelta(minutes=15))
        async_fire_time_changed(hass)
        await hass.async_block_till_done(wait_background_tasks=True)
        assert "Couldn't read" not in caplog.text


@pytest.mark.freeze_time("2026-11-01T00:00:00+00:00")
async def test_not_while_home_assistant_is_starting(
    deps: Panel,
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    hass_storage: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """It waits for HA to have started; a damaged record is just looked back for again."""
    hass_storage[f"{DOMAIN}.backfill"] = {
        "version": 1,
        "minor_version": 1,
        "key": f"{DOMAIN}.backfill",
        "data": {"restarts_x": {"start": "not a time"}},
    }
    lab = build_lab(hass)
    await write_history(hass, freezer, lab)
    hass.set_state(CoreState.starting)
    entry = await install(hass, freezer)
    assert "Couldn't read what was found for restarts_x" in caplog.text
    assert not entry.runtime_data.backfill.found

    hass.set_state(CoreState.running)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()
    freezer.tick(SETTLE + timedelta(seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert len(entry.runtime_data.backfill.found) == 5


async def test_an_unreadable_file_means_looking_back_again(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    store = BackfillStore(hass)
    with patch.object(store._store, "async_load", side_effect=ValueError("not JSON")):
        await store.async_load()
    assert not store.found
    assert "looking back again" in caplog.text
