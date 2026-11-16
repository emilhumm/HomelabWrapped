"""What each story card says, built from plain histories.

The HA layer turns long-term statistics into ``Machine`` (restart times) and
``Daily`` (an amount per day); the functions here turn those into JSON-friendly
dicts for the panel. A card function returns None when there is nothing to show.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta, tzinfo
from enum import StrEnum
from itertools import pairwise
from typing import Any

from .uptime import Streak, merge_restarts

SAME_RESTART = timedelta(hours=2)
"""Restarts this close together are one (hourly statistics vs. an exact boot time)."""

TOP = 5
"""How many machines a ranking shows."""

KWH_PER_UNIT = {"Wh": 0.001, "kWh": 1.0, "MWh": 1000.0}


@dataclass(frozen=True, slots=True)
class Year:
    """The period a Wrapped covers: one calendar year, up to now if it's this year."""

    start: datetime
    end: datetime
    tz: tzinfo

    @classmethod
    def of(cls, year: int, *, now: datetime, tz: tzinfo) -> Year:
        """``year`` in the time zone ``tz``, cut off at ``now``."""
        start = datetime(year, 1, 1, tzinfo=tz)
        return cls(start, max(start, min(now, datetime(year + 1, 1, 1, tzinfo=tz))), tz)

    @property
    def number(self) -> int:
        """The year itself."""
        return self.start.year

    @property
    def over(self) -> bool:
        """The whole calendar year is in: a past year (not this one, so far)."""
        return self.end >= datetime(self.number + 1, 1, 1, tzinfo=self.tz)

    def day(self, moment: datetime) -> date:
        """The local date of a moment."""
        return moment.astimezone(self.tz).date()

    def days(self) -> list[date]:
        """Every day of the period so far, in order."""
        first = self.start.date()
        last = self.day(self.end - timedelta(microseconds=1)) if self.end > self.start else first
        return [first + timedelta(days=n) for n in range((last - first).days + 1)]

    def __contains__(self, moment: object) -> bool:
        """Whether a moment falls in the period."""
        return isinstance(moment, datetime) and self.start <= moment < self.end


class Kind(StrEnum):
    """What a machine is, which decides where it shows."""

    SERVER = "server"
    """A host, VM or NAS: the streaks, the restarts and the machine counts."""
    CONTAINER = "container"
    """A Docker container: a ranking of its own on the Restarts card. It restarts with
    its host, and with every update."""
    NETWORK = "network"
    """A router, firewall, access point or switch: a ranking of its own on the Restarts
    card. It serves the lab, but isn't one of its machines."""


@dataclass(frozen=True, slots=True)
class Machine:
    """One machine's restarts: a server's, a Docker container's or a piece of network gear's."""

    name: str
    restarts: tuple[datetime, ...] = ()
    """Restart times, merged from every source that saw this machine."""
    since: datetime | None = None
    """Where its data starts; None if there's no history at all."""
    last_boot: datetime | None = None
    """Its latest boot time, exact, when an uptime sensor tells it."""
    kind: Kind = Kind.SERVER
    down: tuple[tuple[datetime, datetime | None], ...] = ()
    """When it wasn't running (a stopped VM), or since it was retired (None: still): no
    streak runs through these."""


@dataclass(frozen=True, slots=True)
class Service:
    """A service a monitor watches (Uptime Kuma), and how much of the past year it was up."""

    name: str
    uptime: float
    """Percent, over the 365 days up to the end of the period."""


@dataclass(frozen=True, slots=True)
class Ups:
    """A UPS, and the power cuts it rode out."""

    name: str
    cuts: tuple[tuple[datetime, float], ...] = ()
    """(start, seconds)."""
    since: datetime | None = None
    """Watched since: where its data starts."""


