"""Looking back: what the recorder still remembers from before Wrapped started counting.

HA keeps every state change for the recorder's retention period (10 days by
default). When Wrapped starts counting something, it reads those states once,
so the cards begin days earlier instead of on the day Wrapped was installed.

Each finder is fed a source's states in time order, as (when, state, attributes)
(attributes only where a finder needs them), and ends with what it found as a
``Backfilled``. They read the states the same way
Wrapped's own counters do (``tally``), so a backfilled day and a counted day mean
the same thing.

While HA is down the recorder keeps nothing, so the last state before an outage
seems to carry on through it, where Wrapped's own counters would have counted
nothing. The recorder doesn't say when an unclean shutdown happened, so two
bounds keep an outage from counting: a daily reading needs a state less than a
day old (``MAX_STALE``), and one stretch of playing counts for at most
``MAX_STRETCH``.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, tzinfo
import math
from typing import Any

from .tally import PowerCuts, RestartCounter, media_title, on_battery, read_uptime

PLAYING = "playing"
MAX_STALE = timedelta(hours=24)
"""A rolling 24-hour count that hasn't changed for longer wasn't being recorded (HA was down)."""
MAX_STRETCH = timedelta(hours=12)
"""The most one unbroken stretch of "playing" counts for."""


@dataclass(frozen=True, slots=True)
class Backfilled:
    """What the recorder's states showed for one of Wrapped's counters."""

    start: datetime | None = None
    """Where the states start; None if the recorder had nothing."""
    restarts: tuple[datetime, ...] = ()
    """Restarts, as when HA saw them: like Wrapped's sensor and counter statistics do, so
    the same restart seen by several of them is matched (``merge_restarts``)."""
    days: Mapping[date, float] = field(default_factory=dict)
    """An amount per local day: blocked queries, or hours played."""
    titles: Mapping[str, Mapping[str, float]] = field(default_factory=dict)
    """Year (as text) -> title -> hours played."""
    cuts: tuple[tuple[datetime, float], ...] = ()
    """Power cuts a UPS rode out: (start, seconds)."""

    def as_dict(self) -> dict[str, Any]:
        """For storage."""
        return {
            "start": self.start.isoformat() if self.start else None,
            "restarts": [moment.isoformat() for moment in self.restarts],
            "days": {day.isoformat(): amount for day, amount in sorted(self.days.items())},
            "titles": {year: dict(per_title) for year, per_title in self.titles.items()},
            "cuts": [[start.isoformat(), seconds] for start, seconds in self.cuts],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Backfilled:
        """From storage."""
        start = data.get("start")
        return cls(
            datetime.fromisoformat(start) if start else None,
            tuple(datetime.fromisoformat(moment) for moment in data.get("restarts", [])),
            {
                date.fromisoformat(day): float(amount)
                for day, amount in data.get("days", {}).items()
            },
            {
                str(year): {str(title): float(hours) for title, hours in per_title.items()}
                for year, per_title in data.get("titles", {}).items()
            },
            tuple(
                (datetime.fromisoformat(start), float(seconds))
                for start, seconds in data.get("cuts", [])
            ),
        )


class RestartFinder:
    """Restarts in an uptime sensor's states, counted like Wrapped's restarts sensor."""

    def __init__(self, *, device_class: str | None, unit: str | None, exact: bool = False) -> None:
        """``device_class`` and ``unit`` of the source, which its states don't carry;
        ``exact`` for a start time to the second (a Docker container's)."""
        self._device_class = device_class
        self._unit = unit
        self._exact = exact
        self._counter = RestartCounter()
        self._start: datetime | None = None
        self._restarts: list[datetime] = []

    def feed(self, at: datetime, state: str, attributes: Mapping[str, Any] | None = None) -> None:
        """The next state, in time order."""
        reading = read_uptime(
            state, device_class=self._device_class, unit=self._unit, at=at, exact=self._exact
        )
        if reading is None:
            return
        if self._start is None:
            self._start = at
        if self._counter.observe(reading):
            self._restarts.append(at)

    def result(self) -> Backfilled:
        """What was found."""
        return Backfilled(self._start, tuple(self._restarts))


class CutFinder:
    """Power cuts in a UPS's statuses, counted like Wrapped's power cuts sensor.

    A cut still going on when Wrapped's sensor took over is left to the sensor,
    which sees the UPS on battery when it starts.
    """

    def __init__(self) -> None:
        """Nothing seen yet."""
        self._cuts = PowerCuts()
        self._start: datetime | None = None

    def feed(self, at: datetime, state: str, attributes: Mapping[str, Any] | None = None) -> None:
        """The next state, in time order."""
        battery = on_battery(state)
        if battery is None:
            return
        if self._start is None:
            self._start = at
        self._cuts.observe(battery, at)

    def result(self) -> Backfilled:
        """What was found."""
        return Backfilled(self._start, cuts=tuple(self._cuts.cuts))


class DailyReader:
    """A rolling 24-hour count, as Wrapped reads it: its value at ``read_at`` each day.

    Only days whose reading time is before ``before`` (when Wrapped's own sensor
    took over) are read.
    """

    def __init__(self, *, read_at: time, tz: tzinfo, before: datetime) -> None:
        """Read at ``read_at`` local time (``tz``) on every day before ``before``."""
        self._read_at = read_at
        self._tz = tz
        self._before = before
        self._value: float | None = None
        self._value_at: datetime | None = None
        self._next: datetime | None = None
        self._days: dict[date, float] = {}

    def feed(self, at: datetime, state: str, attributes: Mapping[str, Any] | None = None) -> None:
        """The next state, in time order."""
        self._read_until(at)
        if self._next is None:
            day = at.astimezone(self._tz).date()
            self._next = self._reading_on(day)
            if self._next < at:  # the first state came after that day's reading
                self._next = self._reading_on(day + timedelta(days=1))
        self._value, self._value_at = _amount(state), at

    def result(self) -> Backfilled:
        """What was found."""
        self._read_until(self._before)
        if not self._days:
            return Backfilled()
        first = min(self._days)
        return Backfilled(self._reading_on(first), days=dict(self._days))

    def _read_until(self, moment: datetime) -> None:
        """Take every reading due before ``moment`` (the state then is the latest fed)."""
        while self._next is not None and self._next < min(moment, self._before):
            if (
                self._value is not None
                and self._value_at is not None
                and self._next - self._value_at <= MAX_STALE
            ):
                self._days[self._next.astimezone(self._tz).date()] = self._value
            self._next = self._reading_on(
                self._next.astimezone(self._tz).date() + timedelta(days=1)
            )

    def _reading_on(self, day: date) -> datetime:
        return datetime.combine(day, self._read_at, self._tz)


class PlayTimer:
    """Hours a media player spent playing, per local day and per title, up to ``end``.

    A stretch of playing counts for at most ``MAX_STRETCH``: past that, HA was
    probably down with the player's last state left at "playing". A stretch
    counts for the title playing when it began: the recorder keeps a new title
    within a stretch (the next episode) only with every position update.
    """

    def __init__(self, *, tz: tzinfo, end: datetime) -> None:
        """Count up to ``end`` (when Wrapped's own sensor took over), split at midnight in ``tz``."""
        self._tz = tz
        self._end = end
        self._start: datetime | None = None
        self._since: datetime | None = None
        self._title: str | None = None
        self._hours: defaultdict[date, float] = defaultdict(float)
        self._titles: defaultdict[str, defaultdict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )

    def feed(self, at: datetime, state: str, attributes: Mapping[str, Any] | None = None) -> None:
        """The next state, in time order; ``attributes`` tell what is playing."""
        at = min(at, self._end)
        if self._start is None:
            self._start = at
        playing = state == PLAYING
        if playing and self._since is not None:
            return  # still playing (a repeated state): the stretch, and its title, go on
        if self._since is not None:
            self._add(self._since, min(at, self._since + MAX_STRETCH))
        self._since = at if playing else None
        self._title = media_title(attributes or {}) if playing else None

    def result(self) -> Backfilled:
        """What was found."""
        if self._since is not None:
            self._add(self._since, min(self._end, self._since + MAX_STRETCH))
            self._since = None
        days = {day: round(hours, 4) for day, hours in self._hours.items() if hours > 0}
        titles = {
            year: {title: round(hours, 4) for title, hours in per_title.items()}
            for year, per_title in self._titles.items()
        }
        return Backfilled(self._start, days=days, titles=titles)

    def _add(self, start: datetime, end: datetime) -> None:
        while start < end:
            local = start.astimezone(self._tz)
            midnight = datetime.combine(local.date() + timedelta(days=1), time(), self._tz)
            stop = min(end, midnight)
            hours = (stop - start) / timedelta(hours=1)
            self._hours[local.date()] += hours
            if self._title:
                self._titles[str(local.year)][self._title] += hours
            start = stop


def combine(found: Iterable[Backfilled]) -> Backfilled:
    """One result from several sources of the same counter (a media server's players)."""
    found = list(found)
    starts = [item.start for item in found if item.start is not None]
    days: defaultdict[date, float] = defaultdict(float)
    titles: defaultdict[str, defaultdict[str, float]] = defaultdict(lambda: defaultdict(float))
    for item in found:
        for day, amount in item.days.items():
            days[day] += amount
        for year, per_title in item.titles.items():
            for title, hours in per_title.items():
                titles[year][title] += hours
    return Backfilled(
        min(starts) if starts else None,
        tuple(sorted(moment for item in found for moment in item.restarts)),
        dict(days),
        {year: dict(per_title) for year, per_title in titles.items()},
    )


def _amount(state: str) -> float | None:
    try:
        value = float(state)
    except ValueError:
        return None
    return value if math.isfinite(value) and value >= 0 else None
