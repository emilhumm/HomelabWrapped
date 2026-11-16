"""What the story cards say."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from custom_components.homelab_wrapped.core.cards import (
    Daily,
    Hourly,
    Kind,
    Machine,
    Price,
    Service,
    Ups,
    Year,
    blocked_card,
    intro_card,
    machine_streaks,
    media_card,
    merge_machines,
    personality_card,
    power_card,
    price_unit,
    restarts_card,
    to_kwh,
    uptime_card,
)

TZ = ZoneInfo("Europe/Copenhagen")
NOW = datetime(2026, 11, 11, 12, tzinfo=TZ)
YEAR = Year.of(2026, now=NOW, tz=TZ)


def day(month: int, dom: int, hour: int = 12) -> datetime:
    return datetime(2026, month, dom, hour, tzinfo=TZ)


def test_year() -> None:
    assert YEAR.start == datetime(2026, 1, 1, tzinfo=TZ)
    assert YEAR.end == NOW
    assert YEAR.number == 2026
    assert len(YEAR.days()) == 315
    assert YEAR.days()[-1] == date(2026, 11, 11)
    assert day(3, 1) in YEAR
    assert datetime(2025, 12, 31, 23, tzinfo=TZ) not in YEAR
    assert "2026-03-01" not in YEAR
    last_year = Year.of(2025, now=NOW, tz=TZ)
    assert last_year.end == datetime(2026, 1, 1, tzinfo=TZ)
    assert last_year.days()[-1] == date(2025, 12, 31)
    assert Year.of(2027, now=NOW, tz=TZ).end == datetime(2027, 1, 1, tzinfo=TZ)
    # Midnight in Copenhagen is still the previous day in UTC.
    assert YEAR.day(datetime(2026, 6, 1, 22, 30, tzinfo=UTC)) == date(2026, 6, 2)


def test_streaks_between_restarts() -> None:
    machine = Machine("nas", (day(3, 1), day(9, 1)), since=day(1, 10))
    streaks = machine_streaks(machine, NOW)
    assert [(s.start, s.end) for s in streaks] == [
        (day(1, 10), day(3, 1)),
        (day(3, 1), day(9, 1)),
        (day(9, 1), NOW),
    ]
    assert streaks[0].open_start
    assert not streaks[1].open_start
    assert streaks[-1].ongoing


def test_exact_boot_time_replaces_the_hourly_restart() -> None:
    boot = day(9, 1, 12) + timedelta(minutes=37)
    machine = Machine("nas", (day(3, 1), day(9, 1, 12)), since=day(1, 10), last_boot=boot)
    assert machine_streaks(machine, NOW)[-1].start == boot


def test_boot_before_the_data_starts_gives_the_whole_streak() -> None:
    """Wrapped was installed in November; the machine has been up since last year."""
    boot = datetime(2025, 8, 1, tzinfo=TZ)
    machine = Machine("nas", (), since=day(11, 9), last_boot=boot)
    (streak,) = machine_streaks(machine, NOW)
    assert streak.start == boot
    assert not streak.open_start
    assert streak.ongoing
    assert machine_streaks(Machine("x", (), since=None, last_boot=boot), NOW)[0].start == boot
    assert machine_streaks(Machine("x"), NOW) == []


def test_merge_machines() -> None:
    merged = merge_machines(
        "nas",
        [
            Machine("a", (day(3, 1, 12),), since=day(2, 1), last_boot=day(3, 1, 12)),
            Machine("b", (day(3, 1, 13), day(5, 1)), since=day(1, 1)),
        ],
    )
    assert merged == Machine("nas", (day(3, 1, 12), day(5, 1)), day(1, 1), day(3, 1, 12))


def test_uptime_card() -> None:
    machines = [
        Machine("router", (day(2, 1), day(6, 1)), since=day(1, 1, 0)),
        Machine("nas", (day(3, 3), day(3, 3, 18)), since=day(1, 5)),
        Machine("vm", (), since=day(11, 1), last_boot=datetime(2025, 12, 24, tzinfo=TZ)),
    ]
    card = uptime_card(machines, YEAR)
    assert card is not None
    assert card["longest"]["name"] == "vm"
    assert card["longest"]["days"] == 322.5
    assert card["longest"]["ongoing"]
    assert [streak["name"] for streak in card["current"]] == ["vm", "nas", "router"]
    assert card["machines"] == 3
    assert card["since"] == "2026-01-01"
    grid = card["grid"]
    assert grid["start"] == "2026-01-01"
    assert len(grid["restarts"]) == 315
    assert grid["restarts"][31] == 1  # 1 February
    assert grid["restarts"][61] == 2  # 3 March
    assert grid["restarts"][0] == 0
    assert uptime_card([Machine("x")], YEAR) is None


def test_grid_is_empty_before_the_data_starts() -> None:
    card = uptime_card([Machine("nas", (), since=day(11, 9))], YEAR)
    assert card is not None
    restarts = card["grid"]["restarts"]
    assert restarts[311] is None  # 8 November
    assert restarts[312:] == [0, 0, 0]


def test_restarts_card() -> None:
    machines = [
        Machine("nas", (day(3, 3, 3), day(3, 3, 4), day(7, 1, 3)), since=day(1, 1)),
        Machine("router", (day(2, 1, 22), datetime(2025, 12, 1, tzinfo=TZ)), since=day(1, 1)),
        Machine("pi", (), since=day(1, 1)),
        # Only watched since November (up 10 days): no restarts, but not "never restarted".
        Machine("new", (), since=day(11, 9), last_boot=day(11, 1)),
        # Data since November too, but known to be up since last year: never restarted.
        Machine("switch", (), since=day(11, 9), last_boot=datetime(2025, 12, 1, tzinfo=TZ)),
        Machine("unknown"),
    ]
    card = restarts_card(machines, YEAR)
    assert card is not None
    assert card["total"] == 4
    assert card["machines"] == [
        {"name": "nas", "restarts": 3},
        {"name": "router", "restarts": 1},
        {"name": "new", "restarts": 0},
        {"name": "pi", "restarts": 0},
        {"name": "switch", "restarts": 0},
    ]
    assert card["never"] == ["pi", "switch"]
    assert card["busiest_day"] == {"date": "2026-03-03", "restarts": 2}
    assert card["by_hour"][3] == 2
    assert card["by_hour"][22] == 1
    assert sum(card["by_weekday"]) == 4
    assert restarts_card([Machine("x")], YEAR) is None


def test_blocked_card() -> None:
    sources = [
        Daily(
            "AdGuard Home", {date(2026, 3, 1): 1000, date(2026, 3, 2): 3000, date(2025, 12, 31): 9}
        ),
        Daily("Pi-hole", {date(2026, 3, 2): 500}),
    ]
    card = blocked_card(sources, YEAR)
    assert card == {
        "card": "blocked",
        "total": 4500,
        "per_day": 2250,
        "days": 2,
        "best_day": {"date": "2026-03-02", "blocked": 3500},
        "since": "2026-03-01",
    }
    assert blocked_card([Daily("x")], YEAR) is None


def test_media_card() -> None:
    sources = [
        Daily("Jellyfin", {date(2026, 9, 5): 3.25, date(2026, 10, 1): 2.0}),
        Daily("Plex", {date(2026, 10, 1): 1.0}),
        Daily("Emby", {}),
    ]
    card = media_card(sources, YEAR)
    assert card is not None
    assert card["hours"] == 6.2
    assert card["by_month"][7] is None  # August: before the data
    assert card["by_month"][8:11] == [3.2, 3.0, 0]
    assert card["by_month"][11] is None  # December hasn't happened
    assert card["best_day"] == {"date": "2026-09-05", "hours": 3.2}
    assert card["servers"] == [{"name": "Jellyfin", "hours": 5.2}, {"name": "Plex", "hours": 1.0}]
    assert card["since"] == "2026-09-05"
    assert card["titles"] == []
    assert media_card([], YEAR) is None

    titles = {"Severance": 10.04, "Dune": 2.5, "a": 1, "b": 1, "c": 1, "d": 1, "tiny": 0.01}
    card = media_card(sources, YEAR, titles)
    assert card is not None
    assert card["titles"] == [
        {"title": "Severance", "hours": 10.0},
        {"title": "Dune", "hours": 2.5},
        {"title": "a", "hours": 1.0},
        {"title": "b", "hours": 1.0},
        {"title": "c", "hours": 1.0},
    ]


def test_intro_card() -> None:
    card = intro_card({"host": 1, "guest": 4}, machines=6, since=date(2026, 5, 13))
    assert card == {
        "card": "intro",
        "hosts": 1,
        "guests": 4,
        "containers": 0,
        "machines": 6,
        "since": "2026-05-13",
    }
    assert intro_card({"uptime": 3}, machines=3, since=None) is None


H0 = datetime(2026, 7, 1, 10, tzinfo=UTC)


def hour(n: int) -> datetime:
    return H0 + timedelta(hours=n)


def test_energy_and_price_units() -> None:
    assert to_kwh(1500, "Wh") == 1.5
    assert to_kwh(2, "MWh") == 2000
    assert to_kwh(1, "kW") is None
    assert price_unit("DKK/kWh") == ("DKK", 1.0)
    assert price_unit("EUR/MWh") == ("EUR", 0.001)
    assert price_unit("€/Wh") == ("€", 1000.0)
    assert price_unit("%") is None
    assert price_unit(None) is None


def test_power_priced_hour_by_hour() -> None:
    meters = [
        Hourly(
            "rack", {hour(0): 0.1, hour(1): 0.1, hour(2): 0.1, datetime(2025, 7, 1, tzinfo=UTC): 9}
        ),
        Hourly("ups", {hour(0): 0.05, hour(1): 0.05}),
        Hourly("unplugged", {}),
    ]
    # The price sensor was down for the third hour: it's priced at the average.
    price = Price("DKK", {hour(0): 2.0, hour(1): 1.0})
    card = power_card(meters, price, YEAR)
    assert card == {
        "card": "power",
        "kwh": 0.4,
        "watts": 133,
        "cost": 0.6,
        "currency": "DKK",
        "average_price": 1.5,
        "estimated": True,
        "by_month": [None] * 6 + [0.4] + [None] * 5,
        "meters": [{"name": "rack", "kwh": 0.3}, {"name": "ups", "kwh": 0.1}],
        "power_cuts": None,
        "since": "2026-07-01",
    }


def test_power_with_a_fixed_price_or_none() -> None:
    meters = [Hourly("rack", {hour(0): 1.0, hour(1): 1.0})]
    fixed = power_card(meters, Price("EUR", fixed=0.3), YEAR)
    assert fixed is not None
    assert (fixed["cost"], fixed["currency"], fixed["estimated"]) == (0.6, "EUR", False)
    unpriced = power_card(meters, None, YEAR)
    assert unpriced is not None
    assert (unpriced["cost"], unpriced["currency"], unpriced["average_price"]) == (None, None, None)
    no_history = power_card(meters, Price("DKK"), YEAR)
    assert no_history is not None
    assert no_history["cost"] is None
    assert power_card([Hourly("rack")], None, YEAR) is None


def restarts_stats(
    total: int, *, night: int = 0, weekend: int = 0, machines: int = 2
) -> dict[str, object]:
    by_hour = [0] * 24
    by_hour[3], by_hour[12] = night, total - night
    by_weekday = [0] * 7
    by_weekday[5], by_weekday[1] = weekend, total - weekend
    return {
        "card": "restarts",
        "total": total,
        "machines": [{"name": f"m{n}", "restarts": 1} for n in range(machines)],
        "never": [],
        "by_hour": by_hour,
        "by_weekday": by_weekday,
        "since": "2026-01-01",
    }


def uptime_stats(days: float) -> dict[str, object]:
    return {"card": "uptime", "longest": {"days": days}, "since": "2026-01-01"}


def test_personality_picks_the_strongest_trait() -> None:
    cards = [
        {"card": "intro", "guests": 4, "containers": 30},
        uptime_stats(320),
        restarts_stats(6, night=1),
        {"card": "blocked", "per_day": 9000, "since": "2026-01-01"},
    ]
    card = personality_card(cards, YEAR)
    assert card is not None
    assert card["key"] == "rock"
    assert [trait["key"] for trait in card["traits"]] == ["rock", "collector", "gatekeeper"]
    assert card["traits"][0] == {"key": "rock", "value": 320, "score": 0.88}


def test_night_owls_and_weekend_warriors() -> None:
    night = personality_card([uptime_stats(10), restarts_stats(20, night=18)], YEAR)
    assert night is not None
    assert night["key"] == "night_owl"
    assert night["traits"][0]["value"] == 90  # percent at night
    weekend = personality_card([uptime_stats(10), restarts_stats(20, weekend=15)], YEAR)
    assert weekend is not None
    assert weekend["key"] == "weekend_warrior"


def test_tinkerer_cinephile_and_power() -> None:
    tinkerer = personality_card([uptime_stats(3), restarts_stats(300, machines=1)], YEAR)
    assert tinkerer is not None
    assert tinkerer["key"] == "tinkerer"
    movies = [{"card": "media", "hours": 100, "since": "2026-11-01"}, uptime_stats(40)]
    cinephile = personality_card(movies, YEAR)
    assert cinephile is not None
    assert cinephile["key"] == "cinephile"
    # Without a start date, the whole year so far counts: 100 hours over 314 days.
    slow = personality_card(
        [{"card": "media", "hours": 100, "since": None}, uptime_stats(40)], YEAR
    )
    assert slow is not None
    assert slow["traits"][1] == {"key": "cinephile", "value": 0.3, "score": 0.08}
    sipper = personality_card([{"card": "power", "watts": 12}, uptime_stats(20)], YEAR)
    assert sipper is not None
    assert sipper["key"] == "sipper"
    plant = personality_card([{"card": "power", "watts": 480}, uptime_stats(20)], YEAR)
    assert plant is not None
    assert plant["key"] == "power_plant"


def test_nothing_stands_out() -> None:
    card = personality_card(
        [uptime_stats(40), {"card": "blocked", "per_day": 500, "since": None}], YEAR
    )
    assert card is not None
    assert card["key"] == "all_rounder"
    assert [trait["key"] for trait in card["traits"]] == ["rock", "gatekeeper"]
    assert personality_card([uptime_stats(400), {"card": "intro"}], YEAR) is None


def test_containers_get_their_own_ranking() -> None:
    """One reboot of a Docker host restarts every container: they don't crowd out the machines."""
    machines = [
        Machine("nas", (day(3, 1),), since=day(1, 1, 0)),
        Machine(
            "web",
            (day(11, 2, 13), day(11, 2, 14), day(11, 4)),
            since=day(11, 1),
            kind=Kind.CONTAINER,
        ),
        Machine("db", (day(11, 4),), since=day(11, 1), kind=Kind.CONTAINER),
        Machine("idle", (), since=day(11, 1), kind=Kind.CONTAINER),
        Machine("gone", (), kind=Kind.CONTAINER),  # no data at all
    ]
    card = restarts_card(machines, YEAR)
    assert card is not None
    assert (card["total"], card["machines"], card["never"]) == (
        1,
        [{"name": "nas", "restarts": 1}],
        [],
    )
    assert card["containers"] == {
        "total": 4,
        "watched": 3,
        "top": [{"name": "web", "restarts": 3}, {"name": "db", "restarts": 1}],
        "since": "2026-11-01",
    }
    uptime = uptime_card(machines, YEAR)
    assert uptime is not None
    assert uptime["machines"] == 1
    assert [streak["name"] for streak in uptime["current"]] == ["nas"]


