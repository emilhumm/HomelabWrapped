"""The coverage check: which cards this lab can make today.

Each card is in one of three states:

- ready: the data is there, and the card says how far back it goes;
- counting: the data source is connected, but there isn't enough history yet;
  Wrapped (or HA's long-term statistics) is collecting it, and the card says when
  it will be ready;
- locked: nothing gives this data yet; the card lists what would unlock it.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum
from typing import Any

from .model import Inventory
from .sources import ADAPTERS, Adapter, Found, Signal, find_signals, unlocked_by

MIN_DAYS = 7
"""History a data card needs before it is worth showing."""

PERSONALITY_NEEDS = 2
"""Ready data cards the personality card is built from."""


class CardId(StrEnum):
    """The cards, in story order."""

    INTRO = "intro"
    UPTIME = "uptime"
    RESTARTS = "restarts"
    BLOCKED = "blocked"
    MEDIA = "media"
    POWER = "power"
    PERSONALITY = "personality"
    SUMMARY = "summary"


class CardState(StrEnum):
    """How far a card is from being made."""

    READY = "ready"
    COUNTING = "counting"
    LOCKED = "locked"


class Hint(StrEnum):
    """Extra notes on a card; the frontend turns them into text."""

    HISTORY_BREAK = "history_break"
    """HA stopped keeping long-term statistics for a source, usually after an integration
    update changed its type. Wrapped stitches the old history to what it records now."""
    PRICE_HOURLY = "price_hourly"
    """Priced with the price sensor's hourly history."""
    PRICE_LIVE = "price_live"
    """The price sensor has no history yet; prices are collected from now on."""
    PRICE_FIXED = "price_fixed"
    """Priced with the fixed price from the Energy dashboard."""
    PRICE_MISSING = "price_missing"
    """No price: the card shows kWh only until a price is added to the Energy dashboard."""
    PICK_METERS = "pick_meters"
    """Power is locked until the user picks the meters that measure the lab (options)."""


DATA_CARDS: Mapping[CardId, frozenset[Signal]] = {
    CardId.UPTIME: frozenset({Signal.UPTIME, Signal.SERVICE}),
    CardId.RESTARTS: frozenset({Signal.UPTIME, Signal.CONTAINER_UPTIME, Signal.NETWORK_UPTIME}),
    CardId.BLOCKED: frozenset({Signal.DNS_BLOCKED}),
    CardId.MEDIA: frozenset({Signal.MEDIA}),
    CardId.POWER: frozenset({Signal.ENERGY, Signal.UPS}),
}
"""Which signals feed each data card. Power is fed by the lab meters the user picked,
not by every energy meter (the house's meters aren't the lab's), and by a UPS's power
cuts."""
INTRO_SIGNALS = frozenset({Signal.HOST, Signal.GUEST, Signal.CONTAINER})

FROM_STATISTICS = frozenset({Signal.UPTIME, Signal.NETWORK_UPTIME, Signal.ENERGY, Signal.SERVICE})
"""Signals the cards read from the source's long-term statistics: only for these does a
stopped history (a lost state_class) matter."""

DATED_BY: Mapping[CardId, tuple[frozenset[Signal], ...]] = {
    CardId.UPTIME: (frozenset({Signal.UPTIME}),),
    CardId.RESTARTS: (
        frozenset({Signal.UPTIME}),
        frozenset({Signal.CONTAINER_UPTIME, Signal.NETWORK_UPTIME}),
    ),
    CardId.POWER: (frozenset({Signal.ENERGY}), frozenset({Signal.UPS})),
}
"""How far back a card goes is its main numbers', as on its slide: the servers' (not the
routers' or containers'), the meters' (not the UPS's). The next ones only without those."""


@dataclass(frozen=True, slots=True)
class CardCoverage:
    """Where one card stands."""

    card: CardId
    state: CardState
    since: date | None = None
    """How far back its data goes (ready), or since when it has been collected (counting)."""
    ready_on: date | None = None
    """When a counting card will have enough history."""
    sources: tuple[str, ...] = ()
    """Names of what the card is built from."""
    unlock: tuple[str, ...] = ()
    """For a locked card: names of integrations that would unlock it."""
    hints: tuple[Hint, ...] = ()

    @property
    def number(self) -> int:
        """Position in the story, from 1."""
        return list(CardId).index(self.card) + 1

    def as_dict(self) -> dict[str, Any]:
        """JSON-friendly form for the frontend and diagnostics."""
        return {
            "card": self.card.value,
            "number": self.number,
            "state": self.state.value,
            "since": self.since.isoformat() if self.since else None,
            "ready_on": self.ready_on.isoformat() if self.ready_on else None,
            "sources": list(self.sources),
            "unlock": list(self.unlock),
            "hints": [hint.value for hint in self.hints],
        }


def check_coverage(
    inventory: Inventory,
    *,
    installed: date,
    today: date,
    adapters: Iterable[Adapter] = ADAPTERS,
) -> list[CardCoverage]:
    """Where every card stands, in story order.

    ``installed`` is when Wrapped started collecting what HA doesn't keep itself.
    """
    adapters = tuple(adapters)
    found = find_signals(inventory, adapters)
    platforms = {entity.entity_id: entity.platform for entity in inventory.entities}
    found[Signal.ENERGY] = [
        Found(Signal.ENERGY, inventory.integration_names.get(platforms.get(meter, ""), ""), meter)
        for meter in inventory.lab_meters
    ]

    intro_found = [item for signal in _ordered(INTRO_SIGNALS) for item in found.get(signal, [])]
    intro = (
        CardCoverage(CardId.INTRO, CardState.READY, sources=_names(intro_found))
        if intro_found
        else CardCoverage(
            CardId.INTRO, CardState.LOCKED, unlock=unlocked_by(INTRO_SIGNALS, adapters)
        )
    )

    data_cards = [
        _data_card(
            card,
            signals,
            found=found,
            inventory=inventory,
            installed=installed,
            today=today,
            adapters=adapters,
        )
        for card, signals in DATA_CARDS.items()
    ]
    return [intro, *data_cards, _personality(data_cards, adapters), _summary([intro, *data_cards])]


