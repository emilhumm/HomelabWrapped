"""Reads the histories the cards are built from, out of HA's long-term statistics.

- Restarts, per machine (one per device), per Docker container and per piece of
  network gear: an uptime
  counter's own hourly min/max, where HA keeps them, merged with the increases
  of Wrapped's restarts sensor, its exact last boot time and what the look-back
  found in the recorder from before the sensor existed.
- Blocked queries and playback: the daily increases of Wrapped's sensors, and
  the days the look-back found before them. Hours per title come from the
  playback sensors' own storage (HA's statistics only keep the total).
- Power: the lab meters' hourly kWh, priced with the Energy dashboard's price
  sensor hour by hour (its hourly mean, or the hour's last price for a "total"
  one), else its fixed price.
- Power cuts: from the power cuts sensors' own storage (when and how long), and
  what the look-back found before them.
- Services: each Uptime Kuma monitor's 365-day uptime at the end of the period
  (its last hourly mean), or its state now when the period is this year and
  HA hasn't compiled an hour yet.

All statistics are read in one job in the recorder's executor.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Collection, Iterable, Iterator, Mapping
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta
import math
from typing import Any, Literal

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import (
    async_list_statistic_ids,
    statistics_during_period,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .core.backfill import Backfilled
from .core.cards import (
    Daily,
    Hourly,
    Kind,
    Machine,
    Price,
    Service,
    Ups,
    Year,
    merge_machines,
    price_unit,
    to_kwh,
)
from .core.model import Inventory
from .core.sources import ADAPTERS, Found, Signal, count_found, find_signals
from .core.tally import PlaybackClock, PowerCuts, RestartCounter
from .core.uptime import HourStat, counter_restarts, to_seconds
from .inventory import read_devices, read_energy, read_entities, source_name, split_unique_id
from .storage import TallyStore

MAX_RESTARTS_PER_HOUR = 60
"""More in one hour is a hand-edited statistic, not a machine; it is capped."""

type _Type = Literal["change", "last_reset", "max", "mean", "min", "state", "sum"]


@dataclass(slots=True)
class CardInputs:
    """Everything the card builders need, as plain data."""

    machines: list[Machine]
    blocked: list[Daily]
    media: list[Daily]
    counts: dict[str, int]
    meters: list[Hourly] = field(default_factory=list)
    price: Price | None = None
    titles: dict[str, float] = field(default_factory=dict)
    """Hours per title played in the year, over all media servers."""
    services: list[Service] = field(default_factory=list)
    ups: list[Ups] = field(default_factory=list)


@dataclass(slots=True)
class _MachinePlan:
    name: str
    kind: Kind = Kind.SERVER
    counters: list[str] = field(default_factory=list)
    """Its sources that are still there: their own statistics, and whether they're up."""
    recorded: list[tuple[Backfilled | None, str | None]] = field(default_factory=list)
    """Per source: what the look-back found, and Wrapped's restarts sensor that counted after."""
    boots: list[datetime] = field(default_factory=list)
    down: list[tuple[datetime, datetime | None]] = field(default_factory=list)
    """When it wasn't running (stopped guests)."""
    until: datetime | None = None
    """Not seen since: every source is unavailable (a VM deleted in Proxmox VE)."""

    @property
    def ours(self) -> list[str]:
        """Wrapped's restarts sensors for it."""
        return [own for _, own in self.recorded if own]


@dataclass(slots=True)
class _Query:
    """What to read; units are the statistics' own."""

    counters: dict[str, str] = field(default_factory=dict)
    restarts: set[str] = field(default_factory=set)
    daily: set[str] = field(default_factory=set)
    meters: dict[str, str] = field(default_factory=dict)
    price: tuple[str, float] | None = None
    """The price sensor and the factor that turns its price into per kWh."""
    services: set[str] = field(default_factory=set)


