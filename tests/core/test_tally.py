"""Counting restarts, blocked queries and playback one reading at a time."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime, timedelta

import pytest

from custom_components.homelab_wrapped.core.tally import (
    MAX_CUTS,
    MAX_TITLES,
    DailyTotal,
    PlaybackClock,
    PowerCuts,
    RestartCounter,
    UptimeReading,
    media_title,
    on_battery,
    read_uptime,
)

T0 = datetime(2026, 11, 1, 12, tzinfo=UTC)
BOOT = datetime(2026, 10, 1, 8, tzinfo=UTC)


def at(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


def stamp(boot: datetime, minutes: float = 0) -> UptimeReading:
    reading = read_uptime(boot.isoformat(), device_class="timestamp", unit=None, at=at(minutes))
    assert reading is not None
    return reading


def counter(seconds: float, minutes: float, unit: str = "s") -> UptimeReading:
    reading = read_uptime(str(seconds), device_class="duration", unit=unit, at=at(minutes))
    assert reading is not None
    return reading


def test_read_uptime() -> None:
    reading = counter(3600, 0)
    assert reading.boot == T0 - timedelta(hours=1)
    assert reading.seconds == 3600
    assert reading.tolerance == timedelta(minutes=5)
    assert counter(2.5, 0, unit="d").tolerance == timedelta(days=1)
    assert stamp(BOOT).boot == BOOT
    assert stamp(BOOT).seconds is None
    for state, device_class, unit in [
        ("unavailable", "timestamp", None),
        ("2026-10-01T08:00:00", "timestamp", None),  # no time zone
        ("unknown", "duration", "s"),
        ("12", None, "%"),
        ("nan", None, "s"),
        ("-5", None, "s"),
        ("1e20", None, "s"),  # would overflow the date arithmetic
        ("99999999999", None, "d"),
    ]:
        assert read_uptime(state, device_class=device_class, unit=unit, at=T0) is None


def test_first_reading_is_the_baseline() -> None:
    restarts = RestartCounter()
    assert not restarts.observe(stamp(BOOT))
    assert restarts.count == 0
    assert restarts.last_boot == BOOT


def test_boot_time_that_moves_forward_is_a_restart() -> None:
    restarts = RestartCounter()
    restarts.observe(stamp(BOOT))
    assert not restarts.observe(stamp(BOOT + timedelta(seconds=3), 1))  # wobble
    assert not restarts.observe(stamp(BOOT - timedelta(seconds=40), 2))  # clock correction
    assert restarts.observe(stamp(at(3), 3))
    assert restarts.count == 1
    assert restarts.last_boot == at(3)


def test_counter_that_drops_is_a_restart() -> None:
    restarts = RestartCounter()
    restarts.observe(counter(100_000, 0))
    assert not restarts.observe(counter(100_060, 1))
    assert not restarts.observe(counter(100_100, 2))  # boot moved 20 s: polling wobble
    assert restarts.observe(counter(30, 3))
    assert not restarts.observe(counter(600, 13))
    assert restarts.observe(counter(10, 14))  # and again ten minutes later
    assert restarts.count == 2


def test_restart_while_home_assistant_was_down() -> None:
    """Last seen at 100 s uptime; HA was down for a day, the machine restarted meanwhile."""
    restarts = RestartCounter()
    restarts.observe(counter(100, 0))
    assert restarts.observe(counter(5000, 24 * 60))
    assert restarts.count == 1


def test_coarse_counter_does_not_count_its_rounding() -> None:
    """In days with two decimals, the boot time moves by up to 15 minutes between polls."""
    restarts = RestartCounter()
    restarts.observe(counter(3.00, 0, unit="d"))
    assert not restarts.observe(counter(3.00, 14, unit="d"))
    assert not restarts.observe(counter(3.01, 15, unit="d"))
    assert restarts.observe(counter(0.01, 30, unit="d"))


def test_counter_that_becomes_a_timestamp_carries_on() -> None:
    """An integration update turned the uptime counter into a boot timestamp."""
    restarts = RestartCounter()
    restarts.observe(counter(3600, 0))
    assert not restarts.observe(stamp(T0 - timedelta(hours=1), 10))
    assert restarts.observe(stamp(at(20), 20))
    assert restarts.count == 1


def uptime_class(boot: datetime, minutes: float) -> UptimeReading:
    """HA 2026.10's "uptime" device class (Proxmox VE, System Monitor)."""
    reading = read_uptime(boot.isoformat(), device_class="uptime", unit=None, at=at(minutes))
    assert reading is not None
    return reading


