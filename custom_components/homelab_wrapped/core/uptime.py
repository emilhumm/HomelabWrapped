"""Restarts and uptime streaks.

Machines report uptime in one of two ways, and an integration update can switch
a sensor from one to the other:

- a counter (seconds, minutes ... since boot). It keeps long-term statistics when
  it has a state_class, and only ever goes down when the machine restarts;
- a last-boot timestamp. HA keeps no long-term statistics for timestamps, so
  Wrapped records those itself.

Both are turned into restart times here, and ``merge_restarts`` joins what
several sources saw of the same machine into one list.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import pairwise

SECONDS_PER_UNIT = {"s": 1.0, "min": 60.0, "h": 3600.0, "d": 86400.0}


@dataclass(frozen=True, slots=True)
class HourStat:
    """One hour of an uptime counter's long-term statistics, in seconds."""

    start: datetime
    min: float
    max: float


@dataclass(frozen=True, slots=True)
class Streak:
    """A stretch without restarts."""

    start: datetime
    end: datetime
    ongoing: bool
    """Still running now."""
    open_start: bool
    """Starts where the data starts, so the real streak may be longer."""

    @property
    def length(self) -> timedelta:
        """How long it lasted."""
        return self.end - self.start


def to_seconds(value: float, unit: str | None) -> float | None:
    """An uptime counter's value in seconds, or None for a unit that isn't a duration."""
    factor = SECONDS_PER_UNIT.get(unit or "")
    return None if factor is None else value * factor


def counter_restarts(hours: Iterable[HourStat], *, tolerance: float = 60.0) -> list[datetime]:
    """Restarts in an uptime counter's hourly statistics, as the start of their hour.

    Without a restart the counter never goes down, so an hour's minimum is at
    least the previous hour's maximum. A restart breaks that, but it shows up in
    two hours in a row: in its own hour the minimum drops, and in the next hour
    the minimum is still below the restart hour's maximum (the value from before
    the restart). So after a restart the next hour is compared with the restart
    hour's minimum, the lowest the counter was after the restart, not its maximum.

    Hours missing from the statistics (HA was down) don't matter: a restart
    while HA was down shows up in the next hour there is.

    ``tolerance`` (seconds) absorbs counters that wobble a little between polls.
    """
    restarts: list[datetime] = []
    # Lowest the counter can be in the next hour if the machine doesn't restart.
    floor: float | None = None
    for hour in sorted(hours, key=lambda hour: hour.start):
        if floor is not None and hour.min + tolerance < floor:
            restarts.append(hour.start)
            floor = hour.min
        else:
            floor = hour.max
    return restarts


def boot_time_restarts(
    samples: Iterable[tuple[datetime, datetime]],
    *,
    tolerance: timedelta = timedelta(minutes=2),
) -> list[datetime]:
    """Restarts in a last-boot timestamp sensor's states, as their boot times.

    ``samples`` are (observed at, boot time) pairs. A restart is a boot time
    later than the last one by more than ``tolerance``: integrations that work
    the boot time out as "now - uptime" make it wobble by seconds between polls,
    and a clock correction can move it back a little.
    """
    restarts: list[datetime] = []
    last: datetime | None = None
    for _, boot in sorted(samples):
        if last is not None and boot - last > tolerance:
            restarts.append(boot)
        if last is None or boot > last:
            last = boot
    return restarts


def merge_restarts(
    *sources: Iterable[datetime], window: timedelta = timedelta(hours=2)
) -> list[datetime]:
    """One list of restarts from several sources that saw the same machine.

    Used to stitch across a break (a counter whose long-term statistics ended
    when an integration update turned it into a timestamp, and what Wrapped
    recorded of the timestamp since) and to join what the recorder still had
    with what Wrapped counted itself.

    Every restart a source saw is kept, even two of them minutes apart: a
    container redeployed five times in an hour restarted five times. A restart
    from another source is the same one as a kept restart less than ``window``
    away that no other restart of that source matched yet. The time of the
    source given first is kept, so give the most exact source first.
    """
    merged: list[datetime] = []
    for source in sources:
        matched: set[int] = set()  # restarts in merged this source saw too
        added: list[datetime] = []
        for moment in sorted(source):
            match = next(
                (
                    index
                    for index in range(
                        bisect_left(merged, moment - window), bisect_right(merged, moment + window)
                    )
                    if index not in matched and abs(merged[index] - moment) < window
                ),
                None,
            )
            if match is None:
                added.append(moment)
            else:
                matched.add(match)
        merged = sorted(merged + added)
    return merged


def longest_streak(
    restarts: Iterable[datetime], *, since: datetime, now: datetime
) -> Streak | None:
    """The longest stretch without a restart between ``since`` and ``now``.

    ``since`` is where the data starts (or the earliest boot time known); what
    happened before it is unknown, so a streak starting there is marked open.
    Restarts outside ``since`` .. ``now`` are ignored. None if ``now`` isn't
    after ``since``.
    """
    if now <= since:
        return None
    points = sorted(moment for moment in restarts if since < moment < now)
    edges = [since, *points, now]
    best: Streak | None = None
    for start, end in pairwise(edges):
        streak = Streak(start, end, ongoing=end == now, open_start=start == since)
        if best is None or streak.length > best.length:
            best = streak
    return best
