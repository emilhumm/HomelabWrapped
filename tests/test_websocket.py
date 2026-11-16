"""The panel's websocket commands and the diagnostics download."""

from __future__ import annotations

import json
from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator, WebSocketGenerator

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

from .conftest import Panel
from .test_inventory import import_hours


async def build_lab(hass: HomeAssistant) -> list[str]:
    """A small lab: a Proxmox node with a guest, an uptime counter with history, AdGuard."""
    proxmox = MockConfigEntry(domain="proxmoxve")
    proxmox.add_to_hass(hass)
    devices = dr.async_get(hass)
    node = devices.async_get_or_create(
        config_entry_id=proxmox.entry_id, identifiers={("proxmoxve", "pve-basement")}
    )
    guest = devices.async_get_or_create(
        config_entry_id=proxmox.entry_id,
        identifiers={("proxmoxve", "nas-of-doom")},
        via_device_id=node.id,
    )
    entities = er.async_get(hass)
    # What makes them a node and a guest (a storage would hang off the node too).
    entities.async_get_or_create(
        "sensor", "proxmoxve", "node-status", device_id=node.id, translation_key="node_status"
    )
    entities.async_get_or_create(
        "sensor", "proxmoxve", "guest-status", device_id=guest.id, translation_key="vm_status"
    )
    uptime = entities.async_get_or_create(
        "sensor",
        "proxmoxve",
        "pve-basement-uptime",
        translation_key="uptime",
        original_device_class="duration",
        unit_of_measurement="s",
        capabilities={"state_class": "total_increasing"},
    )
    blocked = entities.async_get_or_create(
        "sensor", "adguard", "adguard-blocked", translation_key="dns_queries_blocked"
    )
    await import_hours(hass, uptime.entity_id, "s", has_sum=False)
    return [uptime.entity_id, blocked.entity_id, "pve-basement", "nas-of-doom"]


@pytest.mark.freeze_time("2026-11-11T12:00:00+00:00")
async def test_coverage(
    deps: Panel, hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    await build_lab(hass)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "homelab_wrapped/coverage"})
    response = await client.receive_json()
    assert response["success"]
    result = response["result"]

    assert result["installed"] == "2026-11-09"
    assert result["signals"] == {"dns_blocked": 1, "guest": 1, "host": 1, "uptime": 1}
    assert (result["years"], result["year"]) == ([dt_util.now().year], dt_util.now().year)
    cards = {card["card"]: card for card in result["cards"]}
    assert list(cards) == [
        "intro",
        "uptime",
        "restarts",
        "blocked",
        "media",
        "power",
        "personality",
        "summary",
    ]
    assert cards["intro"]["state"] == "ready"
    assert cards["uptime"] == {
        "card": "uptime",
        "number": 2,
        "state": "ready",
        "since": "2026-05-13",
        "ready_on": None,
        "sources": ["Proxmox VE"],
        "unlock": [],
        "hints": [],
    }
    assert cards["blocked"]["state"] == "counting"
    assert cards["blocked"]["ready_on"] == "2026-11-16"
    assert cards["media"]["state"] == "locked"
    assert cards["personality"]["state"] == "ready"  # uptime and restarts: two ready cards


async def test_diagnostics_have_no_names(
    deps: Panel,
    hass: HomeAssistant,
    entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    hass_client: ClientSessionGenerator,
) -> None:
    names = await build_lab(hass)
    # Before the websocket client starts the web server: diagnostics adds a route, and
    # a running server's routes are frozen (on Linux the test fails otherwise).
    assert await async_setup_component(hass, "diagnostics", {})
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "homelab_wrapped/diagnostics"})
    response = await client.receive_json()
    assert response["success"]
    report: dict[str, Any] = response["result"]
    assert report["version"] == "0.1.0"
    assert report["installed"] == "2026-11-09"
    assert {"cards", "signals", "devices", "entities", "energy", "home_assistant"} <= set(report)

    download = await get_diagnostics_for_config_entry(hass, hass_client, entry)
    assert download["entities"] == report["entities"]

    for text in (json.dumps(report), json.dumps(download)):
        for name in names:
            assert name not in text


async def test_not_set_up(
    deps: Panel,
    hass: HomeAssistant,
    entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    assert await hass.config_entries.async_unload(entry.entry_id)
    client = await hass_ws_client(hass)
    for command in ("homelab_wrapped/coverage", "homelab_wrapped/diagnostics"):
        await client.send_json_auto_id({"type": command})
        response = await client.receive_json()
        assert not response["success"]
        assert response["error"]["code"] == "not_found"
