"""The coverage check: ready, counting or locked, and why."""

from __future__ import annotations

from datetime import date

from custom_components.homelab_wrapped.core.coverage import (
    CardCoverage,
    CardId,
    CardState,
    Hint,
    check_coverage,
    wrapped_years,
)
from custom_components.homelab_wrapped.core.model import (
    Device,
    EnergyPrefs,
    Entity,
    Inventory,
    Statistic,
)

TODAY = date(2026, 11, 11)
LONG_AGO = date(2026, 5, 13)

UPTIME = Entity(
    "sensor.node_uptime",
    "sensor",
    "glances",
    device_class="duration",
    unit="s",
    state_class="total_increasing",
    translation_key="uptime",
)
BLOCKED = Entity("sensor.blocked", "sensor", "adguard", translation_key="dns_queries_blocked")
PLAYER = Entity("media_player.tv", "media_player", "jellyfin")
NODE = Device("node", frozenset({"proxmoxve"}))
NODE_STATUS = Entity(
    "sensor.node_status", "sensor", "proxmoxve", "node", translation_key="node_status"
)


def cards(inventory: Inventory, installed: date = TODAY) -> dict[CardId, CardCoverage]:
    return {card.card: card for card in check_coverage(inventory, installed=installed, today=TODAY)}


def test_empty_lab_is_all_locked_with_unlock_steps() -> None:
    result = cards(Inventory())
    assert list(result) == list(CardId)
    assert {card.state for card in result.values()} == {CardState.LOCKED}
    assert "Proxmox VE" in result[CardId.INTRO].unlock
    assert result[CardId.BLOCKED].unlock == ("AdGuard Home", "Pi-hole")
    assert result[CardId.POWER].unlock == ("Network UPS Tools", "APC UPS Daemon")
    assert result[CardId.POWER].hints == (Hint.PICK_METERS,)  # in the options
    assert result[CardId.UPTIME].unlock == (
        "Proxmox VE",
        "Synology DSM",
        "QNAP",
        "Glances",
        "System Monitor",
        "Uptime Kuma",
    )
    assert {"OPNsense", "UniFi Network", "Portainer"} <= set(result[CardId.RESTARTS].unlock)
    assert "Jellyfin" in result[CardId.PERSONALITY].unlock


def test_long_history_is_ready_and_says_how_far_back() -> None:
    inventory = Inventory(
        entities=(UPTIME, NODE_STATUS),
        devices=(NODE,),
        statistics={UPTIME.entity_id: Statistic(UPTIME.entity_id, "s", first=LONG_AGO)},
    )
    result = cards(inventory)
    assert result[CardId.INTRO].state is CardState.READY
    assert result[CardId.INTRO].sources == ("Proxmox VE",)
    for card in (CardId.UPTIME, CardId.RESTARTS):
        assert result[card].state is CardState.READY
        assert result[card].since == LONG_AGO
        assert result[card].hints == ()
    assert result[CardId.SUMMARY].state is CardState.READY


def test_without_history_wrapped_counts_from_install() -> None:
    result = cards(Inventory(entities=(BLOCKED,)), installed=date(2026, 11, 9))
    blocked = result[CardId.BLOCKED]
    assert blocked.state is CardState.COUNTING
    assert blocked.since == date(2026, 11, 9)
    assert blocked.ready_on == date(2026, 11, 16)
    assert blocked.sources == ("AdGuard Home",)
    assert result[CardId.SUMMARY].state is CardState.COUNTING
    assert result[CardId.SUMMARY].ready_on == date(2026, 11, 16)


def test_history_that_stopped_is_still_used_and_flagged() -> None:
    """An integration update turned the counter into a timestamp: HA stopped its statistics."""
    now_a_timestamp = Entity(
        UPTIME.entity_id, "sensor", "glances", device_class="timestamp", translation_key="uptime"
    )
    inventory = Inventory(
        entities=(now_a_timestamp,),
        statistics={UPTIME.entity_id: Statistic(UPTIME.entity_id, "s", first=LONG_AGO)},
    )
    uptime = cards(inventory)[CardId.UPTIME]
    assert uptime.state is CardState.READY
    assert uptime.since == LONG_AGO
    assert uptime.hints == (Hint.HISTORY_BREAK,)


