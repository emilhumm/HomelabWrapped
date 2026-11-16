"""Looking back over the recorder's states, the way Wrapped's counters read them."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from custom_components.homelab_wrapped.core.backfill import (
    Backfilled,
    CutFinder,
    DailyReader,
    PlayTimer,
    RestartFinder,
    combine,
)

TZ = ZoneInfo("Europe/Copenhagen")


def at(dom: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 11, dom, hour, minute, tzinfo=TZ)


def test_restarts_in_a_boot_time_sensor() -> None:
    """A container redeployed twice in an hour restarted twice; wobble and junk don't count."""
    finder = RestartFinder(device_class="timestamp", unit=None)
    for moment, state in [
        (at(2, 9), "unavailable"),
        (at(2, 10), at(1, 8).isoformat()),
        (at(3, 10), (at(1, 8) + timedelta(seconds=40)).isoformat()),  # "now - uptime" wobble
        (at(4, 13, 13), at(4, 13, 12).isoformat()),
        (at(4, 13, 31), at(4, 13, 30).isoformat()),
        (at(4, 14), "garbage"),
        (at(5, 9), at(5, 8, 59).isoformat()),
    ]:
        finder.feed(moment, state)
    found = finder.result()
    assert found.start == at(2, 10)  # the first state that made sense
    # When HA saw them, as Wrapped's sensor and counter statistics date them too.
    assert found.restarts == (at(4, 13, 13), at(4, 13, 31), at(5, 9))


def test_restarts_in_a_counter() -> None:
    finder = RestartFinder(device_class="duration", unit="min")
    for moment, minutes in [(at(2, 10), 600), (at(2, 11), 660), (at(2, 12), 5), (at(2, 13), 65)]:
        finder.feed(moment, str(minutes))
    assert finder.result().restarts == (at(2, 12),)
    assert RestartFinder(device_class=None, unit=None).result() == Backfilled()


def test_a_rolling_count_is_read_at_2355_each_day() -> None:
    """The value at 23:55 (the latest state then), only for days before Wrapped took over."""
    reader = DailyReader(read_at=time(23, 55), tz=TZ, before=at(6, 9))
    for moment, state in [
        (at(2, 23, 58), "100"),  # after the 2nd's reading: the 2nd isn't known
        (at(3, 12), "1500"),
        (at(3, 23, 50), "2000"),
        (at(4, 23), "unavailable"),  # still unavailable at 23:55: no reading
        (at(5, 1), "1800"),
        (at(5, 12), "1900"),
        (at(5, 23, 55), "2500"),  # exactly at the reading: the state at 23:55
    ]:
        reader.feed(moment, state)
    found = reader.result()
    assert found.days == {date(2026, 11, 3): 2000, date(2026, 11, 5): 2500}
    assert found.start == at(3, 23, 55)
    assert DailyReader(read_at=time(23, 55), tz=TZ, before=at(6, 9)).result() == Backfilled()


def test_no_reading_from_a_count_that_stood_still_for_a_day() -> None:
    """A rolling count that didn't change for over a day wasn't recorded: HA was down."""
    reader = DailyReader(read_at=time(23, 55), tz=TZ, before=at(6, 23, 55))
    reader.feed(at(2, 8), "300")
    reader.feed(at(5, 10), "400")  # HA is back
    assert reader.result().days == {date(2026, 11, 2): 300, date(2026, 11, 5): 400}


def test_time_playing_split_at_midnight() -> None:
    timer = PlayTimer(tz=TZ, end=at(4, 21))
    for moment, state in [
        (at(2, 22), "playing"),
        (at(3, 1), "paused"),
        (at(3, 1, 30), "playing"),
        (at(3, 2), "idle"),
        (at(4, 20), "playing"),  # still playing when Wrapped's sensor took over
        (at(4, 23), "idle"),  # after that: Wrapped's sensor counted it
    ]:
        timer.feed(moment, state)
    found = timer.result()
    assert found.start == at(2, 22)
    assert found.days == {date(2026, 11, 2): 2.0, date(2026, 11, 3): 1.5, date(2026, 11, 4): 1.0}

    # Still playing, with no later state: counted up to the end.
    timer = PlayTimer(tz=TZ, end=at(4, 21))
    timer.feed(at(4, 20, 30), "playing")
    assert timer.result().days == {date(2026, 11, 4): 0.5}


def test_one_stretch_of_playing_counts_for_at_most_12_hours() -> None:
    """Left at "playing" when HA went down for two days: that isn't two days of films."""
    timer = PlayTimer(tz=TZ, end=at(9, 12))
    timer.feed(at(2, 20), "playing")
    timer.feed(at(4, 20), "idle")
    timer.feed(at(6, 8), "playing")  # and still playing when Wrapped took over, days later
    assert timer.result().days == {
        date(2026, 11, 2): 4.0,
        date(2026, 11, 3): 8.0,
        date(2026, 11, 6): 12.0,
    }


def test_players_of_one_server_add_up() -> None:
    one = Backfilled(at(2, 8), days={date(2026, 11, 2): 1.0})
    two = Backfilled(at(1, 8), days={date(2026, 11, 2): 0.5, date(2026, 11, 3): 2.0})
    assert combine([one, two, Backfilled()]) == Backfilled(
        at(1, 8), days={date(2026, 11, 2): 1.5, date(2026, 11, 3): 2.0}
    )
    assert combine([]) == Backfilled()


def test_stored_and_read_back() -> None:
    found = Backfilled(
        datetime(2026, 11, 2, 8, tzinfo=UTC),
        (datetime(2026, 11, 4, 12, 13, tzinfo=UTC),),
        {date(2026, 11, 3): 2000.0},
    )
    assert Backfilled.from_dict(found.as_dict()) == found
    assert Backfilled.from_dict(Backfilled().as_dict()) == Backfilled()


def test_hours_per_title() -> None:
    """A stretch counts for what was playing when it began."""
    timer = PlayTimer(tz=TZ, end=at(5, 12))
    timer.feed(at(2, 20), "playing", {"media_series_title": "Severance"})
    timer.feed(at(2, 21), "playing", {"media_series_title": "Other"})  # repeated (a new chunk)
    timer.feed(at(2, 22), "idle", {})
    timer.feed(at(3, 9), "playing", {"media_title": "Dune"})
    timer.feed(at(3, 10, 30), "paused")
    found = timer.result()
    assert found.days == {date(2026, 11, 2): 2.0, date(2026, 11, 3): 1.5}
    assert found.titles == {"2026": {"Severance": 2.0, "Dune": 1.5}}
    both = combine([found, Backfilled(titles={"2026": {"Dune": 1.0}, "2025": {"Up": 2.0}})])
    assert both.titles == {"2026": {"Severance": 2.0, "Dune": 2.5}, "2025": {"Up": 2.0}}
    assert Backfilled.from_dict(both.as_dict()) == both


def test_power_cuts_in_a_ups_status() -> None:
    """A cut still going on when Wrapped took over is the sensor's to count."""
    finder = CutFinder()
    for moment, state in [
        (at(2, 8), "unavailable"),
        (at(2, 9), "OL"),
        (at(3, 21), "OB DISCHRG"),
        (at(3, 21, 4), "OB DISCHRG LB"),
        (at(3, 21, 9), "OL CHRG"),
        (at(5, 7), "OB"),
    ]:
        finder.feed(moment, state)
    found = finder.result()
    assert found.start == at(2, 9)
    assert found.cuts == ((at(3, 21), 540.0),)
    assert Backfilled.from_dict(found.as_dict()) == found