@dataclass(frozen=True, slots=True)
class Daily:
    """An amount per local day, such as blocked queries or hours played."""

    name: str
    days: Mapping[date, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Hourly:
    """An amount per hour (keyed by the hour's start), such as the kWh a meter counted."""

    name: str
    hours: Mapping[datetime, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Price:
    """What a kWh cost: hourly prices (keyed like ``Hourly``), else one fixed price."""

    currency: str | None
    hourly: Mapping[datetime, float] = field(default_factory=dict)
    fixed: float | None = None


def to_kwh(value: float, unit: str | None) -> float | None:
    """An energy amount in kWh, or None for a unit that isn't energy."""
    factor = KWH_PER_UNIT.get(unit or "")
    return None if factor is None else value * factor


def price_unit(unit: str | None) -> tuple[str, float] | None:
    """("DKK", factor) for "DKK/MWh": the currency, and what turns the price into per kWh."""
    currency, _, energy = (unit or "").partition("/")
    factor = KWH_PER_UNIT.get(energy)
    return None if not currency or factor is None else (currency.strip(), 1 / factor)


def machine_streaks(machine: Machine, now: datetime) -> list[Streak]:
    """A machine's stretches without a restart, oldest first; the last one may be ongoing.

    The latest boot time, when known, is exact: it replaces the hourly restart
    it matches, and when it lies before the data starts, the current streak is
    known to start there.
    """
    found = _streaks(machine, now)
    for start, end in machine.down:
        found = [piece for streak in found for piece in _cut(streak, start, end or now)]
    return found


def _cut(streak: Streak, start: datetime, end: datetime) -> list[Streak]:
    """A streak without the time from ``start`` to ``end``, when the machine wasn't up."""
    if end <= streak.start or start >= streak.end:
        return [streak]
    pieces = []
    if start > streak.start:
        pieces.append(replace(streak, end=start, ongoing=False))
    if end < streak.end:
        pieces.append(replace(streak, start=end, open_start=False))
    return pieces


def _streaks(machine: Machine, now: datetime) -> list[Streak]:
    since, boot = machine.since, machine.last_boot
    points = sorted(moment for moment in machine.restarts if since is None or since < moment < now)
    if boot is not None and boot < now:
        if since is None or (boot <= since and not points):
            return [Streak(boot, now, ongoing=True, open_start=False)]
        if boot > since:
            points = [moment for moment in points if moment < boot - SAME_RESTART] + [boot]
    if since is None or since >= now:
        return []
    edges = [since, *points, now]
    return [
        Streak(start, end, ongoing=end == now, open_start=start == since)
        for start, end in pairwise(edges)
        if end > start
    ]


def merge_machines(name: str, parts: Iterable[Machine], *, kind: Kind = Kind.SERVER) -> Machine:
    """One machine from several sources that saw it (two uptime sensors on one device)."""
    parts = list(parts)
    sinces = [part.since for part in parts if part.since is not None]
    boots = [part.last_boot for part in parts if part.last_boot is not None]
    return Machine(
        name,
        tuple(merge_restarts(*(part.restarts for part in parts), window=SAME_RESTART)),
        min(sinces) if sinces else None,
        max(boots) if boots else None,
        kind,
    )


def intro_card(
    counts: Mapping[str, int], *, machines: int, since: date | None
) -> dict[str, Any] | None:
    """Card 01: what the lab is made of."""
    hosts, guests, containers = (counts.get(kind, 0) for kind in ("host", "guest", "container"))
    if not hosts + guests + containers:
        return None
    return {
        "card": "intro",
        "hosts": hosts,
        "guests": guests,
        "containers": containers,
        "machines": machines,
        "since": _iso(since),
    }


def uptime_card(
    machines: Sequence[Machine], year: Year, services: Sequence[Service] = ()
) -> dict[str, Any] | None:
    """Card 02: the longest streak without a restart, current streaks, the year grid,
    and how much of the year the monitored services were up.

    Servers only: a container restarts with its host and with every update, and
    network gear isn't one of the lab's machines. A lab with monitored services but
    no server uptime still gets the card, without streaks.
    """
    machines = [machine for machine in machines if machine.kind is Kind.SERVER]
    # A streak that ended before the year began is last year's (the look-back reaches back).
    streaks = [
        (machine, [s for s in machine_streaks(machine, year.end) if s.end > year.start])
        for machine in machines
    ]
    streaks = [(machine, found) for machine, found in streaks if found]
    watched = _services(services)
    if not streaks:
        if watched is None:
            return None
        return {
            "card": "uptime",
            "longest": None,
            "current": [],
            "machines": 0,
            "grid": _grid([], year),
            "services": watched,
            "since": None,
        }
    best_machine, best = max(
        ((machine, streak) for machine, found in streaks for streak in found),
        key=lambda pair: pair[1].length,
    )
    current = sorted(
        ((machine, found[-1]) for machine, found in streaks if found[-1].ongoing),
        key=lambda pair: pair[1].length,
        reverse=True,
    )
    return {
        "card": "uptime",
        "longest": _streak(best_machine, best),
        "current": [_streak(machine, streak) for machine, streak in current[:TOP]],
        "machines": len(streaks),
        "grid": _grid(machines, year),
        "services": watched,
        "since": _iso(_since(machines, year)),
        # A past year: "up at year end", not "up right now".
        "over": year.over,
    }


def _services(services: Sequence[Service]) -> dict[str, Any] | None:
    """The services' part of the Uptime card: their average uptime, and the least reliable."""
    if not services:
        return None
    ranked = sorted(services, key=lambda service: (service.uptime, service.name))
    return {
        "count": len(services),
        "uptime": round(sum(service.uptime for service in services) / len(services), 3),
        "least": [
            {"name": service.name, "uptime": round(service.uptime, 3)}
            for service in ranked[:3]
            if service.uptime < 100
        ],
    }


def restarts_card(machines: Sequence[Machine], year: Year) -> dict[str, Any] | None:
    """Card 03: what restarted most, and when restarts happen.

    The totals, ranking and times are the servers'. Containers get their own
    ranking, since one reboot of a Docker host restarts every container on it, and
    so does network gear (routers, access points, the firewall).
    """
    containers = _group(machines, year, Kind.CONTAINER)
    network = _group(machines, year, Kind.NETWORK)
    watched = [m for m in machines if _watched_in(m.since, year) and m.kind is Kind.SERVER]
    if not watched:
        groups = [group for group in (containers, network) if group]
        if not groups:
            return None
        return {
            "card": "restarts",
            "total": 0,
            "machines": [],
            "never": [],
            "busiest_day": None,
            "by_hour": [0] * 24,
            "by_weekday": [0] * 7,
            "containers": containers,
            "network": network,
            "since": min(group["since"] for group in groups),
        }
    # Per machine, not per name: two VMs can share one (clones, or on two nodes).
    per_machine = [
        (machine, [moment for moment in machine.restarts if moment in year]) for machine in watched
    ]
    moments = [moment for _, found in per_machine for moment in found]
    by_day = Counter(year.day(moment) for moment in moments)
    by_hour = Counter(moment.astimezone(year.tz).hour for moment in moments)
    by_weekday = Counter(moment.astimezone(year.tz).weekday() for moment in moments)
    ranking = sorted(per_machine, key=lambda item: (-len(item[1]), item[0].name))
    busiest = max(by_day.items(), key=lambda item: (item[1], item[0]), default=None)
    return {
        "card": "restarts",
        "total": len(moments),
        "machines": [
            {"name": machine.name, "restarts": len(found)} for machine, found in ranking[:TOP]
        ],
        "never": sorted(
            machine.name
            for machine, found in per_machine
            if not found
            and _watched_most(machine, watched, year)
            and not _down_at(machine, year.end)  # a stopped template didn't "never restart"
        ),
        "busiest_day": {"date": busiest[0].isoformat(), "restarts": busiest[1]}
        if busiest
        else None,
        "by_hour": [by_hour[hour] for hour in range(24)],
        "by_weekday": [by_weekday[day] for day in range(7)],
        "containers": containers,
        "network": network,
        "since": _iso(_since(watched, year)),
    }


def _group(machines: Sequence[Machine], year: Year, kind: Kind) -> dict[str, Any] | None:
    """The containers' or the network gear's part of the Restarts card: how often, and
    which ones most."""
    watched = [m for m in machines if _watched_in(m.since, year) and m.kind is kind]
    if not watched:
        return None
    counts = sorted(
        ((m.name, sum(moment in year for moment in m.restarts)) for m in watched),
        key=lambda item: (-item[1], item[0]),
    )
    return {
        "total": sum(count for _, count in counts),
        "watched": len(watched),
        "top": [{"name": name, "restarts": count} for name, count in counts[:TOP] if count],
        "since": _iso(_since(watched, year)),
    }


def blocked_card(sources: Sequence[Daily], year: Year) -> dict[str, Any] | None:
    """Card 04: DNS queries blocked."""
    days = _in_year(sources, year)
    if not days:
        return None
    total = sum(days.values())
    best = max(days.items(), key=lambda item: (item[1], item[0]))
    return {
        "card": "blocked",
        "total": round(total),
        "per_day": round(total / len(days)),
        "days": len(days),
        "best_day": {"date": best[0].isoformat(), "blocked": round(best[1])},
        "since": min(days).isoformat(),
    }


def media_card(
    sources: Sequence[Daily], year: Year, titles: Mapping[str, float] | None = None
) -> dict[str, Any] | None:
    """Card 05: hours played, by month, by media server and the most played titles.

    ``titles`` are the hours per title (series, artist or film) in the year.
    """
    days = _in_year(sources, year)
    if not days:
        return None
    months: defaultdict[int, float] = defaultdict(float)
    for day, hours in days.items():
        months[day.month] += hours
    best = max(days.items(), key=lambda item: (item[1], item[0]))
    servers = sorted(
        (
            (source.name, sum(hours for day, hours in source.days.items() if day in days))
            for source in sources
        ),
        key=lambda item: (-item[1], item[0]),
    )
    first, last = min(days), year.day(year.end - timedelta(microseconds=1))
    return {
        "card": "media",
        "hours": round(sum(days.values()), 1),
        "by_month": [
            round(months[month], 1) if first.month <= month <= last.month else None
            for month in range(1, 13)
        ],
        "best_day": {"date": best[0].isoformat(), "hours": round(best[1], 1)},
        "servers": [{"name": name, "hours": round(hours, 1)} for name, hours in servers if hours],
        "titles": [
            {"title": title, "hours": round(hours, 1)}
            for title, hours in sorted(
                (titles or {}).items(), key=lambda item: (-item[1], item[0])
            )[:TOP]
            if round(hours, 1) > 0
        ],
        "since": first.isoformat(),
    }


def power_card(
    meters: Sequence[Hourly], price: Price | None, year: Year, ups: Sequence[Ups] = ()
) -> dict[str, Any] | None:
    """Card 06: what the lab used, what it cost, its average draw, and the power cuts
    its UPS rode out.

    A lab with a UPS but no meters picked gets the card with the power cuts only.
    """
    cuts = _power_cuts(ups, year)
    hours: defaultdict[datetime, float] = defaultdict(float)
    per_meter: list[tuple[str, float]] = []
    for meter in meters:
        used = 0.0
        for moment, kwh in meter.hours.items():
            if moment in year and kwh > 0:
                hours[moment] += kwh
                used += kwh
        per_meter.append((meter.name, used))
    if not hours:
        if cuts is None:
            return None
        return {
            "card": "power",
            "kwh": None,
            "watts": None,
            "cost": None,
            "currency": None,
            "average_price": None,
            "estimated": False,
            "by_month": [None] * 12,
            "meters": [],
            "power_cuts": cuts,
            "since": cuts["since"],
        }
    kwh = sum(hours.values())
    cost, priced = _cost(hours, price)
    first, last = min(hours), max(hours)
    span = (min(year.end, last + timedelta(hours=1)) - first) / timedelta(hours=1)
    months: defaultdict[int, float] = defaultdict(float)
    for moment, used in hours.items():
        months[moment.astimezone(year.tz).month] += used
    first_month, last_month = year.day(first).month, year.day(last).month
    return {
        "card": "power",
        "kwh": round(kwh, 1),
        "watts": round(kwh / max(span, 1) * 1000),
        "cost": None if cost is None else round(cost, 2),
        "currency": price.currency if price and cost is not None else None,
        "average_price": None if cost is None else round(cost / kwh, 3),
        "estimated": cost is not None and priced < 0.99,
        "by_month": [
            round(months[month], 1) if first_month <= month <= last_month else None
            for month in range(1, 13)
        ],
        "meters": [
            {"name": name, "kwh": round(used, 1)}
            for name, used in sorted(per_meter, key=lambda item: (-item[1], item[0]))
            if used
        ],
        "power_cuts": cuts,
        "since": year.day(first).isoformat(),
    }


def _power_cuts(ups: Sequence[Ups], year: Year) -> dict[str, Any] | None:
    """The power cuts part of the Power card: how many, for how long, the longest."""
    watched = [unit for unit in ups if _watched_in(unit.since, year)]
    if not watched:
        return None
    cuts = [seconds for unit in watched for start, seconds in unit.cuts if start in year]
    return {
        "count": len(cuts),
        "minutes": round(sum(cuts) / 60),
        "longest_minutes": round(max(cuts, default=0) / 60, 1),
        # Exact, for the panel: most cuts are a flicker of seconds, which "minutes" rounds to 0.
        "seconds": round(sum(cuts)),
        "longest_seconds": round(max(cuts, default=0)),
        "since": _iso(_since([Machine(u.name, since=u.since) for u in watched], year)),
    }


def _cost(hours: Mapping[datetime, float], price: Price | None) -> tuple[float | None, float]:
    """What the hours' kWh cost, and the share of kWh that had a price.

    Hours without an hourly price (the price sensor was down) are priced at the
    average of the hours that had one.
    """
    total = sum(hours.values())
    if price is None:
        return None, 0.0
    priced = {moment: kwh for moment, kwh in hours.items() if moment in price.hourly}
    priced_kwh = sum(priced.values())
    if not priced_kwh:
        return (None, 0.0) if price.fixed is None else (total * price.fixed, 1.0)
    cost = sum(kwh * price.hourly[moment] for moment, kwh in priced.items())
    return cost + (total - priced_kwh) * cost / priced_kwh, priced_kwh / total


def _in_year(sources: Sequence[Daily], year: Year) -> dict[date, float]:
    """Amounts per day over all sources, for days in the period."""
    first, last = year.start.date(), year.day(year.end - timedelta(microseconds=1))
    days: defaultdict[date, float] = defaultdict(float)
    for source in sources:
        for day, amount in source.days.items():
            if first <= day <= last:
                days[day] += amount
    return dict(days)


def _grid(machines: Sequence[Machine], year: Year) -> dict[str, Any]:
    """Restarts per day for the year grid; None for days before any data."""
    sinces = [machine.since for machine in machines if machine.since is not None]
    first = year.day(max(min(sinces), year.start)) if sinces else None
    per_day = Counter(
        year.day(moment) for machine in machines for moment in machine.restarts if moment in year
    )
    return {
        "start": year.start.date().isoformat(),
        "restarts": [None if first is None or day < first else per_day[day] for day in year.days()],
    }


def _streak(machine: Machine, streak: Streak) -> dict[str, Any]:
    return {
        "name": machine.name,
        "days": round(streak.length / timedelta(days=1), 1),
        "start": streak.start.isoformat(),
        "end": streak.end.isoformat(),
        "ongoing": streak.ongoing,
        "open_start": streak.open_start,
    }


NEVER_SHARE = 0.9
"""A machine is "never restarted" only if it was watched for this share of the card's period."""


def _watched_most(machine: Machine, machines: Sequence[Machine], year: Year) -> bool:
    """Whether the machine was watched (its data, or its known boot time) for most of the period.

    A machine Wrapped has only known for days hasn't "never restarted"; one whose
    boot time lies before the data starts has, for as long as the data goes.
    """
    sinces = [m.since for m in machines if m.since is not None]
    card_start = max(min(sinces), year.start) if sinces else year.start
    known = [moment for moment in (machine.since, machine.last_boot) if moment is not None]
    start = max(min(known), year.start) if known else year.end
    return year.end - start >= NEVER_SHARE * (year.end - card_start)


def _down_at(machine: Machine, moment: datetime) -> bool:
    """Whether it wasn't running (or was retired) at ``moment``."""
    return any(start < moment and (end is None or end >= moment) for start, end in machine.down)


def _watched_in(since: datetime | None, year: Year) -> bool:
    """Whether something watched since ``since`` was watched during ``year`` at all."""
    return since is not None and since < year.end


def _since(machines: Sequence[Machine], year: Year) -> date | None:
    sinces = [machine.since for machine in machines if machine.since is not None]
    return year.day(max(min(sinces), year.start)) if sinces else None


def _iso(day: date | None) -> str | None:
    return day.isoformat() if day else None


NIGHT_HOURS = frozenset({22, 23, 0, 1, 2, 3, 4})
WEEKEND = (5, 6)
MIN_TRAIT = 0.35
"""The best trait must score at least this; below it the lab is an all-rounder."""


def personality_card(cards: Sequence[Mapping[str, Any]], year: Year) -> dict[str, Any] | None:
    """Card 07: a personality, picked from what the other cards say.

    Every trait scores 0 to 1 from one number on another card; the best one
    names the lab, and the strongest three explain why. Only keys and numbers
    are returned; the panel words them.
    """
    by_id = {card["card"]: card for card in cards}
    if len(by_id.keys() - {"intro"}) < 2:
        return None
    traits = [trait for trait in _traits(by_id, year) if trait["score"] > 0]
    traits.sort(key=lambda trait: -trait["score"])  # stable: ties keep the order below
    best = traits[0]["key"] if traits and traits[0]["score"] >= MIN_TRAIT else "all_rounder"
    return {"card": "personality", "key": best, "traits": traits[:3], "since": None}


def _traits(cards: Mapping[str, Mapping[str, Any]], year: Year) -> list[dict[str, Any]]:
    """Each trait as {"key", "value" (the number behind it), "score"}."""
    traits: list[dict[str, Any]] = []

    def add(key: str, value: float, score: float) -> None:
        traits.append({"key": key, "value": value, "score": round(max(0.0, min(1.0, score)), 2)})

    if (uptime := cards.get("uptime")) and uptime["longest"]:
        days = uptime["longest"]["days"]
        add("rock", days, days / 365 if days >= 30 else 0)
    if restarts := cards.get("restarts"):
        total = restarts["total"]
        machines = max(1, len(restarts["machines"]) + len(restarts["never"]))
        months = max(1.0, _days_since(restarts["since"], year) / 30)
        add("tinkerer", total, total / machines / months / 2 if total >= 5 else 0)
        if total >= 5:
            night = sum(restarts["by_hour"][hour] for hour in NIGHT_HOURS) / total
            weekend = sum(restarts["by_weekday"][day] for day in WEEKEND) / total
            add("night_owl", round(night * 100), night if night >= 0.5 else 0)
            add("weekend_warrior", round(weekend * 100), weekend if weekend >= 0.5 else 0)
    if blocked := cards.get("blocked"):
        add("gatekeeper", blocked["per_day"], blocked["per_day"] / 20_000)
    if media := cards.get("media"):
        per_day = media["hours"] / max(1.0, _days_since(media["since"], year))
        add("cinephile", round(per_day, 1), per_day / 4)
    if (power := cards.get("power")) and power["watts"] is not None:
        watts = power["watts"]
        add("sipper", watts, 1 - watts / 60 if watts < 60 else 0)
        add("power_plant", watts, watts / 500 if watts >= 200 else 0)
    if power and (cuts := power.get("power_cuts")):
        count = cuts["count"]
        add("survivor", count, count / 12 if count >= 2 else 0)
    if intro := cards.get("intro"):
        count = intro["guests"] + intro["containers"]
        add("collector", count, count / 40 if count >= 10 else 0)
    return traits


def _days_since(since: str | None, year: Year) -> float:
    """Days from a card's ``since`` to the end of the period."""
    if since is None:
        return (year.end - year.start) / timedelta(days=1)
    start = datetime.combine(date.fromisoformat(since), datetime.min.time(), year.tz)
    return max(0.0, (year.end - start) / timedelta(days=1))