@dataclass(slots=True)
class _Rows:
    """What was read."""

    hours: dict[str, list[HourStat]] = field(default_factory=dict)
    increases: dict[str, tuple[datetime, list[datetime]]] = field(default_factory=dict)
    days: dict[str, dict[date, float]] = field(default_factory=dict)
    kwh: dict[str, dict[datetime, float]] = field(default_factory=dict)
    prices: dict[datetime, float] = field(default_factory=dict)
    uptime: dict[str, float] = field(default_factory=dict)
    """Each service's 365-day uptime at the end of the period."""
    last_seen: dict[str, datetime] = field(default_factory=dict)
    """When each restarts sensor's statistics end (a gone source's sensor stops then)."""


async def async_card_inputs(
    hass: HomeAssistant,
    entry_id: str,
    year: Year,
    *,
    lab_meters: Iterable[str] = (),
    left_out: Collection[str] = (),
    backfilled: Mapping[str, Backfilled] | None = None,
    tally: TallyStore | None = None,
) -> CardInputs:
    """Read what the cards need for ``year``; devices in ``left_out`` don't count.

    ``backfilled`` is what the look-back found, by Wrapped's sensors' unique ids;
    ``tally`` is the counters' own storage (for the hours per title).
    """
    backfilled = backfilled or {}
    registry = er.async_get(hass)
    found = find_signals(Inventory(read_entities(hass, left_out), read_devices(hass, left_out)))
    ours = {
        entry.unique_id: entry.entity_id
        for entry in er.async_entries_for_config_entry(registry, entry_id)
    }

    plans = _plans(hass, found, ours, backfilled, tally=tally, left_out=left_out)

    adapters = {adapter.key: adapter.name for adapter in ADAPTERS}
    daily: dict[str, tuple[str, str, Backfilled | None]] = {}  # our entity -> kind, name, earlier
    titles: defaultdict[str, float] = defaultdict(float)
    for unique_id, entity_id in ours.items():
        kind, key = split_unique_id(unique_id)
        earlier = backfilled.get(unique_id)
        if kind == "blocked":
            source = registry.async_get(key)
            if source is not None and source.device_id in left_out:
                continue
            # A replaced DNS blocker's year still counts, under the name kept with its count.
            saved = tally.get(unique_id) if tally else None
            name = source_name(hass, source.entity_id) if source else (saved or {}).get("name")
            if name:
                daily[entity_id] = (kind, str(name), earlier)
        elif kind == "playback":
            daily[entity_id] = (kind, adapters.get(key, key), earlier)
            _add_titles(titles, year, earlier, tally.get(unique_id) if tally else None)

    energy = await read_energy(hass)
    price_entity = energy.price_entities[0] if energy.price_entities else None
    meters = list(lab_meters)
    services = {
        item.entity_id: source_name(hass, item.entity_id)
        for item in found.get(Signal.SERVICE, [])
        if item.entity_id
    }
    wanted = (
        {i for plan in plans.values() for i in plan.counters + plan.ours}
        | set(daily)
        | set(meters)
        | set(services)
        | ({price_entity} if price_entity else set())
    )
    units: dict[str, str | None] = {
        item["statistic_id"]: item.get("statistics_unit_of_measurement")
        for item in await async_list_statistic_ids(hass, statistic_ids=wanted)
    }
    query = _Query(
        counters={
            i: unit
            for plan in plans.values()
            for i in plan.counters
            if (unit := units.get(i)) is not None and to_seconds(1, unit) is not None
        },
        restarts={i for plan in plans.values() for i in plan.ours if i in units},
        daily={i for i in daily if i in units},
        meters={i: unit for i in meters if (unit := units.get(i)) and to_kwh(1, unit) is not None},
        services={i for i in services if i in units},
    )
    currency = hass.config.currency
    if price_entity and (found_unit := price_unit(units.get(price_entity))):
        currency, factor = found_unit
        query.price = (price_entity, factor)
    rows = await get_instance(hass).async_add_executor_job(_read, hass, year, query)

    machines = [_machine(plan, rows) for plan in plans.values()]
    blocked: list[Daily] = []
    media: list[Daily] = []
    for entity_id, (kind, name, earlier) in daily.items():
        # The look-back ends where the sensor began, so on the day it was created
        # each has its own part (playback before and after); they add up.
        days = dict(earlier.days) if earlier else {}
        for day, amount in rows.days.get(entity_id, {}).items():
            days[day] = days.get(day, 0.0) + amount
        series = Daily(name, days)
        (blocked if kind == "blocked" else media).append(series)

    price = None
    if rows.prices or energy.fixed_price is not None:
        price = Price(currency, rows.prices, energy.fixed_price)
    return CardInputs(
        machines,
        blocked,
        media,
        count_found(found),
        [Hourly(source_name(hass, meter), rows.kwh.get(meter, {})) for meter in query.meters],
        price,
        dict(titles),
        _services(hass, services, rows, year),
        _ups(hass, found, ours, backfilled, tally),
    )