def test_slow_drift_is_followed_not_counted() -> None:
    """The machine's clock runs slow against HA's: HA's uptime class holds the boot time until
    it drifts a minute, so it moves a minute at a time, and is followed, never counted."""
    restarts = RestartCounter()
    for step in range(30):
        assert not restarts.observe(uptime_class(BOOT + timedelta(seconds=61 * step), step * 60))
    assert restarts.count == 0


def test_a_crash_loop_counts_every_start_a_poll_sees() -> None:
    """Docker's start time, polled every minute, of a container restarting every minute:
    each poll sees a new start a minute on (the old 5 minutes' tolerance counted none)."""
    restarts = RestartCounter()
    for minute in range(10):
        restarts.observe(stamp(at(minute) - timedelta(seconds=5), minute))
    assert restarts.count == 9


def run_uptime_class(
    restarts: RestartCounter,
    boot_at: Callable[[float], datetime | None],
    minutes: Iterable[float],
) -> None:
    """Feed what HA writes for an uptime-class sensor polled every minute: the boot time
    ("now - uptime"; uptime 0 for a stopped guest, so now) only when it moved more than
    60 s from the one HA holds. Between writes Wrapped's timer settles the counter."""
    held: datetime | None = None
    for minute in minutes:
        boot = boot_at(minute)
        value = at(minute) if boot is None else boot
        if held is None or abs(value - held) > timedelta(seconds=60):
            held = value
            restarts.observe(uptime_class(value, minute))
        else:
            restarts.settle(at(minute))


def test_reboots_seen_live_all_count() -> None:
    """A rebooted machine's new boot time is written once, a minute after the boot, and
    then held: it isn't "stopped", and its next reboot counts too."""
    boots = [BOOT, at(100), at(400), at(900)]
    restarts = RestartCounter()
    run_uptime_class(
        restarts, lambda m: max(b for b in boots if b <= at(m)), [m + 0.5 for m in range(1200)]
    )
    assert restarts.count == 3
    assert not restarts.stopped
    assert restarts.downs == []


def test_a_stopped_guest_counts_once_and_isnt_up() -> None:
    """Proxmox VE reports a stopped guest's uptime as 0, so its boot time follows the clock.
    The stop counts once; nothing while it stays stopped, across an HA restart too; nor
    when it starts again. The time it was stopped is kept, so streaks leave it out."""

    def boot_at(minute: float) -> datetime | None:
        if minute < 100:
            return BOOT
        if minute < 400:
            return None  # stopped at 100
        return at(400)  # started at 400

    ha_up = [m + 0.5 for m in range(1000) if not 200 <= m < 230]  # HA down half an hour
    restarts = RestartCounter()
    run_uptime_class(restarts, boot_at, ha_up)
    assert restarts.count == 1
    assert not restarts.stopped
    ((start, end),) = restarts.downs
    assert at(100) <= start <= at(102)
    assert at(400) <= end <= at(401.5)
    assert RestartCounter.from_dict(restarts.as_dict()) == restarts


def test_a_guest_that_never_runs() -> None:
    """A template: stopped from the first reading on. Never a restart, never up."""
    restarts = RestartCounter()
    run_uptime_class(restarts, lambda m: None, [m + 0.5 for m in range(600)])
    assert restarts.count == 0
    assert restarts.stopped
    ((start, end),) = restarts.down(at(600))
    assert start <= at(3)
    assert end is None
    # Read again much later with no reading since (Wrapped's timer hadn't run): it started.
    ((_, end),) = restarts.down(at(700))
    assert end == restarts.last_boot


def test_a_reboot_then_a_stop() -> None:
    def boot_at(minute: float) -> datetime | None:
        if minute < 100:
            return BOOT
        if minute < 300:
            return at(100)  # rebooted at 100
        return None  # stopped at 300

    restarts = RestartCounter()
    run_uptime_class(restarts, boot_at, [m + 0.5 for m in range(500)])
    assert restarts.count == 2
    assert restarts.stopped