def test_machines_with_the_same_name_are_counted_apart() -> None:
    """Two VMs called "docker" (clones, or on two nodes) are two machines."""
    machines = [
        Machine("docker", (day(3, 1), day(4, 1), day(5, 1)), since=day(1, 1, 0)),
        Machine("docker", (day(6, 1),), since=day(1, 1, 0)),
        Machine("docker", (), since=day(1, 1, 0)),
    ]
    card = restarts_card(machines, YEAR)
    assert card is not None
    assert card["total"] == 4
    assert card["machines"] == [
        {"name": "docker", "restarts": 3},
        {"name": "docker", "restarts": 1},
        {"name": "docker", "restarts": 0},
    ]
    assert card["never"] == ["docker"]


def test_time_not_running_is_no_streak() -> None:
    """A VM off for six weeks isn't up for them; one stopped now (or retired) isn't up right
    now, and a template that never runs neither has a streak nor "never restarted"."""
    vm = Machine(
        "vm",
        (day(3, 1),),
        since=day(1, 1, 0),
        down=((day(3, 1), day(4, 12)), (day(10, 1), None)),
    )
    streaks = machine_streaks(vm, NOW)
    assert [(s.start, s.end, s.ongoing) for s in streaks] == [
        (day(1, 1, 0), day(3, 1), False),
        (day(4, 12), day(10, 1), False),
    ]
    template = Machine("template", (), since=day(1, 1, 0), down=((day(1, 1, 0), None),))
    assert machine_streaks(template, NOW) == []
    card = uptime_card([vm, template, Machine("pve", (), since=day(1, 1, 0))], YEAR)
    assert card is not None
    assert [streak["name"] for streak in card["current"]] == ["pve"]
    assert card["over"] is False
    restarts = restarts_card([template, Machine("pve", (), since=day(1, 1, 0))], YEAR)
    assert restarts is not None
    assert restarts["never"] == ["pve"]


