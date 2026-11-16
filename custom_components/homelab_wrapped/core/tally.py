"""Counting what Home Assistant doesn't keep: restarts, blocked DNS queries, playback.

HA forgets events after the recorder's retention period (10 days by default).
These counters turn them into ever-growing totals, which the HA layer exposes as
``total_increasing`` sensors, so HA keeps their long-term statistics forever.

Each counter is fed one reading at a time and saves as plain JSON
(``as_dict`` / ``from_dict``), so it survives restarts of Home Assistant.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
import math
import re
from typing import Any

from .uptime import SECONDS_PER_UNIT, to_seconds

COUNTER_DROP = 60.0
"""Seconds an uptime counter must fall by to count as a restart (absorbs wobble)."""

TIMESTAMP_TOLERANCE = timedelta(seconds=45)
"""How far a reported boot time may move without a restart: worked out as "now - uptime" to a
second or two (a firewall's, a NAS's). Under a minute, so restarts a minute apart count."""

EXACT_TOLERANCE = timedelta(seconds=10)
"""For a start time that is exact to the second (Docker's StartedAt, via Portainer): a
container crash-looping every 30 seconds still counts every start a poll sees."""

UPTIME_CLASS_TOLERANCE = timedelta(seconds=90)
"""HA's "uptime" device class holds a boot time until it drifts more than 60 seconds."""

COUNTER_TOLERANCE = timedelta(minutes=5)
"""A counter's boot time ("now - uptime") moves with the poll and its unit's rounding; a
restart shows as the counter dropping anyway."""

BOOT_TIME_CLASSES = frozenset({"timestamp", "uptime"})
"""Device classes whose state is the boot time itself (HA 2026.10 added "uptime")."""

FRESH_AGE = timedelta(minutes=3)
"""A reading this soon after its boot time: the machine has just booted, or isn't running.
Proxmox VE reports a stopped guest's uptime as 0, so its "boot time" is always about now."""

FOLLOW_GAP = timedelta(minutes=5)
"""HA holds an uptime-class boot time until it moves 60 s, so a stopped guest's is written
every minute or two, a running machine's never. Readings this close whose boot times move
with the clock are a stopped guest; none for this long, and it is running."""

CLOCK_SLACK = timedelta(seconds=30)
"""How closely a stopped guest's boot time follows the clock between two readings."""

MAX_DOWNS = 100
"""Stopped periods kept, the latest: streaks don't count them as up."""

MAX_UPTIME = 100 * 365 * 24 * 3600.0
"""Seconds; a larger uptime is a broken sensor, not a machine."""


@dataclass(frozen=True, slots=True)
class UptimeReading:
    """One reading of an uptime sensor, as the boot time it implies."""

    at: datetime
    boot: datetime
    seconds: float | None
    """The counter's value in seconds; None for a last-boot timestamp."""
    tolerance: timedelta
    """How far ``boot`` can move between readings without a restart."""
    can_stop: bool = False
    """HA's uptime class (Proxmox VE): an uptime of about 0 can mean "not running"."""

    @property
    def fresh(self) -> bool:
        """Only just booted, or not running (see ``FRESH_AGE``)."""
        return self.can_stop and self.at - self.boot < FRESH_AGE


def read_uptime(
    state: str, *, device_class: str | None, unit: str | None, at: datetime, exact: bool = False
) -> UptimeReading | None:
    """Make sense of an uptime sensor's state, or None (unavailable, unknown, garbage).

    ``at`` is when the state was last updated: a counter's boot time is ``at``
    minus its value. ``exact``: a start time to the second (Docker's), so a smaller tolerance.
    """
    if device_class in BOOT_TIME_CLASSES:
        try:
            boot = datetime.fromisoformat(state)
        except ValueError:
            return None
        if boot.tzinfo is None:
            return None
        uptime_class = device_class == "uptime"
        tolerance = (
            UPTIME_CLASS_TOLERANCE
            if uptime_class
            else EXACT_TOLERANCE
            if exact
            else TIMESTAMP_TOLERANCE
        )
        if boot > at + tolerance:
            return None  # booted in the future: an unsynced clock, a glitch
        return UptimeReading(at, boot, None, tolerance, can_stop=uptime_class)
    try:
        value = float(state)
    except ValueError:
        return None
    seconds = to_seconds(value, unit)
    if seconds is None or not math.isfinite(seconds) or not 0 <= seconds <= MAX_UPTIME:
        return None  # also keeps absurd values from overflowing the date arithmetic
    rounding = timedelta(seconds=SECONDS_PER_UNIT[unit or ""])
    return UptimeReading(
        at,
        at - timedelta(seconds=seconds),
        seconds,
        max(COUNTER_TOLERANCE, rounding),
    )


@dataclass(slots=True)
class RestartCounter:
    """Restarts of one machine, counted from its uptime sensor's readings.

    A restart is a counter that drops, or a boot time that moves forward. The
    second also catches restarts while HA was down (the machine is back up,
    with a later boot time) and carries on when an integration update turns a
    counter into a timestamp, since both are compared as boot times.
    """

    count: int = 0
    last_boot: datetime | None = None
    last_seconds: float | None = None
    last_at: datetime | None = None
    """When the last reading was taken."""
    fresh: bool = False
    """The last reading was just after its boot time: booted, or maybe stopped."""
    stopped: bool = False
    """Not running: a guest whose boot time follows the clock."""
    stopped_since: datetime | None = None
    downs: list[tuple[datetime, datetime]] = field(default_factory=list)
    """The latest ``MAX_DOWNS`` stopped periods that ended."""

    def observe(self, reading: UptimeReading) -> bool:
        """Take a reading; True if it shows a restart.

        A guest that stops counts once: its boot time jumps to now, like a reboot's.
        When the next readings keep following the clock, it is stopped, and nothing
        more counts while it is (across restarts of HA too), nor when it starts.
        """
        if self.last_boot is None:
            self._seen(reading)
            return False
        if self._follows_clock(reading):
            if not self.stopped:
                since = self.last_boot
                if self.downs and self.downs[-1][1] == since:
                    # Still the same stop: HA was down, so the readings had a gap.
                    since = self.downs.pop()[0]
                self.stopped, self.stopped_since = True, since
            self._seen(reading)
            return False
        if self.stopped:
            self._end_stop(reading.boot)  # running again; the stop was counted
            self._seen(reading)
            return False
        dropped = (
            reading.seconds is not None
            and self.last_seconds is not None
            and reading.seconds + COUNTER_DROP < self.last_seconds
        )
        restarted = dropped or reading.boot - self.last_boot > reading.tolerance
        if restarted:
            self.count += 1
            self.last_boot = reading.boot
        else:
            # Keep the latest boot time seen: wobble never builds up, and slow clock
            # drift between the machine and HA is followed rather than counted.
            self.last_boot = max(self.last_boot, reading.boot)
        self.last_seconds, self.last_at, self.fresh = reading.seconds, reading.at, reading.fresh
        return restarted

    def settle(self, now: datetime) -> bool:
        """No reading for a while: a stopped guest's boot time would have moved, so the
        machine is running. True if it was stopped until now."""
        if self.last_at is None or now - self.last_at <= FOLLOW_GAP:
            return False
        self.fresh = False
        if not self.stopped:
            return False
        self._end_stop(self.last_boot)  # its last boot time is when it started again
        return True

    def down(self, now: datetime) -> list[tuple[datetime, datetime | None]]:
        """Its stopped periods; one still going on ends with None."""
        found: list[tuple[datetime, datetime | None]] = list(self.downs)
        if self.stopped and self.stopped_since is not None:
            if self.last_at is not None and now - self.last_at > FOLLOW_GAP:
                found.append((self.stopped_since, self.last_boot))  # started since
            else:
                found.append((self.stopped_since, None))
        return found

    def _follows_clock(self, reading: UptimeReading) -> bool:
        if not (reading.fresh and (self.fresh or self.stopped)) or self.last_at is None:
            return False
        elapsed = reading.at - self.last_at
        moved = reading.boot - (self.last_boot or reading.boot)
        return (
            timedelta(0) < elapsed <= FOLLOW_GAP
            and moved > timedelta(0)
            and abs(moved - elapsed) <= CLOCK_SLACK
        )

    def _seen(self, reading: UptimeReading) -> None:
        self.last_boot, self.last_seconds = reading.boot, reading.seconds
        self.last_at, self.fresh = reading.at, reading.fresh

    def _end_stop(self, until: datetime | None) -> None:
        if self.stopped_since is not None and until is not None and until > self.stopped_since:
            self.downs = [*self.downs, (self.stopped_since, until)][-MAX_DOWNS:]
        self.stopped, self.stopped_since = False, None

    def as_dict(self) -> dict[str, Any]:
        """For storage."""
        return {
            "count": self.count,
            "last_boot": _iso(self.last_boot),
            "last_seconds": self.last_seconds,
            "last_at": _iso(self.last_at),
            "fresh": self.fresh,
            "stopped": self.stopped,
            "stopped_since": _iso(self.stopped_since),
            "downs": [[start.isoformat(), end.isoformat()] for start, end in self.downs],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> RestartCounter:
        """From storage; a fresh counter for None."""
        if not data:
            return cls()
        return cls(
            count=int(data.get("count", 0)),
            last_boot=_moment(data.get("last_boot")),
            last_seconds=data.get("last_seconds"),
            last_at=_moment(data.get("last_at")),
            fresh=bool(data.get("fresh", False)),
            stopped=bool(data.get("stopped", False)),
            stopped_since=_moment(data.get("stopped_since")),
            downs=[
                (datetime.fromisoformat(start), datetime.fromisoformat(end))
                for start, end in data.get("downs") or []
            ],
        )


def _iso(moment: datetime | None) -> str | None:
    return moment.isoformat() if moment else None


def _moment(text: str | None) -> datetime | None:
    return datetime.fromisoformat(text) if text else None


@dataclass(slots=True)
class DailyTotal:
    """Adds up a count that covers the last 24 hours by reading it once a day.

    AdGuard Home's and Pi-hole's blocked counts are rolling 24-hour windows, so
    adding up how they change would count wrong; one reading a day, at the same
    time, adds up to the real total.
    """

    total: float = 0
    last_day: date | None = None

    def take(self, value: float, day: date) -> bool:
        """Add the day's reading; False if that day was already counted or the value is junk."""
        if day == self.last_day or not math.isfinite(value) or value < 0:
            return False
        self.total += value
        self.last_day = day
        return True

    def as_dict(self) -> dict[str, Any]:
        """For storage."""
        return {
            "total": self.total,
            "last_day": self.last_day.isoformat() if self.last_day else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> DailyTotal:
        """From storage; a fresh total for None."""
        if not data:
            return cls()
        day = data.get("last_day")
        return cls(float(data.get("total", 0)), date.fromisoformat(day) if day else None)


MAX_TITLES = 100
"""Titles kept per year, the longest played: plenty for a top five, and the store stays small."""

MAX_TITLE_LENGTH = 100


SEASON_SUFFIX = re.compile(r"[\s._-]+[(\[]?(?:s|season[\s._]*)0*(\d{1,3})[)\]]?$", re.IGNORECASE)
"""A season at the end of a series name: " S01", ".S1", " - Season 2", " (Season 3)"."""


def media_title(attributes: Mapping[str, Any]) -> str | None:
    """What a media player is playing, as a Wrapped counts it: the series of an episode,
    the artist of a song, else the title of the film or track."""
    for key in ("media_series_title", "media_artist", "media_title"):
        value = attributes.get(key)
        if isinstance(value, str) and (value := value.strip()):
            if key == "media_series_title":
                value = _without_season(value, attributes.get("media_season"))
            return value[:MAX_TITLE_LENGTH]
    return None


def _without_season(series: str, season: Any) -> str:
    """The series without the season playing at the end of its name.

    A series Jellyfin hasn't matched is named after its folder, often one per
    season ("Slow Horses S01"): counted as one series, not one per season.
    Only the season the player says it plays is taken off, so a name that
    merely ends in a number keeps it.
    """
    found = SEASON_SUFFIX.search(series)
    if found is None or isinstance(season, bool):
        return series
    try:
        playing = int(season)
    except (TypeError, ValueError):
        return series
    rest = series[: found.start()].strip()
    return rest if rest and int(found.group(1)) == playing else series


@dataclass(slots=True)
class PlaybackClock:
    """Time spent playing, added up over a media server's players, and per title.

    Two players playing for an hour make two hours. The total and the time per
    title (per year) are saved; which players are playing right now, and what,
    is picked up again after a restart.
    """

    seconds: float = 0
    playing_since: dict[str, datetime] = field(default_factory=dict)
    playing_title: dict[str, str] = field(default_factory=dict)
    titles: dict[str, dict[str, float]] = field(default_factory=dict)
    """Year (as text) -> title -> seconds played."""

    def update(
        self,
        player: str,
        playing: bool,
        at: datetime,
        *,
        title: str | None = None,
        year: int | None = None,
    ) -> float:
        """A player started or stopped playing, or moved on to another title.

        What it played until ``at`` counts for its previous title, in ``year``
        (the local year of ``at``). Returns the seconds added.
        """
        added = self._settle(player, at, year)
        if playing:
            self.playing_since[player] = at
            if title:
                self.playing_title[player] = title
            else:
                self.playing_title.pop(player, None)
        else:
            self.playing_since.pop(player, None)
            self.playing_title.pop(player, None)
        return added

    def settle(self, at: datetime, year: int | None = None) -> float:
        """Count what the playing players have played so far; returns the seconds added."""
        return sum(self._settle(player, at, year) for player in list(self.playing_since))

    def top_titles(self, year: int) -> dict[str, float]:
        """Hours per title in ``year``."""
        return {title: seconds / 3600 for title, seconds in self.titles.get(str(year), {}).items()}

    def _settle(self, player: str, at: datetime, year: int | None) -> float:
        since = self.playing_since.get(player)
        if since is None:
            return 0.0
        self.playing_since[player] = at
        added = max(0.0, (at - since).total_seconds())
        self.seconds += added
        if added and year is not None and (title := self.playing_title.get(player)):
            per_title = self.titles.setdefault(str(year), {})
            per_title[title] = per_title.get(title, 0.0) + added
            if len(per_title) > MAX_TITLES * 3 // 2:
                kept = sorted(per_title.items(), key=lambda item: -item[1])[:MAX_TITLES]
                self.titles[str(year)] = dict(kept)
        return added

    def as_dict(self) -> dict[str, Any]:
        """For storage."""
        return {
            "seconds": self.seconds,
            "titles": {
                year: {title: round(seconds, 1) for title, seconds in per_title.items()}
                for year, per_title in self.titles.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> PlaybackClock:
        """From storage; a fresh clock for None."""
        data = data or {}
        titles = data.get("titles")
        return cls(
            float(data.get("seconds", 0)),
            titles={
                str(year): {str(title): float(seconds) for title, seconds in per_title.items()}
                for year, per_title in (titles.items() if isinstance(titles, dict) else ())
                if isinstance(per_title, dict)
            },
        )


MAX_CUT = timedelta(hours=12)
"""The longest a power cut counts for: past that, HA was down too (the UPS ran out)."""

MAX_CUTS = 500
"""Cuts kept, the latest: years of them for any UPS that isn't broken."""

BATTERY_WORDS = frozenset({"OB", "ONBATT"})
"""What a UPS status says while it runs on battery: NUT's "OB", APC UPS Daemon's "ONBATT"."""

MAINS_WORDS = frozenset({"OL", "ONLINE"})
"""What it says while it runs on mains."""


def on_battery(status: str) -> bool | None:
    """Whether a UPS status (such as "OB DISCHRG" or "ONLINE") says it runs on battery.

    None for a status that says neither: unavailable, unknown, APC UPS Daemon's
    "COMMLOST" or "SHUTTING DOWN", NUT's "WAIT" or "OFF". Taking those for mains
    would end a cut that is still going on and count it twice.
    """
    words = set(status.upper().split())
    if words & BATTERY_WORDS:
        return True
    if words & MAINS_WORDS:
        return False
    return None


@dataclass(slots=True)
class PowerCuts:
    """The times a UPS ran on battery: how many, and when and how long each lasted.

    A cut still going on is saved too, so a restart of HA in the middle of one
    doesn't count it twice.
    """

    count: int = 0
    since: datetime | None = None
    """On battery since then; None on mains."""
    cuts: list[tuple[datetime, float]] = field(default_factory=list)
    """(start, seconds) of the latest ``MAX_CUTS`` cuts that ended."""

    def observe(self, battery: bool, at: datetime) -> bool:
        """A status; True if a cut began or ended."""
        if battery and self.since is None:
            self.since = at
            self.count += 1
            return True
        if not battery and self.since is not None:
            seconds = min(max(0.0, (at - self.since).total_seconds()), MAX_CUT.total_seconds())
            self.cuts = [*self.cuts, (self.since, seconds)][-MAX_CUTS:]
            self.since = None
            return True
        return False

    def all_cuts(self, now: datetime) -> list[tuple[datetime, float]]:
        """Every cut kept, with one still going on counted up to ``now``."""
        if self.since is None:
            return list(self.cuts)
        ongoing = min(max(0.0, (now - self.since).total_seconds()), MAX_CUT.total_seconds())
        return [*self.cuts, (self.since, ongoing)]

    def as_dict(self) -> dict[str, Any]:
        """For storage."""
        return {
            "count": self.count,
            "since": self.since.isoformat() if self.since else None,
            "cuts": [[start.isoformat(), seconds] for start, seconds in self.cuts],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> PowerCuts:
        """From storage; a fresh tally for None."""
        if not data:
            return cls()
        since = data.get("since")
        return cls(
            int(data.get("count", 0)),
            datetime.fromisoformat(since) if since else None,
            [
                (datetime.fromisoformat(start), float(seconds))
                for start, seconds in data.get("cuts", [])
            ],
        )