def _data_card(
    card: CardId,
    signals: frozenset[Signal],
    *,
    found: Mapping[Signal, list[Found]],
    inventory: Inventory,
    installed: date,
    today: date,
    adapters: tuple[Adapter, ...],
) -> CardCoverage:
    items = [item for signal in _ordered(signals) for item in found.get(signal, [])]
    if not items:
        if card is CardId.POWER:
            # Meters are picked in the options; a UPS's power cuts make the card too.
            return CardCoverage(
                card,
                CardState.LOCKED,
                unlock=unlocked_by({Signal.UPS}, adapters),
                hints=(Hint.PICK_METERS,),
            )
        return CardCoverage(card, CardState.LOCKED, unlock=unlocked_by(signals, adapters))

    hints: list[Hint] = []
    starts = [installed]
    entities = {entity.entity_id: entity for entity in inventory.entities}
    dated = _dated(card, items)
    for item in items:
        if (
            item in dated
            and item.entity_id is not None
            and (day := inventory.backfilled.get(item.entity_id))
        ):
            starts.append(day)
        if (
            item.entity_id is None
            or (statistic := inventory.statistics.get(item.entity_id)) is None
        ):
            continue
        if item in dated and statistic.first is not None:
            starts.append(statistic.first)
        # HA has statistics for the entity but no longer keeps them: its state_class is gone.
        entity = entities.get(item.entity_id)
        if (
            entity is not None
            and entity.state_class is None
            and item.signal in FROM_STATISTICS
            and Hint.HISTORY_BREAK not in hints
        ):
            hints.append(Hint.HISTORY_BREAK)
    if card is CardId.POWER:
        if any(item.signal is Signal.ENERGY for item in items):
            hints.append(_price_hint(inventory))
        else:
            hints.append(Hint.PICK_METERS)  # only a UPS so far

    since = min(starts)
    ready_on = since + timedelta(days=MIN_DAYS)
    if today >= ready_on:
        return CardCoverage(
            card, CardState.READY, since=since, sources=_names(items), hints=tuple(hints)
        )
    return CardCoverage(
        card,
        CardState.COUNTING,
        since=since,
        ready_on=ready_on,
        sources=_names(items),
        hints=tuple(hints),
    )


def _price_hint(inventory: Inventory) -> Hint:
    """How the Power card prices: the Energy dashboard's first price sensor, else its fixed
    price. A price sensor that isn't in the dashboard isn't used, so it doesn't count here."""
    energy = inventory.energy
    if energy.price_entities:
        if energy.price_entities[0] in inventory.statistics:
            return Hint.PRICE_HOURLY
        return Hint.PRICE_LIVE
    if energy.fixed_price is not None:
        return Hint.PRICE_FIXED
    return Hint.PRICE_MISSING


def _personality(data_cards: list[CardCoverage], adapters: tuple[Adapter, ...]) -> CardCoverage:
    """Built from at least two ready data cards, as the story builds it."""
    ready = [c for c in data_cards if c.state is CardState.READY]
    if len(ready) >= PERSONALITY_NEEDS:
        return CardCoverage(CardId.PERSONALITY, CardState.READY)
    coming = sorted(c.ready_on for c in data_cards if c.ready_on is not None)
    missing = PERSONALITY_NEEDS - len(ready)
    if len(coming) >= missing:
        return CardCoverage(CardId.PERSONALITY, CardState.COUNTING, ready_on=coming[missing - 1])
    locked = {s for c in data_cards if c.state is CardState.LOCKED for s in DATA_CARDS[c.card]}
    return CardCoverage(CardId.PERSONALITY, CardState.LOCKED, unlock=unlocked_by(locked, adapters))


def _summary(cards: list[CardCoverage]) -> CardCoverage:
    """Ready as soon as any card before it is."""
    if any(c.state is CardState.READY for c in cards):
        return CardCoverage(CardId.SUMMARY, CardState.READY)
    coming = [c.ready_on for c in cards if c.ready_on is not None]
    if coming:
        return CardCoverage(CardId.SUMMARY, CardState.COUNTING, ready_on=min(coming))
    return CardCoverage(CardId.SUMMARY, CardState.LOCKED)


def wrapped_years(cards: Iterable[CardCoverage], today: date) -> tuple[list[int], int]:
    """The years a Wrapped can be played for, oldest first, and the one to start with.

    A year can be played once any card has data in it. In January the year that
    just ended comes first: its story is complete, and it is the one people look
    back on then (a Wrapped of a few January days says nothing yet).
    """
    sinces = [card.since for card in cards if card.since is not None]
    first = min(min(sinces, default=today).year, today.year)
    years = list(range(first, today.year + 1))
    start = today.year - 1 if today.month == 1 and today.year - 1 in years else today.year
    return years, start


def _dated(card: CardId, items: list[Found]) -> list[Found]:
    """The items a card's "since" comes from (``DATED_BY``); all of them by default."""
    for signals in DATED_BY.get(card, ()):
        if main := [item for item in items if item.signal in signals]:
            return main
    return items


def _ordered(signals: frozenset[Signal]) -> list[Signal]:
    """In the order they're defined (a set's order changes with each start of Python), so a
    card's sources read the same every time: its main source first."""
    return [signal for signal in Signal if signal in signals]


def _names(items: Iterable[Found]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item.source for item in items if item.source))
