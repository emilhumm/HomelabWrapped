"""Reading Home Assistant into the core's plain data."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)

from custom_components.homelab_wrapped.core.model import EnergyPrefs, Entity
from custom_components.homelab_wrapped.inventory import (
    FirstDays,
    async_build_inventory,
    integration_name,
    split_unique_id,
)
from homeassistant.components.recorder.models import StatisticMeanType
from homeassistant.components.recorder.statistics import async_import_statistics
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.loader import async_get_integration

from .conftest import Panel

FIRST = datetime(2026, 5, 13, 10, tzinfo=UTC)


async def import_hours(
    hass: HomeAssistant, statistic_id: str, unit: str, *, has_sum: bool, start: datetime = FIRST
) -> None:
    """Three hours of long-term statistics."""
    metadata: Any = {
        "mean_type": StatisticMeanType.NONE if has_sum else StatisticMeanType.ARITHMETIC,
        "has_sum": has_sum,
        "name": None,
        "source": "recorder",
        "statistic_id": statistic_id,
        "unit_class": None,
        "unit_of_measurement": unit,
    }
    rows: Any = [
        {"start": start + timedelta(hours=n), "sum": n, "state": n}
        if has_sum
        else {"start": start + timedelta(hours=n), "mean": n, "min": n, "max": n}
        for n in range(3)
    ]
    async_import_statistics(hass, metadata, rows)
    await async_wait_recording_done(hass)


async def test_entities_by_what_they_are(deps: Panel, hass: HomeAssistant) -> None:
    registry = er.async_get(hass)
    uptime = registry.async_get_or_create(
        "sensor",
        "glances",
        "uptime-1",
        translation_key="uptime",
        original_device_class="duration",
        unit_of_measurement="s",
        capabilities={"state_class": "total_increasing"},
    )
    hass.states.async_set(
        uptime.entity_id,
        "100",
        {"device_class": "duration", "unit_of_measurement": "s", "state_class": "measurement"},
    )
    # Unavailable: its attributes are gone, so the registry's are used.
    down = registry.async_get_or_create(
        "sensor",
        "glances",
        "uptime-2",
        translation_key="uptime",
        original_device_class="duration",
        unit_of_measurement="s",
        capabilities={"state_class": "total_increasing"},
    )
    hass.states.async_set(down.entity_id, "unavailable", {})
    registry.async_get_or_create(
        "sensor", "glances", "off", disabled_by=er.RegistryEntryDisabler.USER
    )

    inventory = await async_build_inventory(hass, FirstDays(hass))
    assert set(inventory.entities) == {
        Entity(
            uptime.entity_id,
            "sensor",
            "glances",
            device_class="duration",
            unit="s",
            state_class="measurement",
            translation_key="uptime",
            unique_id="uptime-1",
        ),
        Entity(
            down.entity_id,
            "sensor",
            "glances",
            device_class="duration",
            unit="s",
            state_class="total_increasing",
            translation_key="uptime",
            unique_id="uptime-2",
            available=False,
        ),
    }


async def test_a_lab_meter_is_named_after_its_integration(deps: Panel, hass: HomeAssistant) -> None:
    """The Power card's "From ..." names the meter's integration, which has no adapter."""
    meter = er.async_get(hass).async_get_or_create("sensor", "sensor", "rack-energy")
    await async_get_integration(hass, "sensor")
    inventory = await async_build_inventory(hass, FirstDays(hass), lab_meters=[meter.entity_id])
    assert inventory.integration_names == {"sensor": "Sensor"}
    assert integration_name(hass, "shelly") == "shelly"  # not loaded


async def test_devices_with_their_integrations(deps: Panel, hass: HomeAssistant) -> None:
    proxmox = MockConfigEntry(domain="proxmoxve")
    proxmox.add_to_hass(hass)
    registry = dr.async_get(hass)
    node = registry.async_get_or_create(
        config_entry_id=proxmox.entry_id, identifiers={("proxmoxve", "node")}
    )
    guest = registry.async_get_or_create(
        config_entry_id=proxmox.entry_id,
        identifiers={("proxmoxve", "vm")},
        via_device_id=node.id,
    )
    off = registry.async_get_or_create(
        config_entry_id=proxmox.entry_id, identifiers={("proxmoxve", "off")}
    )
    registry.async_update_device(off.id, disabled_by=dr.DeviceEntryDisabler.USER)

    inventory = await async_build_inventory(hass, FirstDays(hass))
    assert {(d.device_id, d.integrations, d.via_device_id) for d in inventory.devices} == {
        (node.id, frozenset({"proxmoxve"}), None),
        (guest.id, frozenset({"proxmoxve"}), node.id),
    }


async def test_first_day_only_for_statistics_an_adapter_uses(
    deps: Panel, hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    registry = er.async_get(hass)
    uptime = registry.async_get_or_create(
        "sensor", "glances", "uptime-1", translation_key="uptime", unit_of_measurement="s"
    )
    await import_hours(hass, uptime.entity_id, "s", has_sum=False)
    await import_hours(hass, "sensor.unrelated", "W", has_sum=False)
    await import_hours(
        hass, "sensor.grid", "kWh", has_sum=True, start=datetime(2026, 3, 2, 12, tzinfo=UTC)
    )
    # An energy meter in the house: found as energy, but no card says "since" about it
    # unless it's picked as a lab meter, so its whole history isn't read.
    fridge = registry.async_get_or_create(
        "sensor",
        "shelly",
        "fridge-energy",
        original_device_class="energy",
        unit_of_measurement="kWh",
        capabilities={"state_class": "total_increasing"},
    )
    await import_hours(hass, fridge.entity_id, "kWh", has_sum=True)

    inventory = await async_build_inventory(hass, FirstDays(hass))
    assert inventory.statistics[fridge.entity_id].first is None
    picked = await async_build_inventory(hass, FirstDays(hass), [fridge.entity_id])
    assert picked.statistics[fridge.entity_id].first == date(2026, 5, 13)
    assert inventory.statistics[uptime.entity_id].first == date(2026, 5, 13)
    assert inventory.statistics[uptime.entity_id].unit == "s"
    assert inventory.statistics["sensor.unrelated"].first is None
    assert inventory.statistics["sensor.grid"].first is None  # not in the Energy dashboard

    # Kept between restarts, and not looked up twice.
    await hass.async_block_till_done()
    stored = hass_storage["homelab_wrapped.first_days"]["data"]
    assert stored == {uptime.entity_id: "2026-05-13", fridge.entity_id: "2026-05-13"}
    with patch("custom_components.homelab_wrapped.inventory._first_days") as lookup:
        again = await FirstDays(hass).async_get({uptime.entity_id}, existing={uptime.entity_id})
    lookup.assert_not_called()
    assert again == {uptime.entity_id: date(2026, 5, 13)}


async def test_first_day_of_a_sum_statistic(deps: Panel, hass: HomeAssistant) -> None:
    await import_hours(
        hass, "sensor.grid", "kWh", has_sum=True, start=datetime(2026, 3, 2, 12, tzinfo=UTC)
    )
    days = await FirstDays(hass).async_get({"sensor.grid", "sensor.none"}, existing={"sensor.grid"})
    assert days == {"sensor.grid": date(2026, 3, 2)}


async def test_deleted_statistics_are_forgotten(
    deps: Panel, hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    hass_storage["homelab_wrapped.first_days"] = {
        "version": 1,
        "key": "homelab_wrapped.first_days",
        "data": {"sensor.kept": "2026-01-01", "sensor.deleted": "2025-01-01"},
    }
    days = await FirstDays(hass).async_get({"sensor.kept"}, existing={"sensor.kept"})
    assert days == {"sensor.kept": date(2026, 1, 1)}
    assert hass_storage["homelab_wrapped.first_days"]["data"] == {"sensor.kept": "2026-01-01"}


async def energy_prefs(hass: HomeAssistant, prefs: dict[str, Any] | None) -> EnergyPrefs:
    hass.config.components.add("energy")
    with patch(
        "homeassistant.components.energy.data.async_get_manager",
        AsyncMock(return_value=MagicMock(data=prefs)),
    ):
        return (await async_build_inventory(hass, FirstDays(hass))).energy


async def test_energy_dashboard_in_both_formats(deps: Panel, hass: HomeAssistant) -> None:
    legacy = {
        "energy_sources": [
            {
                "type": "grid",
                "flow_from": [
                    {"stat_energy_from": "sensor.day", "entity_energy_price": "sensor.price"},
                    {"stat_energy_from": "sensor.night", "entity_energy_price": "sensor.price"},
                ],
                "flow_to": [],
            },
            {"type": "solar", "stat_energy_from": "sensor.solar"},
        ],
        "device_consumption": [],
    }
    assert await energy_prefs(hass, legacy) == EnergyPrefs(
        ("sensor.day", "sensor.night"), ("sensor.price",), fixed_price=None
    )

    current = {
        "energy_sources": [
            {
                "type": "grid",
                "stat_energy_from": "sensor.meter",
                "entity_energy_price": None,
                "number_energy_price": 2.1,
            },
            {"type": "grid", "stat_energy_from": None, "stat_energy_to": "sensor.export"},
        ],
        "device_consumption": [],
    }
    assert await energy_prefs(hass, current) == EnergyPrefs(("sensor.meter",), (), fixed_price=2.1)
    assert await energy_prefs(hass, None) == EnergyPrefs()


def test_reading_wrapped_sensors_unique_ids() -> None:
    """A kind can have an underscore of its own ("power_cuts")."""
    assert split_unique_id("power_cuts_abc_1") == ("power_cuts", "abc_1")
    assert split_unique_id("restarts_abc") == ("restarts", "abc")
    assert split_unique_id("playback_jellyfin") == ("playback", "jellyfin")
    assert split_unique_id("something_else") == ("", "something_else")