def test_a_past_year_and_last_years_streaks() -> None:
    """2027's card doesn't show a streak that ended in 2026 (the look-back reaches back), and
    a past year's card says so."""
    later = Year.of(2027, now=datetime(2027, 3, 1, tzinfo=TZ), tz=TZ)
    old = Machine(
        "old", (datetime(2026, 12, 5, tzinfo=TZ),), since=datetime(2026, 11, 2, tzinfo=TZ)
    )
    card = uptime_card([old], later)
    assert card is not None
    assert card["longest"]["start"].startswith("2026-12-05")
    past = Year.of(2026, now=datetime(2027, 1, 5, tzinfo=TZ), tz=TZ)
    assert past.over
    assert not YEAR.over


def test_network_gear_gets_its_own_ranking() -> None:
    """Routers, access points and the firewall serve the lab: a ranking of their own, and
    not in the streaks (on the first real lab two access points headed "up right now")."""
    machines = [
        Machine("pve", (day(3, 1),), since=day(1, 1, 0)),
        Machine("ap", (day(5, 2), day(9, 3)), since=day(1, 1, 0), kind=Kind.NETWORK),
        Machine("firewall", (day(10, 30),), since=day(1, 1, 0), kind=Kind.NETWORK),
    ]
    card = restarts_card(machines, YEAR)
    assert card is not None
    assert (card["total"], card["machines"]) == (1, [{"name": "pve", "restarts": 1}])
    assert card["network"] == {
        "total": 3,
        "watched": 2,
        "top": [{"name": "ap", "restarts": 2}, {"name": "firewall", "restarts": 1}],
        "since": "2026-01-01",
    }
    assert card["containers"] is None
    uptime = uptime_card(machines, YEAR)
    assert uptime is not None
    assert uptime["machines"] == 1
    assert [streak["name"] for streak in uptime["current"]] == ["pve"]

    # A lab Wrapped sees only network gear and containers of: the Restarts card is theirs.
    gear = [*machines[1:], Machine("web", (day(11, 2),), since=day(11, 1), kind=Kind.CONTAINER)]
    only = restarts_card(gear, YEAR)
    assert only is not None
    assert (only["total"], only["machines"]) == (0, [])
    assert (only["network"]["total"], only["containers"]["total"]) == (3, 1)
    assert only["since"] == "2026-01-01"  # the earlier of the two
    assert uptime_card(gear, YEAR) is None