def _plans(
    hass: HomeAssistant,
    found: Mapping[Signal, list[Found]],
    ours: Mapping[str, str],
    backfilled: Mapping[str, Backfilled],
    *,
    tally: TallyStore | None = None,
    left_out: Collection[str] = (),
) -> dict[str, _MachinePlan]:
    """What to read for each machine (by device), container and piece of network gear."""
    registry = er.async_get(hass)
    now = dt_util.utcnow()
    plans: dict[str, _MachinePlan] = {}

    def record(plan: _MachinePlan, unique_id: str, own: str | None) -> None:
        plan.recorded.append((backfilled.get(unique_id), own))
        saved = tally.get(unique_id) if tally else None
        plan.down.extend(RestartCounter.from_dict(saved).down(now))

    kinds = (
        (Signal.UPTIME, Kind.SERVER),
        (Signal.CONTAINER_UPTIME, Kind.CONTAINER),
        (Signal.NETWORK_UPTIME, Kind.NETWORK),
    )
    uptime = [(item, kind) for signal, kind in kinds for item in found.get(signal, [])]
    for item, kind in uptime:
        if item.entity_id is None or (source := registry.async_get(item.entity_id)) is None:
            continue  # pragma: no cover - the inventory is read from the registry
        plan = plans.setdefault(
            f"{kind}:{item.device_id or item.entity_id}",
            _MachinePlan(source_name(hass, item.entity_id), kind),
        )
        plan.counters.append(item.entity_id)
        own = ours.get(f"restarts_{source.id}")
        record(plan, f"restarts_{source.id}", own)
        if own and (state := hass.states.get(own)) and (boot := state.attributes.get("last_boot")):
            plan.boots.append(datetime.fromisoformat(boot))

    # Not up now when every source is unavailable: HA keeps a deleted VM's entities, so its
    # last streak ends when they went, instead of running on for ever. While HA starts, every
    # entity its integration hasn't added yet is unavailable too: that machine isn't gone.
    def loaded(entity_id: str) -> bool:
        source = registry.async_get(entity_id)
        if source is None or source.config_entry_id is None:
            return True
        entry = hass.config_entries.async_get_entry(source.config_entry_id)
        return entry is None or entry.state is ConfigEntryState.LOADED

    for plan in plans.values():
        states = [hass.states.get(entity_id) for entity_id in plan.counters]
        if (
            states
            and all(s is not None and s.state == STATE_UNAVAILABLE for s in states)
            and all(loaded(entity_id) for entity_id in plan.counters)
        ):
            plan.until = max(state.last_changed for state in states if state is not None)

    # A machine whose source is gone (removed, or its entity disabled) keeps its history:
    # Wrapped's own sensor counted it, and its name and kind are kept with the count. Not a
    # left-out device, not a source that's still there (one no adapter matches any more),
    # nor counts kept before kinds were (the old any-integration rule's phones and plugs).
    planned = {own for plan in plans.values() for own in plan.ours}
    by_value = {kind.value: kind for kind in Kind}
    for unique_id, own in ours.items():
        kind_key, key = split_unique_id(unique_id)
        saved = (tally.get(unique_id) if tally else None) or {}
        if kind_key != "restarts" or own in planned or saved.get("machine") not in by_value:
            continue
        source = registry.async_get(key)
        if source is not None and (source.device_id in left_out or source.disabled_by is None):
            continue
        kind = by_value[saved["machine"]]
        # A disabled duplicate joins its device's machine.
        plan_key = f"{kind}:{source.device_id}" if source and source.device_id else unique_id
        plan = plans.setdefault(plan_key, _MachinePlan(str(saved.get("name") or own), kind))
        record(plan, unique_id, own)
    return plans