def test_counters_have_no_stopped_state() -> None:
    """A counter that drops counts once; it climbing again from there doesn't."""
    counted = RestartCounter()
    counted.observe(counter(5000, 0))
    assert counted.observe(counter(30, 1))
    assert not counted.observe(counter(90, 2))
    assert counted.count == 1
    assert not counted.stopped


def test_a_docker_start_time_is_exact() -> None:
    """Portainer's start time is Docker's, to the second: starts 30 s apart both count."""
    exact = read_uptime(
        at(0).isoformat(), device_class="timestamp", unit=None, at=at(1), exact=True
    )
    assert exact is not None
    assert exact.tolerance == timedelta(seconds=10)
    restarts = RestartCounter()
    restarts.observe(exact)
    later = read_uptime(
        (at(0) + timedelta(seconds=30)).isoformat(),
        device_class="timestamp",
        unit=None,
        at=at(2),
        exact=True,
    )
    assert later is not None
    assert restarts.observe(later)


def test_a_boot_time_in_the_future_is_ignored() -> None:
    """An unsynced clock or a glitch would otherwise end restart counting for good."""
    assert (
        read_uptime("2036-01-01T00:00:00+00:00", device_class="timestamp", unit=None, at=at(0))
        is None
    )
    assert read_uptime(at(1).isoformat(), device_class="uptime", unit=None, at=at(0)) is not None


def test_restart_counter_storage() -> None:
    restarts = RestartCounter()
    restarts.observe(counter(100, 0))
    restarts.observe(counter(5, 1))
    copy = RestartCounter.from_dict(restarts.as_dict())
    assert copy == restarts
    assert RestartCounter.from_dict(None) == RestartCounter()


def test_daily_total() -> None:
    blocked = DailyTotal()
    assert blocked.take(1000, date(2026, 11, 1))
    assert not blocked.take(1200, date(2026, 11, 1))  # same day again
    assert blocked.take(800, date(2026, 11, 2))
    assert not blocked.take(float("nan"), date(2026, 11, 3))
    assert not blocked.take(-1, date(2026, 11, 3))
    assert blocked.total == 1800
    assert DailyTotal.from_dict(blocked.as_dict()) == blocked
    assert DailyTotal.from_dict(None) == DailyTotal()


def test_playback_adds_up_over_players() -> None:
    clock = PlaybackClock()
    assert clock.update("tv", True, at(0)) == 0
    assert clock.update("phone", True, at(30)) == 0
    assert clock.settle(at(60)) == pytest.approx(60 * 60 + 30 * 60)  # both keep playing
    assert clock.update("tv", False, at(90)) == pytest.approx(30 * 60)
    assert clock.update("tv", False, at(100)) == 0  # paused stays paused
    assert clock.settle(at(120)) == pytest.approx(60 * 60)
    assert clock.seconds == pytest.approx(3 * 60 * 60)


def test_playback_storage_keeps_only_the_total() -> None:
    clock = PlaybackClock()
    clock.update("tv", True, at(0))
    clock.settle(at(10))
    copy = PlaybackClock.from_dict(clock.as_dict())
    assert copy.seconds == pytest.approx(600)
    assert copy.playing_since == {}
    assert PlaybackClock.from_dict(None) == PlaybackClock()


def test_hours_per_title_by_year() -> None:
    clock = PlaybackClock()
    clock.update("tv", True, at(0), title="Severance", year=2026)
    clock.update("tv", True, at(60), title="Dune", year=2026)  # the next title
    clock.settle(at(90), year=2026)
    clock.update("tv", False, at(120), year=2027)  # past midnight on New Year's Eve
    clock.update("phone", True, at(0))
    clock.update("phone", False, at(30), year=2026)  # nothing known about what played
    assert clock.top_titles(2026) == {"Severance": 1.0, "Dune": 0.5}
    assert clock.top_titles(2027) == {"Dune": 0.5}
    assert clock.seconds == pytest.approx(150 * 60)
    assert PlaybackClock.from_dict(clock.as_dict()).titles == clock.titles
    assert PlaybackClock.from_dict({"seconds": 5, "titles": "junk"}).titles == {}
    assert PlaybackClock.from_dict({"titles": {"2026": "junk"}}).titles == {}


