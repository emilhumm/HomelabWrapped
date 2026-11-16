"""Restarts and streaks from uptime counters and last-boot timestamps."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from itertools import pairwise

import pytest

from custom_components.homelab_wrapped.core.uptime import (
    HourStat,
    boot_time_restarts,
    counter_restarts,
    longest_streak,
    merge_restarts,
    to_seconds,
)

T0 = datetime(2026, 5, 13, tzinfo=UTC)


def hour(n: int) -> datetime:
    return T0 + timedelta(hours=n)


def simulate(
    hours: range, boots: list[datetime], *, step: int = 300, skip: range = range(0)
) -> list[HourStat]:
    """Hourly min/max of an uptime counter polled every ``step`` seconds, as HA compiles them."""
    first_boot = T0 - timedelta(days=30)
    stats = []
    for n in hours:
        if n in skip:
            continue
        values = []
        for second in range(0, 3600, step):
            moment = hour(n) + timedelta(seconds=second)
            boot = max([first_boot, *(b for b in boots if b <= moment)])
            values.append((moment - boot).total_seconds())
        stats.append(HourStat(hour(n), min(values), max(values)))
    return stats


def test_no_restart() -> None:
    assert counter_restarts(simulate(range(48), [])) == []


def test_one_restart_counts_once() -> None:
    """The restart shows up in its own hour and the next one, but is one restart."""
    stats = simulate(range(24), [hour(5) + timedelta(minutes=20)])

    naive = [b.start for a, b in pairwise(stats) if b.min < a.max]
    assert naive == [hour(5), hour(6)]  # the trap
    assert counter_restarts(stats) == [hour(5)]


@pytest.mark.parametrize(
    ("offset", "seen"),
    [
        (timedelta(seconds=1), 5),
        # The last poll in hour 5 is at 05:55; the first one after the restart is at 06:00.
        (timedelta(minutes=59, seconds=59), 6),
    ],
)
def test_restart_at_the_edges_of_an_hour(offset: timedelta, seen: int) -> None:
    assert counter_restarts(simulate(range(24), [hour(5) + offset])) == [hour(seen)]


def test_two_restarts() -> None:
    boots = [hour(5) + timedelta(minutes=20), hour(30) + timedelta(minutes=45)]
    assert counter_restarts(simulate(range(48), boots)) == [hour(5), hour(30)]


def test_restart_while_ha_was_down() -> None:
    """No statistics for hours 10-19; the restart shows in the first hour after."""
    stats = simulate(range(30), [hour(14)], skip=range(10, 20))
    assert counter_restarts(stats) == [hour(20)]


def test_wobble_within_tolerance_is_not_a_restart() -> None:
    stats = [HourStat(hour(0), 1000, 4600), HourStat(hour(1), 4570, 8200)]
    assert counter_restarts(stats) == []
    assert counter_restarts(stats, tolerance=10) == [hour(1)]


def test_hours_out_of_order() -> None:
    stats = simulate(range(24), [hour(5) + timedelta(minutes=20)])
    assert counter_restarts(reversed(stats)) == [hour(5)]


def test_to_seconds() -> None:
    assert to_seconds(2, "min") == 120
    assert to_seconds(1.5, "d") == 129600
    assert to_seconds(7, "s") == 7
    assert to_seconds(7, "%") is None
    assert to_seconds(7, None) is None


def test_boot_time_restarts() -> None:
    boot = T0
    samples = [
        (hour(1), boot),
        (hour(2), boot + timedelta(seconds=3)),  # "now - uptime" wobble
        (hour(3), boot - timedelta(seconds=40)),  # clock correction
        (hour(4), hour(4)),  # restart
        (hour(5), hour(4) + timedelta(seconds=1)),
    ]
    assert boot_time_restarts(reversed(samples)) == [hour(4)]


def test_merge_stitches_two_sources() -> None:
    """A counter's hourly restarts before the break, the timestamp's after; one overlaps."""
    counter = [hour(5), hour(30)]
    timestamp = [hour(30) + timedelta(minutes=12), hour(80)]
    assert merge_restarts(counter, timestamp) == [hour(5), hour(30), hour(80)]


def test_longest_streak() -> None:
    since, now = hour(0), hour(100)
    streak = longest_streak([hour(10), hour(70), hour(200)], since=since, now=now)
    assert streak is not None
    assert (streak.start, streak.end) == (hour(10), hour(70))
    assert streak.length == timedelta(hours=60)
    assert not streak.ongoing
    assert not streak.open_start


def test_streak_without_restarts_is_open_and_ongoing() -> None:
    streak = longest_streak([], since=hour(0), now=hour(10))
    assert streak is not None
    assert streak.ongoing
    assert streak.open_start
    assert longest_streak([], since=hour(10), now=hour(10)) is None


def test_merge_keeps_every_restart_one_source_saw() -> None:
    """Five redeploys in an hour are five restarts; another source's view of them adds none."""
    deploys = [hour(5) + timedelta(minutes=12 * n) for n in range(5)]
    hourly = [hour(5), hour(5), hour(6)]  # Wrapped's sensor: increases, at the hour's start
    assert merge_restarts(deploys) == deploys
    assert merge_restarts(deploys, hourly) == deploys
    # A restart only the second source saw is added; three sources of one restart make one.
    assert merge_restarts([hour(5)], [hour(5) + timedelta(minutes=5), hour(40)]) == [
        hour(5),
        hour(40),
    ]
    assert merge_restarts([hour(9)], [hour(8) + timedelta(minutes=50)], [hour(9)]) == [hour(9)]
