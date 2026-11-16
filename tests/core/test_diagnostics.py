"""The diagnostics report never contains names."""

from __future__ import annotations

from datetime import date
import json

from custom_components.homelab_wrapped.core.coverage import check_coverage
from custom_components.homelab_wrapped.core.diagnostics import diagnostics
from custom_components.homelab_wrapped.core.model import (
    Device,
    EnergyPrefs,
    Entity,
    Inventory,
    Statistic,
)

SECRET_NAMES = (
    "pve-basement",
    "192_168_1_20",
    "nas-of-doom",
    "media_player.livingroom_tv",
    "02_42_ac_11_00_07",  # unique ids can hold a MAC address or a serial number
)


def test_grouped_and_without_names() -> None:
    entities = (
        Entity(
            "sensor.pve_basement_uptime",
            "sensor",
            "proxmoxve",
            device_id="pve-basement",
            device_class="uptime",
            translation_key="node_uptime",
        ),
        Entity(
            "sensor.192_168_1_20_uptime",
            "sensor",
            "proxmoxve",
            device_id="nas-of-doom",
            device_class="uptime",
            translation_key="vm_uptime",
        ),
        Entity(
            "media_player.livingroom_tv",
            "media_player",
            "jellyfin",
            unique_id="02_42_ac_11_00_07_player",
        ),
    )
    inventory = Inventory(
        entities=entities,
        devices=(
            Device("pve-basement", frozenset({"proxmoxve"})),
            Device("nas-of-doom", frozenset({"proxmoxve"}), via_device_id="pve-basement"),
        ),
        statistics={
            "sensor.192_168_1_20_uptime": Statistic(
                "sensor.192_168_1_20_uptime", "s", date(2026, 5, 13)
            )
        },
        energy=EnergyPrefs(grid_import=("sensor.grid",), fixed_price=2.1),
    )
    coverage = check_coverage(inventory, installed=date(2026, 11, 1), today=date(2026, 11, 11))
    report = diagnostics(inventory, coverage)

    text = json.dumps(report)
    for name in SECRET_NAMES:
        assert name not in text

    assert report["entities"] == [
        {
            "integration": "jellyfin",
            "domain": "media_player",
            "device_class": None,
            "unit": None,
            "state_class": None,
            "translation_key": None,
            "long_term_statistics": False,
            "count": 1,
        },
        {
            "integration": "proxmoxve",
            "domain": "sensor",
            "device_class": "uptime",
            "unit": None,
            "state_class": None,
            "translation_key": "node_uptime",
            "long_term_statistics": False,
            "count": 1,
        },
        {
            "integration": "proxmoxve",
            "domain": "sensor",
            "device_class": "uptime",
            "unit": None,
            "state_class": None,
            "translation_key": "vm_uptime",
            "long_term_statistics": True,
            "count": 1,
        },
    ]
    assert report["devices"] == [
        {"integration": "proxmoxve", "via_device": False, "count": 1},
        {"integration": "proxmoxve", "via_device": True, "count": 1},
    ]
    assert report["signals"] == {
        "energy": 1,
        "guest": 1,
        "host": 1,
        "media": 1,
        "price": 1,
        "uptime": 2,
    }
    assert report["energy"] == {
        "grid_import": 1,
        "price_entities": 0,
        "fixed_price": True,
        "lab_meters": 0,
    }
    assert report["cards"][0]["card"] == "intro"
