"""The story cards, read from long-term statistics in a running Home Assistant."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.homelab_wrapped import history
from custom_components.homelab_wrapped.const import DOMAIN
from custom_components.homelab_wrapped.core.backfill import Backfilled
from custom_components.homelab_wrapped.core.cards import Year
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import StatisticMeanType
from homeassistant.components.recorder.statistics import async_import_statistics
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util

from .conftest import Panel

RESTART = datetime(2026, 3, 1, 20, tzinfo=UTC)
VM_BOOT = datetime(2026, 11, 10, 1, 17, tzinfo=UTC)


def metadata(statistic_id: str, unit: str | None, *, has_sum: bool) -> Any:
    return {
        "mean_type": StatisticMeanType.NONE if has_sum else StatisticMeanType.ARITHMETIC,
        "has_sum": has_sum,
        "name": None,
        "source": "recorder",
        "statistic_id": statistic_id,
        "unit_class": None,
        "unit_of_measurement": unit,
    }


def sums(
    statistic_id: str, unit: str | None, rows: list[tuple[datetime, float]]
) -> tuple[Any, Any]:
    return metadata(statistic_id, unit, has_sum=True), [
        {"start": start, "sum": total, "state": total} for start, total in rows
    ]


def build_sources(hass: HomeAssistant) -> dict[str, er.RegistryEntry]:
    registry = er.async_get(hass)
    server = registry.async_get_or_create(
        "sensor",
        "glances",
        "server-uptime",
        translation_key="uptime",
        original_name="Server uptime",
    )
    hass.states.async_set(
        server.entity_id,
        str(250 * 24 * 3600),
        {"device_class": "duration", "unit_of_measurement": "s", "state_class": "measurement"},
    )
    proxmox = MockConfigEntry(domain="proxmoxve")
    proxmox.add_to_hass(hass)
    devices = dr.async_get(hass)
    node = devices.async_get_or_create(
        config_entry_id=proxmox.entry_id, identifiers={("proxmoxve", "node")}, name="pve"
    )
    guest = devices.async_get_or_create(
        config_entry_id=proxmox.entry_id,
        identifiers={("proxmoxve", "vm")},
        via_device_id=node.id,
        name="haos",
    )
    # As Proxmox VE reports it on HA 2026.10: the "uptime" device class, a boot time.
    vm = registry.async_get_or_create(
        "sensor",
        "proxmoxve",
        "vm-uptime",
        device_id=guest.id,
        translation_key="vm_uptime",
        original_device_class="uptime",
    )
    hass.states.async_set(vm.entity_id, VM_BOOT.isoformat(), {"device_class": "uptime"})
    registry.async_get_or_create(
        "sensor", "proxmoxve", "node-status", device_id=node.id, translation_key="node_status"
    )
    adguard = registry.async_get_or_create(
        "sensor",
        "adguard",
        "blocked",
        translation_key="dns_queries_blocked",
        original_name="AdGuard",
    )
    hass.states.async_set(adguard.entity_id, "100")
    tv = registry.async_get_or_create("media_player", "jellyfin", "tv")
    hass.states.async_set(tv.entity_id, "idle")
    return {"server": server, "vm": vm, "adguard": adguard}


async def import_history(hass: HomeAssistant, sources: dict[str, er.RegistryEntry]) -> None:
    registry = er.async_get(hass)

    def ours(unique_id: str) -> str:
        entity_id = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        assert entity_id is not None
        return entity_id

    # A Glances server's uptime counter: HA kept hourly min/max; it restarted at 20:xx on 1 March.
    hours = []
    for n in range(48):
        start = datetime(2026, 3, 1, tzinfo=UTC) + timedelta(hours=n)
        if start < RESTART:
            low = 100_000 + n * 3600
            hours.append({"start": start, "min": low, "max": low + 3540, "mean": low})
        elif start == RESTART:
            hours.append({"start": start, "min": 60, "max": 100_000 + n * 3600 + 1740, "mean": 0})
        else:
            low = (start - RESTART).total_seconds() - 1800
            hours.append({"start": start, "min": low, "max": low + 3540, "mean": low})
    async_import_statistics(hass, metadata(sources["server"].entity_id, "s", has_sum=False), hours)

    # Wrapped's own sensors since install (9 November).
    vm_restarts = ours(f"restarts_{sources['vm'].id}")
    async_import_statistics(
        hass,
        *sums(
            vm_restarts,
            None,
            [
                (datetime(2026, 11, 9, 8, tzinfo=UTC), 0),
                (datetime(2026, 11, 10, 1, tzinfo=UTC), 1),
            ],
        ),
    )
    async_import_statistics(
        hass,
        *sums(
            ours(f"blocked_{sources['adguard'].id}"),
            None,
            [
                (datetime(2026, 11, 9, 8, tzinfo=UTC), 0),
                (datetime(2026, 11, 9, 23, tzinfo=UTC), 1000),
                (datetime(2026, 11, 10, 23, tzinfo=UTC), 3000),
            ],
        ),
    )
    async_import_statistics(
        hass,
        *sums(
            ours("playback_jellyfin"),
            "h",
            [
                (datetime(2026, 11, 9, 8, tzinfo=UTC), 0),
                (datetime(2026, 11, 10, 4, tzinfo=UTC), 1.5),
                (datetime(2026, 11, 11, 4, tzinfo=UTC), 2.5),
            ],
        ),
    )
    await async_wait_recording_done(hass)


async def cards(hass: HomeAssistant, hass_ws_client: WebSocketGenerator, **extra: Any) -> Any:
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "homelab_wrapped/cards", **extra})
    response = await client.receive_json()
    assert response["success"], response
    return response["result"]


@pytest.mark.freeze_time("2026-11-11T12:00:00+00:00")
async def test_cards_from_long_term_statistics(
    deps: Panel,
    hass: HomeAssistant,
    entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    sources = build_sources(hass)
    await hass.config_entries.async_reload(entry.entry_id)  # Wrapped picks up the sources
    await hass.async_block_till_done()
    await import_history(hass, sources)

    result = await cards(hass, hass_ws_client)
    assert result["year"] == 2026
    by_id = {card["card"]: card for card in result["cards"]}
    assert list(by_id) == ["intro", "uptime", "restarts", "blocked", "media", "personality"]
    assert by_id["personality"]["key"] == "rock"  # the server: 250 days up

    intro = by_id["intro"]
    assert (intro["hosts"], intro["guests"], intro["machines"]) == (1, 1, 2)
    assert intro["since"] == "2026-02-28"  # midnight UTC is still 28 February in US/Pacific

    uptime = by_id["uptime"]
    assert uptime["longest"]["name"] == "Server uptime"
    assert uptime["longest"]["ongoing"]
    assert uptime["current"][1]["name"] == "haos"
    assert uptime["current"][1]["start"] == VM_BOOT.isoformat()  # exact, not the hour
    assert uptime["state"] == "ready"

    restarts = by_id["restarts"]
    assert restarts["total"] == 2
    assert {m["name"]: m["restarts"] for m in restarts["machines"]} == {
        "Server uptime": 1,
        "haos": 1,
    }

    assert by_id["blocked"]["total"] == 3000
    assert by_id["blocked"]["best_day"] == {"date": "2026-11-10", "blocked": 2000}
    assert by_id["media"]["hours"] == 2.5
    assert by_id["media"]["servers"] == [{"name": "Jellyfin", "hours": 2.5}]

    last_year = await cards(hass, hass_ws_client, year=2025)
    assert [card["card"] for card in last_year["cards"]] == ["intro"]


async def test_cards_not_set_up(
    deps: Panel, hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    assert await hass.config_entries.async_unload(entry.entry_id)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "homelab_wrapped/cards"})
    response = await client.receive_json()
    assert response["error"]["code"] == "not_found"


@pytest.mark.freeze_time("2026-11-11T12:00:00+00:00")
@pytest.mark.parametrize("price_class", ["measurement", "total"])
async def test_power_card_from_the_lab_meters(
    deps: Panel,
    hass: HomeAssistant,
    entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    price_class: str,
) -> None:
    """Priced hour by hour, whether the price sensor keeps a mean or (Energi Data
    Service, a "total") only each hour's last price."""
    registry = er.async_get(hass)
    rack = registry.async_get_or_create(
        "sensor", "shelly", "rack-energy", original_device_class="energy", original_name="Rack"
    )
    start = datetime(2026, 11, 10, 8, tzinfo=UTC)
    async_import_statistics(
        hass,
        *sums(rack.entity_id, "Wh", [(start + timedelta(hours=n), 100.0 * n) for n in range(4)]),
    )
    hours = [start + timedelta(hours=n) for n in range(4)]
    if price_class == "measurement":
        async_import_statistics(
            hass,
            metadata("sensor.spot_price", "DKK/MWh", has_sum=False),
            [{"start": hour, "mean": 2000.0, "min": 2000.0, "max": 2000.0} for hour in hours],
        )
    else:
        async_import_statistics(
            hass, *sums("sensor.spot_price", "DKK/MWh", [(hour, 2000.0) for hour in hours])
        )
    await async_wait_recording_done(hass)
    hass.config_entries.async_update_entry(entry, options={"lab_meters": [rack.entity_id]})
    hass.config.components.add("energy")
    prefs = {
        "energy_sources": [
            {
                "type": "grid",
                "stat_energy_from": "sensor.house",
                "entity_energy_price": "sensor.spot_price",
            }
        ]
    }

    with patch(
        "homeassistant.components.energy.data.async_get_manager",
        AsyncMock(return_value=MagicMock(data=prefs)),
    ):
        result = await cards(hass, hass_ws_client)
    power = next(card for card in result["cards"] if card["card"] == "power")
    assert power["kwh"] == 0.3  # 100 Wh in each of three hours
    assert power["cost"] == 0.6  # at 2,000 DKK/MWh
    assert power["currency"] == "DKK"
    assert power["meters"] == [{"name": "Rack", "kwh": 0.3}]
    assert power["state"] == "counting"  # one day of history


