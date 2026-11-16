"""What a loaded config entry keeps, and the reports built from it."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration
from homeassistant.util import dt as dt_util

from .backfill import BackfillStore
from .const import CONF_LAB_METERS, CONF_LEFT_OUT, DOMAIN
from .core.cards import (
    Kind,
    Year,
    blocked_card,
    intro_card,
    media_card,
    personality_card,
    power_card,
    restarts_card,
    uptime_card,
)
from .core.coverage import CardCoverage, check_coverage, wrapped_years
from .core.diagnostics import diagnostics
from .core.model import Inventory
from .core.sources import count_found, find_signals
from .history import async_card_inputs
from .inventory import FirstDays, async_build_inventory
from .storage import TallyStore

CARDS_REUSED_FOR = timedelta(minutes=10)
"""How long a computed set of cards is reused before statistics are read again."""


@dataclass(slots=True)
class Wrapped:
    """Homelab Wrapped while it is loaded."""

    hass: HomeAssistant
    entry_id: str
    installed: date
    """The day Wrapped started collecting what HA doesn't keep itself."""
    first_days: FirstDays
    tally: TallyStore
    """State of Wrapped's own counters (restarts, blocked queries, playback)."""
    backfill: BackfillStore
    """What the recorder still had from before each counter started."""
    _cards_lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)
    _cards: dict[int, tuple[datetime, dict[str, Any]]] = field(
        default_factory=dict, init=False, repr=False
    )

    @property
    def lab_meters(self) -> tuple[str, ...]:
        """The energy meters the user picked as measuring the lab (in the options)."""
        entry = self.hass.config_entries.async_get_entry(self.entry_id)
        return tuple(entry.options.get(CONF_LAB_METERS, [])) if entry else ()

    @property
    def left_out(self) -> frozenset[str]:
        """Device ids the user chose to leave out (in the options)."""
        entry = self.hass.config_entries.async_get_entry(self.entry_id)
        return frozenset(entry.options.get(CONF_LEFT_OUT, [])) if entry else frozenset()

    async def async_coverage(self) -> tuple[Inventory, list[CardCoverage]]:
        """What the lab has, and where every card stands today."""
        inventory = await async_build_inventory(
            self.hass, self.first_days, self.lab_meters, self.left_out, self.backfill.found
        )
        today = dt_util.now().date()
        return inventory, check_coverage(inventory, installed=self.installed, today=today)

    async def async_coverage_report(self) -> dict[str, Any]:
        """The coverage screen's data."""
        inventory, cards = await self.async_coverage()
        years, year = wrapped_years(cards, dt_util.now().date())
        return {
            "installed": self.installed.isoformat(),
            "cards": [card.as_dict() for card in cards],
            "signals": count_found(find_signals(inventory)),
            "years": years,
            "year": year,
        }

    def forget_cards(self) -> None:
        """New history came in (the look-back found some): build the cards afresh."""
        self._cards = {}

    async def async_cards(self, year: int | None = None) -> dict[str, Any]:
        """The story cards for a calendar year, this year by default.

        They read a year of hourly statistics, so one computation runs at a time
        (several tabs or clicks wait for it) and its result is reused for a few
        minutes. Only the latest year asked for is kept.
        """
        now = dt_util.now()
        number = year or now.year
        async with self._cards_lock:
            cached = self._cards.get(number)
            if cached and now - cached[0] < CARDS_REUSED_FOR:
                return cached[1]
            report = await self._async_build_cards(number, now)
            self._cards = {number: (now, report)}
            return report

    async def _async_build_cards(self, year: int, now: datetime) -> dict[str, Any]:
        period = Year.of(year, now=now, tz=dt_util.get_default_time_zone())
        _, coverage = await self.async_coverage()
        inputs = await async_card_inputs(
            self.hass,
            self.entry_id,
            period,
            lab_meters=self.lab_meters,
            left_out=self.left_out,
            backfilled=self.backfill.found,
            tally=self.tally,
        )
        built = [
            uptime_card(inputs.machines, period, inputs.services),
            restarts_card(inputs.machines, period),
            blocked_card(inputs.blocked, period),
            media_card(inputs.media, period, inputs.titles),
            power_card(inputs.meters, inputs.price, period, inputs.ups),
        ]
        sinces = [date.fromisoformat(card["since"]) for card in built if card and card["since"]]
        watched = [
            m
            for m in inputs.machines
            if m.kind is Kind.SERVER
            and (first := m.since or m.last_boot) is not None
            and first < period.end
        ]
        intro = intro_card(inputs.counts, machines=len(watched), since=min(sinces, default=None))
        found = [card for card in (intro, *built) if card]
        if personality := personality_card(found, period):
            found.append(personality)
        states = {card.card.value: card.state.value for card in coverage}
        return {
            "year": period.number,
            "cards": [card | {"state": states[card["card"]]} for card in found],
        }

    async def async_diagnostics(self) -> dict[str, Any]:
        """The "copy diagnostics" report: no entity ids, names, hostnames or IPs."""
        inventory, cards = await self.async_coverage()
        integration = await async_get_integration(self.hass, DOMAIN)
        return {
            "version": str(integration.version),
            "home_assistant": HA_VERSION,
            "installed": self.installed.isoformat(),
            "left_out": len(self.left_out),
            "looked_back": {
                "sensors": len(self.backfill.found),
                "with_history": sum(1 for item in self.backfill.found.values() if item.start),
            },
            **diagnostics(inventory, cards),
        }


type WrappedConfigEntry = ConfigEntry[Wrapped]


def loaded(hass: HomeAssistant) -> Wrapped | None:
    """The loaded instance, if Homelab Wrapped is set up."""
    entries: list[WrappedConfigEntry] = hass.config_entries.async_loaded_entries(DOMAIN)
    return entries[0].runtime_data if entries else None