def power(energy: EnergyPrefs, *, price_history: bool = False) -> CardCoverage:
    """Power with one lab meter picked; the Energy dashboard only gives the price."""
    statistics = {"sensor.rack": Statistic("sensor.rack", "kWh", first=LONG_AGO)}
    if price_history:
        statistics["sensor.price"] = Statistic("sensor.price", "DKK/kWh", first=LONG_AGO)
    inventory = Inventory(statistics=statistics, energy=energy, lab_meters=("sensor.rack",))
    return cards(inventory)[CardId.POWER]


def test_a_card_goes_back_as_far_as_its_main_numbers() -> None:
    """Restarts counts the servers; the routers' longer history is their own ranking's, so
    the card says how far back the servers go, as its slide does (on the first real lab
    the coverage said 19 January, the slide 8 April)."""
    router = Entity(
        "sensor.router",
        "sensor",
        "asusrouter",
        device_class="duration",
        unit="s",
        state_class="total",
    )
    statistics = {
        UPTIME.entity_id: Statistic(UPTIME.entity_id, "s", first=LONG_AGO),
        router.entity_id: Statistic(router.entity_id, "s", first=date(2026, 1, 19)),
    }
    both = cards(Inventory(entities=(UPTIME, router), statistics=statistics))[CardId.RESTARTS]
    assert both.since == LONG_AGO
    assert both.sources == ("Glances", "ASUS Router")
    # Without servers, the slide is the network gear's, and so is the date.
    alone = cards(Inventory(entities=(router,), statistics=statistics))[CardId.RESTARTS]
    assert alone.since == date(2026, 1, 19)


def test_power_names_the_meters_integration_first() -> None:
    """The meter's integration has no adapter; HA's name for it is used. Its main source
    first, the UPS after it, whatever order Python keeps the card's signals in."""
    rack = Entity("sensor.rack", "sensor", "shelly", device_class="energy", unit="kWh")
    ups = Entity("sensor.ups", "sensor", "nut", translation_key="ups_status", device_id="ups")
    inventory = Inventory(
        entities=(rack, ups),
        statistics={"sensor.rack": Statistic("sensor.rack", "kWh", first=LONG_AGO)},
        lab_meters=("sensor.rack", "sensor.gone"),
        integration_names={"shelly": "Shelly"},
    )
    assert cards(inventory)[CardId.POWER].sources == ("Shelly", "Network UPS Tools")


def test_a_price_sensor_outside_the_energy_dashboard_isnt_used() -> None:
    """The Power card prices with the dashboard's price only; the hint says what it does."""
    nordpool = Entity("sensor.nordpool", "sensor", "nordpool", unit="DKK/kWh")
    statistics = {
        "sensor.rack": Statistic("sensor.rack", "kWh", first=LONG_AGO),
        nordpool.entity_id: Statistic(nordpool.entity_id, "DKK/kWh", first=LONG_AGO),
    }
    inventory = Inventory(
        entities=(nordpool,),
        statistics=statistics,
        energy=EnergyPrefs(("sensor.grid",)),
        lab_meters=("sensor.rack",),
    )
    assert cards(inventory)[CardId.POWER].hints == (Hint.PRICE_MISSING,)


def test_power_and_its_price() -> None:
    grid = ("sensor.grid",)
    assert power(EnergyPrefs(grid)).hints == (Hint.PRICE_MISSING,)
    assert power(EnergyPrefs(grid, fixed_price=2.1)).hints == (Hint.PRICE_FIXED,)
    assert power(EnergyPrefs(grid, ("sensor.price",))).hints == (Hint.PRICE_LIVE,)
    hourly = power(EnergyPrefs(grid, ("sensor.price",)), price_history=True)
    assert hourly.hints == (Hint.PRICE_HOURLY,)
    assert hourly.state is CardState.READY
    assert hourly.since == LONG_AGO