def _ups(
    hass: HomeAssistant,
    found: Mapping[Signal, list[Found]],
    ours: Mapping[str, str],
    backfilled: Mapping[str, Backfilled],
    tally: TallyStore | None,
) -> list[Ups]:
    """Each UPS's power cuts: what the look-back found, and what the sensor counted.

    It is watched from where the look-back's states start, else from when
    Wrapped's sensor was created.
    """
    registry = er.async_get(hass)
    now = dt_util.utcnow()
    units = []
    for item in found.get(Signal.UPS, []):
        if item.entity_id is None or (source := registry.async_get(item.entity_id)) is None:
            continue  # pragma: no cover - the inventory is read from the registry
        key = f"power_cuts_{source.id}"
        earlier = backfilled.get(key)
        own = registry.async_get(ours[key]) if key in ours else None
        counted = PowerCuts.from_dict(tally.get(key) if tally else None)
        sinces = [
            moment for moment in (earlier and earlier.start, own and own.created_at) if moment
        ]
        cuts = [*(earlier.cuts if earlier else ()), *counted.all_cuts(now)]
        units.append(Ups(source_name(hass, item.entity_id), tuple(cuts), min(sinces, default=None)))
    return units


def _services(
    hass: HomeAssistant, services: dict[str, str], rows: _Rows, year: Year
) -> list[Service]:
    """Each service's uptime at the end of the period; its state now, if that is now."""
    now = year.end >= dt_util.utcnow() - timedelta(hours=2)
    found = []
    for entity_id, name in services.items():
        uptime = rows.uptime.get(entity_id)
        if uptime is None and now and (state := hass.states.get(entity_id)):
            try:
                uptime = float(state.state)
            except ValueError:
                continue
        if uptime is not None and math.isfinite(uptime) and 0 <= uptime <= 100:
            found.append(Service(name, uptime))
    return found


def _add_titles(
    titles: defaultdict[str, float],
    year: Year,
    earlier: Backfilled | None,
    saved: dict[str, Any] | None,
) -> None:
    """Hours per title in ``year``: what the look-back found, and what the sensor counted."""
    if earlier:
        for title, hours in earlier.titles.get(str(year.number), {}).items():
            titles[title] += hours
    for title, hours in PlaybackClock.from_dict(saved).top_titles(year.number).items():
        titles[title] += hours


def _machine(plan: _MachinePlan, rows: _Rows) -> Machine:
    """One machine (or container) from everything that saw it."""
    parts = [Machine(plan.name, last_boot=boot) for boot in plan.boots]
    for statistic_id in plan.counters:
        if stats := rows.hours.get(statistic_id):
            parts.append(Machine(plan.name, tuple(counter_restarts(stats)), stats[0].start))
    for earlier, own in plan.recorded:
        # The look-back's restarts end where the sensor's begin: one record, not two sources
        # to match (two restarts an hour apart either side of the handover are two).
        restarts: list[datetime] = []
        starts: list[datetime] = []
        if earlier is not None and earlier.start is not None:
            restarts += earlier.restarts
            starts.append(earlier.start)
        if own is not None and own in rows.increases:
            first, moments = rows.increases[own]
            restarts += moments
            starts.append(first)
        if starts:
            parts.append(Machine(plan.name, tuple(sorted(restarts)), min(starts)))
    until = plan.until
    if not plan.counters:  # gone: its sensor's statistics end when it went
        until = max(
            (rows.last_seen[own] for own in plan.ours if own in rows.last_seen), default=None
        )
    down = [*plan.down, *([(until, None)] if until else [])]
    machine = merge_machines(plan.name, parts, kind=plan.kind)
    return replace(machine, down=tuple(down))