def test_only_the_longest_played_titles_are_kept() -> None:
    clock = PlaybackClock()
    minute = 0
    for n in range(200):
        clock.update("tv", True, at(minute), title=f"show {n}", year=2026)
        minute += n + 1  # show n plays for n + 1 minutes
    clock.settle(at(minute), year=2026)
    kept = clock.titles["2026"]
    assert MAX_TITLES <= len(kept) <= MAX_TITLES * 3 // 2
    assert "show 199" in kept
    assert "show 0" not in kept


def test_what_a_player_plays() -> None:
    assert media_title({"media_series_title": " Severance ", "media_title": "Ep 1"}) == "Severance"
    assert media_title({"media_artist": "Daft Punk", "media_title": "One More Time"}) == "Daft Punk"
    assert media_title({"media_title": "x" * 300}) == "x" * 100
    assert media_title({"media_title": 5, "media_series_title": " "}) is None
    assert media_title({}) is None


def test_a_season_in_a_series_name_is_left_off() -> None:
    """Jellyfin names a series it hasn't matched after its folder, often one per season."""

    def series(name: str, season: object) -> str | None:
        return media_title({"media_series_title": name, "media_season": season})

    assert series("Slow Horses S01", 1) == "Slow Horses"
    assert series("Slow.Horses.S02", 2) == "Slow.Horses"
    assert series("Dark - Season 3", "3") == "Dark"
    assert series("Fargo (Season 4)", 4) == "Fargo"
    assert series("Slow Horses S01", 2) == "Slow Horses S01"  # not the season playing
    assert series("Ravens1", 1) == "Ravens1"  # no space before it: part of the name
    assert series("Season 1", 1) == "Season 1"  # nothing would be left
    assert series("Slow Horses S01", None) == "Slow Horses S01"
    assert series("Slow Horses S01", "one") == "Slow Horses S01"
    assert series("Slow Horses S01", True) == "Slow Horses S01"


def test_what_a_ups_status_says() -> None:
    assert on_battery("OB DISCHRG") is True  # NUT
    assert on_battery("ONBATT") is True  # APC UPS Daemon
    assert on_battery("OL CHRG") is False
    assert on_battery("ONLINE") is False
    assert on_battery("unavailable") is None
    assert on_battery("") is None


def test_power_cuts() -> None:
    cuts = PowerCuts()
    assert not cuts.observe(False, at(0))
    assert cuts.observe(True, at(10))
    assert not cuts.observe(True, at(11))  # still on battery
    assert cuts.observe(False, at(14))
    assert (cuts.count, cuts.cuts) == (1, [(at(10), 240.0)])
    cuts.observe(True, at(100))
    assert cuts.count == 2
    assert cuts.all_cuts(at(103)) == [(at(10), 240.0), (at(100), 180.0)]  # one going on
    # Back after HA was down for days: the cut counts for at most 12 hours.
    cuts.observe(False, at(100 + 3 * 24 * 60))
    assert cuts.cuts[-1] == (at(100), 12 * 3600.0)
    assert PowerCuts.from_dict(cuts.as_dict()) == cuts
    assert PowerCuts.from_dict(None) == PowerCuts()
    many = PowerCuts()
    for n in range(MAX_CUTS + 20):
        many.observe(True, at(2 * n))
        many.observe(False, at(2 * n + 1))
    assert (many.count, len(many.cuts)) == (MAX_CUTS + 20, MAX_CUTS)


def test_a_ups_status_that_says_neither() -> None:
    """Lost contact or shutting down: still on battery as far as anyone knows."""
    for status in ("COMMLOST", "SHUTTING DOWN", "WAIT", "OFF"):
        assert on_battery(status) is None
    cuts = PowerCuts()
    for minutes, status in (
        (0, "ONBATT"),
        (1, "COMMLOST"),
        (2, "ONBATT"),
        (3, "SHUTTING DOWN"),
        (9, "ONLINE"),
    ):
        if (battery := on_battery(status)) is not None:
            cuts.observe(battery, at(minutes))
    assert (cuts.count, cuts.cuts) == (1, [(at(0), 540.0)])