def test_personality_needs_two_ready_cards() -> None:
    """As many as the story builds it from (core.cards.personality_card)."""
    # Blocked and media both counting until 15 Nov.
    inventory = Inventory(entities=(BLOCKED, PLAYER))
    personality = cards(inventory, installed=date(2026, 11, 8))[CardId.PERSONALITY]
    assert personality.state is CardState.COUNTING
    assert personality.ready_on == date(2026, 11, 15)

    history = {UPTIME.entity_id: Statistic(UPTIME.entity_id, "s", first=LONG_AGO)}
    inventory = Inventory(entities=(UPTIME,), statistics=history)  # uptime and restarts
    assert cards(inventory, installed=date(2026, 11, 8))[CardId.PERSONALITY].state is (
        CardState.READY
    )

    alone = cards(Inventory(entities=(BLOCKED,)))[CardId.PERSONALITY]
    assert alone.state is CardState.LOCKED
    assert {"Glances", "Jellyfin"} <= set(alone.unlock)


def test_as_dict() -> None:
    blocked = cards(Inventory(entities=(BLOCKED,)))[CardId.BLOCKED]
    assert blocked.as_dict() == {
        "card": "blocked",
        "number": 4,
        "state": "counting",
        "since": "2026-11-11",
        "ready_on": "2026-11-18",
        "sources": ["AdGuard Home"],
        "unlock": [],
        "hints": [],
    }


def test_what_the_recorder_still_had_counts_as_history() -> None:
    """Installed today, but the look-back found ten days of blocked counts: ready now."""
    started = Entity(
        "sensor.web_started",
        "sensor",
        "portainer",
        device_class="timestamp",
        translation_key="container_started_at",
    )
    result = cards(
        Inventory(
            entities=(BLOCKED, PLAYER, started),
            backfilled={
                "sensor.blocked": date(2026, 11, 1),
                "sensor.web_started": date(2026, 11, 2),
            },
        )
    )
    assert result[CardId.BLOCKED].state is CardState.READY
    assert result[CardId.BLOCKED].since == date(2026, 11, 1)
    assert result[CardId.MEDIA].state is CardState.COUNTING  # nothing found for the player
    # Container start times feed the Restarts card, not Uptime.
    assert result[CardId.RESTARTS].state is CardState.READY
    assert result[CardId.RESTARTS].sources == ("Portainer",)
    assert result[CardId.UPTIME].state is CardState.LOCKED


def test_which_years_can_be_played() -> None:
    """In January the year that just ended comes first; after that, this year."""
    cards = [
        CardCoverage(CardId.UPTIME, CardState.READY, since=date(2025, 3, 1)),
        CardCoverage(CardId.BLOCKED, CardState.COUNTING, since=date(2026, 11, 2)),
        CardCoverage(CardId.MEDIA, CardState.LOCKED),
    ]
    assert wrapped_years(cards, date(2027, 1, 5)) == ([2025, 2026, 2027], 2026)
    assert wrapped_years(cards, date(2027, 2, 1)) == ([2025, 2026, 2027], 2027)
    assert wrapped_years(cards, date(2026, 12, 31)) == ([2025, 2026], 2026)
    # Nothing from last year: January is this year's, however short.
    assert wrapped_years([], date(2027, 1, 5)) == ([2027], 2027)


def test_a_ups_alone_makes_the_power_card() -> None:
    """Power cuts make the card before any meter is picked; picking meters is still hinted."""
    ups = Entity("sensor.ups_status", "sensor", "nut", translation_key="ups_status")
    power = cards(Inventory(entities=(ups,)), installed=LONG_AGO)[CardId.POWER]
    assert power.state is CardState.READY
    assert power.sources == ("Network UPS Tools",)
    assert power.hints == (Hint.PICK_METERS,)