def test_a_restarts_card_of_containers_only() -> None:
    containers = [Machine("web", (day(11, 2),), since=day(11, 1), kind=Kind.CONTAINER)]
    card = restarts_card(containers, YEAR)
    assert card is not None
    assert (card["total"], card["machines"], card["busiest_day"]) == (0, [], None)
    assert card["containers"]["total"] == 1
    assert card["since"] == "2026-11-01"
    assert uptime_card(containers, YEAR) is None
    assert restarts_card([Machine("web", kind=Kind.CONTAINER)], YEAR) is None
    assert (
        restarts_card([Machine("nas", (day(3, 1),), since=day(1, 1))], YEAR)["containers"] is None
    )  # type: ignore[index]


def test_services_on_the_uptime_card() -> None:
    services = [
        Service("web", 99.9),
        Service("dns", 100.0),
        Service("vpn", 97.5),
        Service("nas", 99.0),
    ]
    card = uptime_card([Machine("pve", since=day(1, 1))], YEAR, services)
    assert card is not None
    assert card["services"] == {
        "count": 4,
        "uptime": 99.1,
        "least": [
            {"name": "vpn", "uptime": 97.5},
            {"name": "nas", "uptime": 99.0},
            {"name": "web", "uptime": 99.9},
        ],
    }
    assert uptime_card([Machine("pve", since=day(1, 1))], YEAR)["services"] is None  # type: ignore[index]

    # Only Uptime Kuma: the card has the services, and no streaks.
    only = uptime_card([], YEAR, services)
    assert only is not None
    assert (only["longest"], only["current"], only["machines"], only["since"]) == (
        None,
        [],
        0,
        None,
    )
    assert set(only["grid"]["restarts"]) == {None}
    assert uptime_card([], YEAR) is None
    blocked = blocked_card([Daily("AdGuard", {date(2026, 10, 1): 30_000.0})], YEAR)
    assert blocked is not None
    personality = personality_card([only, blocked], YEAR)
    assert personality is not None
    assert [trait["key"] for trait in personality["traits"]] == ["gatekeeper"]


