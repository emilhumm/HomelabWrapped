"""Plain data the core works on.

The Home Assistant layer (or later a standalone version) fills these in.
Nothing in here knows where the data came from.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True, slots=True)
class Entity:
    """One entity, described by what it is rather than what it is called."""

    entity_id: str
    domain: str
    """sensor, binary_sensor, media_player, update ..."""
    platform: str
    """The integration that created it: proxmoxve, adguard, jellyfin ..."""
    device_id: str | None = None
    device_class: str | None = None
    unit: str | None = None
    state_class: str | None = None
    """As the entity has it now. HA only keeps long-term statistics while it is set."""
    translation_key: str | None = None
    """The integration's own key for the entity (uptime, last_boot ...).

    Integrations keep it stable across releases, and users can't rename it.
    """
    unique_id: str | None = None
    """The integration's own id for it, which users can't change either. It can hold a serial
    number or a MAC address, so it is only matched against, never reported."""
    available: bool = True
    """False while it is unavailable. A container or VM that was removed leaves its device and
    entities behind in HA, all unavailable."""


@dataclass(frozen=True, slots=True)
class Device:
    """One device: a host, a VM, a container, a media server ..."""

    device_id: str
    integrations: frozenset[str]
    """Domains of the config entries behind the device."""
    via_device_id: str | None = None
    """The device it hangs off, such as the Proxmox node a VM runs on."""


@dataclass(frozen=True, slots=True)
class Statistic:
    """Long-term statistics HA keeps for one statistic id."""

    statistic_id: str
    unit: str | None = None
    first: date | None = None
    """First day with data, if it was looked up."""


@dataclass(frozen=True, slots=True)
class EnergyPrefs:
    """What the user set up in the Energy dashboard."""

    grid_import: tuple[str, ...] = ()
    """Statistic ids of energy taken from the grid."""
    price_entities: tuple[str, ...] = ()
    """Entities holding the current price per kWh."""
    fixed_price: float | None = None
    """The fixed price per kWh entered instead, if any."""


@dataclass(frozen=True, slots=True)
class Inventory:
    """Everything the coverage check and the cards start from."""

    entities: tuple[Entity, ...] = ()
    devices: tuple[Device, ...] = ()
    statistics: Mapping[str, Statistic] = field(default_factory=dict)
    """Long-term statistics by statistic id (the entity id for entity statistics)."""
    energy: EnergyPrefs = field(default_factory=EnergyPrefs)
    lab_meters: tuple[str, ...] = ()
    """Energy meters the user picked as measuring the lab (the Power card)."""
    integration_names: Mapping[str, str] = field(default_factory=dict)
    """Integration -> its name ("shelly" -> "Shelly"), for the lab meters' integrations:
    they have no adapter to name them."""
    backfilled: Mapping[str, date] = field(default_factory=dict)
    """Entity id -> the first day the recorder still had when Wrapped started counting it."""