@pytest.mark.freeze_time("2026-11-11T12:00:00+00:00")
async def test_cards_are_read_once_and_reused(
    deps: Panel,
    hass: HomeAssistant,
    entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    freezer: Any,
) -> None:
    """Clicking Play again (or another tab) doesn't read a year of statistics again."""
    reads = AsyncMock(wraps=history.async_card_inputs)
    with patch("custom_components.homelab_wrapped.runtime.async_card_inputs", reads):
        await cards(hass, hass_ws_client)
        await cards(hass, hass_ws_client)
        assert reads.await_count == 1
        freezer.tick(timedelta(minutes=11))
        await cards(hass, hass_ws_client)
        assert reads.await_count == 2


@pytest.mark.freeze_time("2026-11-11T12:00:00+00:00")
async def test_a_hand_edited_statistic_is_capped(
    deps: Panel,
    hass: HomeAssistant,
    entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    sources = build_sources(hass)
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    restarts = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"restarts_{sources['vm'].id}"
    )
    assert restarts is not None
    start = datetime(2026, 11, 10, 8, tzinfo=UTC)
    async_import_statistics(
        hass, *sums(restarts, None, [(start, 0), (start + timedelta(hours=1), 1_000_000)])
    )
    await async_wait_recording_done(hass)

    # The list of restart times is capped at 60 for the hour, not a million entries ...
    year = Year.of(2026, now=dt_util.now(), tz=dt_util.get_default_time_zone())
    rows = await get_instance(hass).async_add_executor_job(
        history._read, hass, year, history._Query(restarts={restarts})
    )
    assert len(rows.increases[restarts][1]) == history.MAX_RESTARTS_PER_HOUR
    # ... and the card counts what the cap left.
    result = await cards(hass, hass_ws_client)
    by_id = {card["card"]: card for card in result["cards"]}
    assert by_id["restarts"]["total"] == history.MAX_RESTARTS_PER_HOUR