def test_power_cuts_on_the_power_card() -> None:
    long_ago = day(1, 1) - timedelta(days=400)
    ups = Ups("UPS", ((day(3, 1), 300.0), (day(6, 2), 1800.0), (long_ago, 60.0)), day(1, 1))
    meters = [Hourly("Rack", {day(3, 1, h): 0.1 for h in range(24)})]
    card = power_card(meters, None, YEAR, [ups])
    assert card is not None
    assert card["power_cuts"] == {
        "count": 2,  # the third was in another year
        "minutes": 35,
        "longest_minutes": 30.0,
        "seconds": 2100,
        "longest_seconds": 1800,
        "since": "2026-01-01",
    }
    assert power_card(meters, None, YEAR)["power_cuts"] is None  # type: ignore[index]
    assert power_card(meters, None, YEAR, [Ups("new")])["power_cuts"] is None  # type: ignore[index]

    # A UPS but no meters picked: the card has the power cuts only.
    only = power_card([], None, YEAR, [Ups("UPS", (), day(10, 1))])
    assert only is not None
    assert (only["kwh"], only["watts"], only["meters"]) == (None, None, [])
    assert only["power_cuts"] == {
        "count": 0,
        "minutes": 0,
        "longest_minutes": 0.0,
        "seconds": 0,
        "longest_seconds": 0,
        "since": "2026-10-01",
    }
    assert power_card([], None, YEAR) is None

    nine = tuple((day(month, 1), 60.0) for month in range(1, 10))
    survivor = power_card([], None, YEAR, [Ups("UPS", nine, day(1, 1))])
    blocked = blocked_card([Daily("AdGuard", {date(2026, 10, 1): 100.0})], YEAR)
    assert survivor is not None
    assert blocked is not None
    personality = personality_card([survivor, blocked], YEAR)
    assert personality is not None
    assert personality["key"] == "survivor"
    assert personality["traits"][0] == {"key": "survivor", "value": 9, "score": 0.75}


def test_nothing_watched_yet_in_an_earlier_year() -> None:
    """The year switch offers 2025 (uptime statistics go back that far); what Wrapped only
    watched since 2026 isn't on 2025's cards."""
    last_year = Year.of(2025, now=NOW, tz=TZ)
    old = Machine("pve", (datetime(2025, 3, 1, tzinfo=TZ),), datetime(2025, 1, 1, tzinfo=TZ))
    new = Machine("nas", (), day(11, 1))
    container = Machine("web", (day(11, 2),), day(11, 1), kind=Kind.CONTAINER)
    card = restarts_card([old, new, container], last_year)
    assert card is not None
    assert card["machines"] == [{"name": "pve", "restarts": 1}]
    assert card["containers"] is None
    assert power_card([], None, last_year, [Ups("UPS", (), day(11, 1))]) is None
