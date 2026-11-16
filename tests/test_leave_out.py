"""The Leave out option: devices Wrapped ignores (a second integration watching a machine)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.homelab_wrapped.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util

from .conftest import Panel

BOOT = datetime(2026, 10, 1, 8, tzinfo=UTC)


def build_lab(hass: HomeAssistant) -> dict[str, Any]:
    """A Proxmox node, Glances on that same host, and AdGuard."""
    devices = dr.async_get(hass)
    entities = er.async_get(hass)
    lab: dict[str, Any] = {}
    for domain in ("proxmoxve", "glances", "adguard"):
        config = MockConfigEntry(domain=domain)
        config.add_to_hass(hass)
        lab[domain] = devices.async_get_or_create(
            config_entry_id=config.entry_id, identifiers={(domain, "x")}, name=domain
        )
    entities.async_get_or_create(
        "sensor",
        "proxmoxve",
        "status",
        device_id=lab["proxmoxve"].id,
        translation_key="node_status",
    )
    for domain, key, device_class in (
        ("proxmoxve", "node_uptime", "uptime"),
        ("glances", "uptime", "timestamp"),
    ):
        uptime = entities.async_get_or_create(
            "sensor",
            domain,
            f"{domain}-uptime",
            device_id=lab[domain].id,
            translation_key=key,
            original_device_class=device_class,
        )
        hass.states.async_set(uptime.entity_id, BOOT.isoformat(), {"device_class": device_class})
        lab[f"{domain}_uptime"] = uptime
    blocked = entities.async_get_or_create(
        "sensor",
        "adguard",
        "blocked",
        device_id=lab["adguard"].id,
        translation_key="dns_queries_blocked",
    )
    hass.states.async_set(blocked.entity_id, "100")
    lab["blocked"] = blocked
    return lab


async def ws(hass_ws_client: WebSocketGenerator, hass: HomeAssistant, command: str) -> Any:
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": command})
    response = await client.receive_json()
    assert response["success"], response
    return response["result"]


@pytest.mark.freeze_time("2026-11-11T12:00:00+00:00")
async def test_left_out_devices_dont_count(
    deps: Panel, hass: HomeAssistant, hass_ws_client: WebSocketGenerator
) -> None:
    lab = build_lab(hass)
    entry = MockConfigEntry(domain=DOMAIN, data={"installed": "2026-11-09"})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    before = await ws(hass_ws_client, hass, "homelab_wrapped/coverage")
    assert before["signals"]["host"] == 2  # the same machine, twice
    assert before["signals"]["uptime"] == 2

    # Leaving out Glances and AdGuard reloads Wrapped right away.
    loaded = entry.runtime_data
    hass.config_entries.async_update_entry(
        entry, options={"left_out": [lab["glances"].id, lab["adguard"].id]}
    )
    await hass.async_block_till_done()
    assert entry.runtime_data is not loaded

    after = await ws(hass_ws_client, hass, "homelab_wrapped/coverage")
    assert after["signals"] == {"host": 1, "uptime": 1}
    cards = {card["card"]: card for card in after["cards"]}
    assert cards["blocked"]["state"] == "locked"

    story = await ws(hass_ws_client, hass, "homelab_wrapped/cards")
    found = {card["card"]: card for card in story["cards"]}
    assert "blocked" not in found
    assert [streak["name"] for streak in found["uptime"]["current"]] == ["proxmoxve"]

    report = await ws(hass_ws_client, hass, "homelab_wrapped/diagnostics")
    assert report["left_out"] == 2

    # A left-out source is no longer followed: its restart isn't counted.
    registry = er.async_get(hass)
    glances = registry.async_get_entity_id("sensor", DOMAIN, f"restarts_{lab['glances_uptime'].id}")
    assert glances is not None
    hass.states.async_set(
        lab["glances_uptime"].entity_id,
        (BOOT + timedelta(days=5)).isoformat(),
        {"device_class": "timestamp"},
    )
    await hass.async_block_till_done()
    state = hass.states.get(glances)
    assert state is None or state.state in ("0", "unavailable")


@pytest.mark.freeze_time("2026-11-11T12:00:00+00:00")  # 04:00 in the tests' US/Pacific
async def test_a_source_that_disappears_stops_counting(
    deps: Panel, hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    lab = build_lab(hass)
    entry = MockConfigEntry(domain=DOMAIN, data={"installed": "2026-11-09"})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    blocked = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"blocked_{lab['blocked'].id}"
    )
    assert blocked is not None

    er.async_get(hass).async_remove(lab["blocked"].entity_id)
    freezer.tick(timedelta(minutes=15))
    async_fire_time_changed(hass)  # the rescan: the sensor stops following it
    await hass.async_block_till_done()

    moment = datetime(2026, 11, 11, 23, 55, tzinfo=dt_util.get_default_time_zone())
    freezer.move_to(moment)
    async_fire_time_changed(hass, moment)  # the daily read finds nothing to read
    await hass.async_block_till_done()
    state = hass.states.get(blocked)
    assert state is not None
    assert state.state == "0"