def _read(hass: HomeAssistant, year: Year, query: _Query) -> _Rows:
    """Runs in the recorder's executor."""
    rows = _Rows()

    def during(
        ids: Iterable[str], period: Literal["hour", "day"], types: set[_Type]
    ) -> Iterator[tuple[str, list[Any]]]:
        """Each statistic's rows, one statistic at a time: a year of hourly rows for a lab's
        hundred containers at once would take hundreds of MB on a small box."""
        for statistic_id in sorted(ids):
            found = statistics_during_period(
                hass, year.start, year.end, {statistic_id}, period, None, types
            )
            if rows := found.get(statistic_id):
                yield statistic_id, rows

    # A "measurement" counter keeps each hour's min and max; a "total" one (the ASUS
    # routers' uptime) only the value at the end of the hour, which then stands for both.
    for statistic_id, found in during(query.counters, "hour", {"min", "max", "state"}):
        unit = query.counters[statistic_id]
        hours = []
        for row in found:
            low = _seconds(row.get("min"), unit)
            high = _seconds(row.get("max"), unit)
            if low is None or high is None:
                low = high = _seconds(row.get("state"), unit)
            if low is not None and high is not None:
                hours.append(HourStat(_moment(row), low, high))
        rows.hours[statistic_id] = hours

    for statistic_id, found in during(query.restarts, "hour", {"change"}):
        moments = [
            _moment(row)
            for row in found
            for _ in range(min(MAX_RESTARTS_PER_HOUR, round(row.get("change") or 0)))
        ]
        rows.increases[statistic_id] = (_moment(found[0]), moments)
        rows.last_seen[statistic_id] = _moment(found[-1]) + timedelta(hours=1)

    days: dict[str, dict[date, float]] = defaultdict(dict)
    for statistic_id, found in during(query.daily, "day", {"change"}):
        for row in found:
            if (change := row.get("change")) and change > 0:
                days[statistic_id][dt_util.as_local(_moment(row)).date()] = change
    rows.days = dict(days)

    for statistic_id, found in during(query.meters, "hour", {"change"}):
        unit = query.meters[statistic_id]
        rows.kwh[statistic_id] = {
            _moment(row): kwh
            for row in found
            if (kwh := to_kwh(row.get("change") or 0, unit)) is not None and kwh > 0
        }

    if query.services:
        last_hours = max(year.start, year.end - timedelta(days=2))
        ends = statistics_during_period(
            hass, last_hours, year.end, query.services, "hour", None, {"mean"}
        )
        for statistic_id, last in ends.items():
            means = [mean for row in last if (mean := row.get("mean")) is not None]
            if means:
                rows.uptime[statistic_id] = means[-1]

    if query.price is not None:
        # A "measurement" price keeps each hour's mean; a "total" one (Energi Data
        # Service) only the price at the end of the hour, the best there is for it.
        price_id, factor = query.price
        for row in dict(during({price_id}, "hour", {"mean", "state"})).get(price_id, []):
            value = row.get("mean")
            if value is None:
                value = row.get("state")
            if value is not None and math.isfinite(value):
                rows.prices[_moment(row)] = value * factor
    return rows


def _moment(row: Any) -> datetime:
    return dt_util.utc_from_timestamp(row["start"])


def _seconds(value: float | None, unit: str) -> float | None:
    return None if value is None else to_seconds(value, unit)
