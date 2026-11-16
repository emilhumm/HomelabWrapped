"""The "copy diagnostics" report, with names stripped.

It doubles as the support tool and as the starting point for a new adapter:
it shows what each integration in the lab provides (domain, device_class,
unit, state_class, translation_key) without a single entity id, device id,
name, hostname or IP. Entities are grouped and counted, never listed.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import Any

from .coverage import CardCoverage
from .model import Inventory
from .sources import ADAPTERS, Adapter, count_found, find_signals


def diagnostics(
    inventory: Inventory,
    coverage: Iterable[CardCoverage],
    *,
    adapters: Iterable[Adapter] = ADAPTERS,
) -> dict[str, Any]:
    """A JSON-friendly report of what the lab has, without names."""
    adapters = tuple(adapters)
    groups: Counter[tuple[str, str, str | None, str | None, str | None, str | None, bool]] = (
        Counter()
    )
    for entity in inventory.entities:
        groups[
            (
                entity.platform,
                entity.domain,
                entity.device_class,
                entity.unit,
                entity.state_class,
                entity.translation_key,
                entity.entity_id in inventory.statistics,
            )
        ] += 1

    devices: Counter[tuple[str, bool]] = Counter()
    for device in inventory.devices:
        for integration in device.integrations:
            devices[(integration, device.via_device_id is not None)] += 1

    return {
        "cards": [card.as_dict() for card in coverage],
        "signals": count_found(find_signals(inventory, adapters)),
        "energy": {
            "grid_import": len(inventory.energy.grid_import),
            "price_entities": len(inventory.energy.price_entities),
            "fixed_price": inventory.energy.fixed_price is not None,
            "lab_meters": len(inventory.lab_meters),
        },
        "devices": [
            {"integration": integration, "via_device": via, "count": count}
            for (integration, via), count in sorted(devices.items())
        ],
        "entities": [
            {
                "integration": platform,
                "domain": domain,
                "device_class": device_class,
                "unit": unit,
                "state_class": state_class,
                "translation_key": translation_key,
                "long_term_statistics": has_statistics,
                "count": count,
            }
            for (
                platform,
                domain,
                device_class,
                unit,
                state_class,
                translation_key,
                has_statistics,
            ), count in sorted(groups.items(), key=lambda item: _sort_key(item[0]))
        ],
    }


def _sort_key(
    group: tuple[str, str, str | None, str | None, str | None, str | None, bool],
) -> tuple[str, ...]:
    return tuple("" if part is None else str(part) for part in group)