async def test_year_must_be_a_calendar_year(
    deps: Panel, hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    client = await hass_ws_client(hass)
    for year in (9999, 0):
        await client.send_json_auto_id({"type": "homelab_wrapped/cards", "year": year})
        response = await client.receive_json()
        assert response["error"]["code"] == "invalid_format"


@pytest.mark.freeze_time("2026-11-11T12:00:00+00:00")
async def test_restarts_from_a_total_counter(
    deps: Panel, hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """A "total" uptime counter (ASUS routers) keeps only each hour's end value. A router
    is network gear: its restarts are ranked apart from the servers'."""
    router = er.async_get(hass).async_get_or_create("sensor", "asusrouter", "uptime")
    hass.states.async_set(
        router.entity_id,
        "5000",
        {"device_class": "duration", "unit_of_measurement": "s", "state_class": "total"},
    )
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    start = datetime(2026, 1, 19, tzinfo=UTC)
    values = [100_000 + n * 3600 for n in range(10)] + [1800 + n * 3600 for n in range(10)]
    async_import_statistics(
        hass,
        *sums(
            router.entity_id, "s", [(start + timedelta(hours=n), v) for n, v in enumerate(values)]
        ),
    )
    await async_wait_recording_done(hass)

    result = await cards(hass, hass_ws_client)
    by_id = {card["card"]: card for card in result["cards"]}
    assert by_id["restarts"]["total"] == 0  # no servers
    assert by_id["restarts"]["network"]["total"] == 1
    assert (
        by_id["restarts"]["since"] == "2026-01-18"
    )  # midnight UTC is still the 18th in US/Pacific
    assert "uptime" not in by_id  # nor in the streaks


@pytest.mark.freeze_time("2026-11-11T12:00:00+00:00")
async def test_a_retired_machine_keeps_its_history(
    deps: Panel, hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """A server taken out of service (its uptime entity removed, or disabled) still counts in
    its year: Wrapped's own sensor has its restarts, and its name and kind are kept with the
    count. A count an older Wrapped kept without a kind (a phone's uptime) stays out."""
    registry = er.async_get(hass)
    old = registry.async_get_or_create(
        "sensor",
        "glances",
        "old-uptime",
        translation_key="uptime",
        original_device_class="timestamp",
    )
    first, later = datetime(2026, 1, 5, tzinfo=UTC), datetime(2026, 3, 1, 9, tzinfo=UTC)
    hass.states.async_set(old.entity_id, first.isoformat(), {"device_class": "timestamp"})
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    hass.states.async_set(old.entity_id, later.isoformat(), {"device_class": "timestamp"})
    await hass.async_block_till_done()
    own = registry.async_get_entity_id("sensor", DOMAIN, f"restarts_{old.id}")
    assert own is not None
    saved = entry.runtime_data.tally.get(f"restarts_{old.id}")
    assert saved is not None
    assert (saved["machine"], saved["count"]) == ("server", 1)
    async_import_statistics(
        hass, *sums(own, None, [(datetime(2026, 2, 28, tzinfo=UTC), 0), (later, 1)])
    )
    phone = registry.async_get_or_create(
        "sensor", DOMAIN, "restarts_phone", config_entry=entry, original_name="phone"
    )
    entry.runtime_data.tally.update("restarts_phone", {"count": 7})  # kept before kinds were
    async_import_statistics(
        hass, *sums(phone.entity_id, None, [(datetime(2026, 2, 1, tzinfo=UTC), 0), (later, 7)])
    )
    await async_wait_recording_done(hass)

    registry.async_remove(old.entity_id)  # retired
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    result = await cards(hass, hass_ws_client)
    restarts = next(card for card in result["cards"] if card["card"] == "restarts")
    assert restarts["total"] == 1
    assert [machine["restarts"] for machine in restarts["machines"]] == [1]


@pytest.mark.freeze_time("2026-11-11T12:00:00+00:00")
async def test_services_from_uptime_kuma(
    deps: Panel, hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """The 365-day uptime at the end of the year, or now while HA has no hour of it yet."""
    registry = er.async_get(hass)
    kuma = MockConfigEntry(domain="uptime_kuma")
    kuma.add_to_hass(hass)
    attributes = {"unit_of_measurement": "%", "state_class": "measurement"}
    monitors = {}
    for name, state in (("Website", "99.0"), ("VPN", "97.25"), ("Old", "unavailable")):
        device = dr.async_get(hass).async_get_or_create(
            config_entry_id=kuma.entry_id, identifiers={("uptime_kuma", name)}, name=name
        )
        monitors[name] = registry.async_get_or_create(
            "sensor",
            "uptime_kuma",
            f"{name}-365",
            device_id=device.id,
            translation_key="uptime_365d",
            unit_of_measurement="%",
        )
        hass.states.async_set(monitors[name].entity_id, state, attributes)
    website = monitors["Website"].entity_id
    hour = datetime(2026, 11, 11, 9, tzinfo=UTC)
    async_import_statistics(
        hass,
        metadata(website, "%", has_sum=False),
        [
            {"start": hour - timedelta(hours=1), "mean": 99.9, "min": 99.9, "max": 99.9},
            {"start": hour, "mean": 99.95, "min": 99.9, "max": 100.0},
        ],
    )
    await async_wait_recording_done(hass)

    result = await cards(hass, hass_ws_client)
    uptime = {card["card"]: card for card in result["cards"]}["uptime"]
    assert uptime["longest"] is None  # no machine uptime in this lab
    assert uptime["services"] == {
        "count": 2,
        "uptime": 98.6,
        "least": [{"name": "VPN", "uptime": 97.25}, {"name": "Website", "uptime": 99.95}],
    }


def test_the_look_back_and_the_sensor_are_one_record() -> None:
    """What the look-back found ends where Wrapped's sensor began: a reboot at 09:40 (the
    look-back) and one in 10:00's hour (the sensor) are two, not one seen twice."""
    hour = datetime(2026, 11, 10, 10, tzinfo=UTC)
    earlier = Backfilled(
        datetime(2026, 11, 1, tzinfo=UTC), (datetime(2026, 11, 10, 9, 40, tzinfo=UTC),)
    )
    plan = history._MachinePlan(
        "vm", counters=["sensor.vm_uptime"], recorded=[(earlier, "sensor.ours")]
    )
    machine = history._machine(plan, history._Rows(increases={"sensor.ours": (hour, [hour])}))
    assert len(machine.restarts) == 2
    assert machine.since == datetime(2026, 11, 1, tzinfo=UTC)
