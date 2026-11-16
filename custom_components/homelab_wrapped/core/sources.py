"""Source adapters: which integrations give which kinds of data.

An adapter never looks at entity or device names. It matches on what something
is: the integration that made it, the entity's domain, device_class, unit and
the integration's own translation_key, which integrations keep stable across
releases and users can't rename.

To support another integration, add one ``Adapter`` to ``ADAPTERS`` with a test
built from that integration's part of the "copy diagnostics" report.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from .model import Device, Entity, Inventory


class Signal(StrEnum):
    """A kind of data the cards are built from."""

    HOST = "host"
    """A machine: a Proxmox node, a Glances or System Monitor host."""
    GUEST = "guest"
    """A VM or LXC container."""
    CONTAINER = "container"
    """A Docker container."""
    UPTIME = "uptime"
    """An uptime counter or a last-boot timestamp."""
    CONTAINER_UPTIME = "container_uptime"
    """When a Docker container last started."""
    NETWORK_UPTIME = "network_uptime"
    """A router's, firewall's, access point's or switch's uptime or boot time: network
    gear, counted apart from the servers."""
    DNS_BLOCKED = "dns_blocked"
    """Blocked DNS queries."""
    MEDIA = "media"
    """A media server's players or sessions."""
    ENERGY = "energy"
    """An energy meter in kWh."""
    PRICE = "price"
    """An electricity price per kWh."""
    UPS = "ups"
    """A UPS's status: on mains or on battery (NUT, APC UPS Daemon)."""
    SERVICE = "service"
    """A monitored service's uptime over the last 365 days, in percent (Uptime Kuma)."""


TIME_UNITS = frozenset({"s", "min", "h", "d"})
UPTIME_KEYS = frozenset(
    {
        "uptime",
        "last_boot",
        "boot_time",
        "sensor_uptime",
        "sensor_last_boot",
        "node_uptime",  # Proxmox VE until HA 2026.10; 2026.11 dropped these keys
        "vm_uptime",
        "container_uptime",
    }
)
_PROXMOX_PARTS = ("status", "cpu", "max_cpu", "memory", "max_memory", "memory_percentage", "disk")
PROXMOX_NODE_KEYS = frozenset({"node_uptime", *(f"node_{part}" for part in _PROXMOX_PARTS)})
"""Any of a node's own sensors: a token may not see them all (node_status needs VM.Audit)."""
PROXMOX_GUEST_KEYS = frozenset(
    {
        "vm_uptime",
        "container_uptime",
        *(f"{guest}_{part}" for guest in ("vm", "container") for part in _PROXMOX_PARTS),
    }
)
PORTAINER_CONTAINER_KEYS = frozenset(
    {"container_state", "container_started_at", "container_restart_count"}
)
"""Stacks and volumes hang off a Portainer endpoint too; only containers have these."""
ENERGY_DASHBOARD = "Energy dashboard"
ENERGY_DASHBOARD_KEY = "energy_dashboard"


@dataclass(frozen=True, slots=True)
class EntityRule:
    """Entities that give ``signal``. A criterion left as None accepts anything."""

    signal: Signal
    domain: str
    device_classes: frozenset[str] | None = None
    translation_keys: frozenset[str] | None = None
    units: frozenset[str] | None = None
    unit_suffix: str | None = None
    state_classes: frozenset[str] | None = None
    unique_id_prefix: str | None = None
    unique_id_suffix: str | None = None
    """For integrations without translation keys whose sensors differ only in their
    unique id ("device_uptime-…" against "uptime-…", a phone's connected time)."""

    def matches(self, entity: Entity) -> bool:
        """Whether the entity is what this rule looks for."""
        unique_id = entity.unique_id or ""
        return (
            entity.domain == self.domain
            and _accepts(self.device_classes, entity.device_class)
            and _accepts(self.translation_keys, entity.translation_key)
            and _accepts(self.units, entity.unit)
            and _accepts(self.state_classes, entity.state_class)
            and (
                self.unit_suffix is None
                or (entity.unit is not None and entity.unit.endswith(self.unit_suffix))
            )
            and (self.unique_id_prefix is None or unique_id.startswith(self.unique_id_prefix))
            and (self.unique_id_suffix is None or unique_id.endswith(self.unique_id_suffix))
        )


@dataclass(frozen=True, slots=True)
class DeviceRule:
    """Devices that give ``signal``: top-level devices, or devices hanging off another.

    ``entity_keys``, if set, also requires one of the device's entities to have one
    of these translation keys: what the device is, when hanging off another isn't
    enough (Proxmox storages hang off the node just like its VMs). That entity must
    be available: HA keeps the devices of removed containers and VMs, with every
    entity unavailable.
    """

    signal: Signal
    via_device: bool
    entity_keys: frozenset[str] | None = None

    def matches(self, device: Device, keys: frozenset[str] = frozenset()) -> bool:
        """Whether the device, whose entities have ``keys``, is what this rule looks for."""
        return (device.via_device_id is not None) == self.via_device and (
            self.entity_keys is None or bool(self.entity_keys & keys)
        )


@dataclass(frozen=True, slots=True)
class Adapter:
    """What one integration can tell us."""

    key: str
    name: str
    """Shown in "connect X" hints."""
    integrations: frozenset[str]
    """Integration domains it reads. Empty: entities from any integration."""
    entity_rules: tuple[EntityRule, ...] = ()
    device_rules: tuple[DeviceRule, ...] = ()

    @property
    def signals(self) -> frozenset[Signal]:
        """Every signal this adapter can give."""
        return frozenset(rule.signal for rule in self.entity_rules) | frozenset(
            rule.signal for rule in self.device_rules
        )

    @property
    def generic(self) -> bool:
        """Matches entities from any integration rather than naming its own."""
        return not self.integrations


@dataclass(frozen=True, slots=True)
class Found:
    """One entity, device or Energy dashboard setting that gives a signal."""

    signal: Signal
    source: str
    """The adapter's name, or "Energy dashboard"."""
    entity_id: str | None = None
    """Entity or statistic id, if the signal comes from one."""
    device_id: str | None = None
    adapter: str = ""
    """The adapter's key, stable across renames of its display name."""


_UPTIME_RULES = (
    # HA's own "uptime" device class: when the device last restarted.
    EntityRule(Signal.UPTIME, "sensor", device_classes=frozenset({"uptime"})),
    EntityRule(
        Signal.UPTIME,
        "sensor",
        device_classes=frozenset({"timestamp"}),
        translation_keys=UPTIME_KEYS,
    ),
    EntityRule(Signal.UPTIME, "sensor", translation_keys=UPTIME_KEYS, units=TIME_UNITS),
)

ADAPTERS: tuple[Adapter, ...] = (
    Adapter(
        "proxmoxve",
        "Proxmox VE",
        frozenset({"proxmoxve"}),
        entity_rules=_UPTIME_RULES,
        device_rules=(
            DeviceRule(Signal.HOST, via_device=False, entity_keys=PROXMOX_NODE_KEYS),
            DeviceRule(Signal.GUEST, via_device=True, entity_keys=PROXMOX_GUEST_KEYS),
        ),
    ),
    Adapter(
        "asusrouter",
        "ASUS Router",
        frozenset({"asusrouter"}),
        # No translation keys; its only duration sensors in seconds that keep a total
        # are the routers' uptime. Routers and access points are network gear.
        entity_rules=(
            EntityRule(
                Signal.NETWORK_UPTIME,
                "sensor",
                device_classes=frozenset({"duration"}),
                units=TIME_UNITS,  # seconds, unless the user shows it in hours or days
                state_classes=frozenset({"total"}),
            ),
        ),
    ),
    Adapter(
        "opnsense",
        "OPNsense",
        frozenset({"opnsense"}),
        # The custom hass-opnsense integration has no translation keys either; its only
        # timestamp sensor is the firewall's boot time ("telemetry.system.boottime").
        entity_rules=(
            EntityRule(
                Signal.NETWORK_UPTIME,
                "sensor",
                device_classes=frozenset({"timestamp"}),
                # Its unique id ends in the description's key, so a timestamp sensor it adds
                # later (a certificate's expiry) isn't taken for the boot time.
                unique_id_suffix="telemetry_system_boottime",
            ),
        ),
    ),
    # HA's own network integrations whose devices say when they restarted. Checked in
    # HA 2026.11's code: UniFi's other uptime sensor is how long a client (a phone) has
    # been connected, FRITZ!Box's is how long its internet connection has been up.
    Adapter(
        "unifi",
        "UniFi Network",
        frozenset({"unifi"}),
        entity_rules=(
            EntityRule(
                Signal.NETWORK_UPTIME,
                "sensor",
                device_classes=frozenset({"uptime"}),
                unique_id_prefix="device_uptime-",
            ),
        ),
    ),
    Adapter(
        "fritz",
        "FRITZ!Box",
        frozenset({"fritz"}),
        entity_rules=(
            EntityRule(
                Signal.NETWORK_UPTIME,
                "sensor",
                device_classes=frozenset({"uptime"}),
                unique_id_suffix="-device_uptime",
            ),
        ),
    ),
    *(
        Adapter(
            key,
            name,
            frozenset({key}),
            entity_rules=(
                EntityRule(Signal.NETWORK_UPTIME, "sensor", device_classes=frozenset({"uptime"})),
            ),
        )
        for key, name in (
            ("mikrotik", "MikroTik"),
            ("vodafone_station", "Vodafone Station"),
            ("devolo_home_network", "devolo Home Network"),
        )
    ),
    *(
        Adapter(
            key,
            name,
            frozenset({key}),
            entity_rules=(EntityRule(Signal.NETWORK_UPTIME, "sensor", translation_keys=keys),),
        )
        for key, name, keys in (
            ("asuswrt", "ASUSWRT", frozenset({"last_boot", "uptime"})),  # HTTP(S) only
            ("huawei_lte", "Huawei LTE", frozenset({"uptime"})),
            ("starlink", "Starlink", frozenset({"last_restart"})),
            ("qnap_qsw", "QNAP QSW", frozenset({"uptime_timestamp"})),
            ("airos", "Ubiquiti airOS", frozenset({"host_uptime"})),
            # Not UPnP/IGD: its "uptime" is the internet connection's (NewUptime), so a
            # reconnect would count as a restart of the router.
        )
    ),
    # NAS: their only uptime sensor (both disabled until the user turns it on).
    Adapter(
        "synology_dsm",
        "Synology DSM",
        frozenset({"synology_dsm"}),
        entity_rules=(EntityRule(Signal.UPTIME, "sensor", device_classes=frozenset({"uptime"})),),
    ),
    Adapter(
        "qnap",
        "QNAP",
        frozenset({"qnap"}),
        entity_rules=(EntityRule(Signal.UPTIME, "sensor", translation_keys=frozenset({"uptime"})),),
    ),
    Adapter(
        "glances",
        "Glances",
        frozenset({"glances"}),
        entity_rules=_UPTIME_RULES,
        device_rules=(DeviceRule(Signal.HOST, via_device=False),),
    ),
    Adapter(
        "systemmonitor",
        "System Monitor",
        frozenset({"systemmonitor"}),
        entity_rules=_UPTIME_RULES,
        device_rules=(DeviceRule(Signal.HOST, via_device=False),),
    ),
    Adapter(
        "portainer",
        "Portainer",
        frozenset({"portainer"}),
        # When the container last started. Its "restart count" only counts what Docker's
        # restart policy brought back (and resets when the container is started by hand),
        # so it misses redeploys, updates and reboots.
        entity_rules=(
            EntityRule(
                Signal.CONTAINER_UPTIME,
                "sensor",
                device_classes=frozenset({"timestamp"}),
                translation_keys=frozenset({"container_started_at"}),
            ),
        ),
        device_rules=(
            DeviceRule(Signal.CONTAINER, via_device=True, entity_keys=PORTAINER_CONTAINER_KEYS),
        ),
    ),
    Adapter(
        "adguard",
        "AdGuard Home",
        frozenset({"adguard"}),
        entity_rules=(
            EntityRule(
                Signal.DNS_BLOCKED, "sensor", translation_keys=frozenset({"dns_queries_blocked"})
            ),
        ),
    ),
    Adapter(
        "pi_hole",
        "Pi-hole",
        frozenset({"pi_hole"}),
        entity_rules=(
            EntityRule(
                Signal.DNS_BLOCKED,
                "sensor",
                # Pi-hole v5's key, and v6's (the same rolling 24-hour count).
                translation_keys=frozenset({"ads_blocked_today", "ads_blocked"}),
            ),
        ),
    ),
    Adapter(
        "jellyfin",
        "Jellyfin",
        frozenset({"jellyfin"}),
        entity_rules=(EntityRule(Signal.MEDIA, "media_player"),),
    ),
    Adapter(
        "plex",
        "Plex",
        frozenset({"plex"}),
        entity_rules=(EntityRule(Signal.MEDIA, "media_player"),),
    ),
    Adapter(
        "nut",
        "Network UPS Tools",
        frozenset({"nut"}),
        # The raw ups.status, such as "OL" or "OB DISCHRG"; not the display text.
        entity_rules=(
            EntityRule(Signal.UPS, "sensor", translation_keys=frozenset({"ups_status"})),
        ),
    ),
    Adapter(
        "apcupsd",
        "APC UPS Daemon",
        frozenset({"apcupsd"}),
        entity_rules=(EntityRule(Signal.UPS, "sensor", translation_keys=frozenset({"status"})),),
    ),
    Adapter(
        "uptime_kuma",
        "Uptime Kuma",
        frozenset({"uptime_kuma"}),
        # Uptime Kuma keeps each monitor's history itself; HA keeps the 365-day ratio's
        # statistics, so its value at the end of a year is that year's uptime.
        entity_rules=(
            EntityRule(
                Signal.SERVICE,
                "sensor",
                translation_keys=frozenset({"uptime_365d"}),
                units=frozenset({"%"}),
            ),
        ),
    ),
    # Last, so a named adapter gets the credit for an entity both match: the lab meters
    # and prices, from any integration. Never uptime: lights, plugs, printers and phones
    # report one too (WLED, Shelly, ESPHome, Matter ...), and they aren't the lab.
    Adapter(
        "generic",
        "other integrations",
        frozenset(),
        entity_rules=(
            EntityRule(
                Signal.ENERGY,
                "sensor",
                device_classes=frozenset({"energy"}),
                state_classes=frozenset({"total", "total_increasing"}),
            ),
            EntityRule(Signal.PRICE, "sensor", unit_suffix="/kWh"),
        ),
    ),
)


def find_signals(
    inventory: Inventory, adapters: Iterable[Adapter] = ADAPTERS
) -> dict[Signal, list[Found]]:
    """Everything in the inventory that gives a signal, by signal.

    An entity or device counts once per signal: for the first adapter that
    matches it, in the order of ``adapters``.
    """
    adapters = tuple(adapters)
    found: dict[tuple[Signal, str], Found] = {}
    domains = {rule.domain for adapter in adapters for rule in adapter.entity_rules}
    # The adapters that can match an integration's entities, in order; worked out once
    # per integration rather than once per entity.
    per_platform: dict[str, tuple[Adapter, ...]] = {}

    for entity in inventory.entities:
        if entity.domain not in domains:
            continue
        candidates = per_platform.get(entity.platform)
        if candidates is None:
            candidates = per_platform[entity.platform] = tuple(
                adapter
                for adapter in adapters
                if adapter.generic or entity.platform in adapter.integrations
            )
        for adapter in candidates:
            for rule in adapter.entity_rules:
                if rule.matches(entity):
                    found.setdefault(
                        (rule.signal, entity.entity_id),
                        Found(
                            rule.signal,
                            adapter.name,
                            entity.entity_id,
                            entity.device_id,
                            adapter.key,
                        ),
                    )

    keys_by_device: dict[str, set[str]] = {}
    for entity in inventory.entities:
        if entity.device_id and entity.translation_key and entity.available:
            keys_by_device.setdefault(entity.device_id, set()).add(entity.translation_key)
    for device in inventory.devices:
        keys = frozenset(keys_by_device.get(device.device_id, ()))
        for adapter in adapters:
            if adapter.generic or not device.integrations & adapter.integrations:
                continue
            for device_rule in adapter.device_rules:
                if device_rule.matches(device, keys):
                    found.setdefault(
                        (device_rule.signal, f"device:{device.device_id}"),
                        Found(
                            device_rule.signal,
                            adapter.name,
                            device_id=device.device_id,
                            adapter=adapter.key,
                        ),
                    )

    energy = inventory.energy
    for statistic_id in energy.grid_import:
        found[(Signal.ENERGY, statistic_id)] = Found(
            Signal.ENERGY, ENERGY_DASHBOARD, statistic_id, adapter=ENERGY_DASHBOARD_KEY
        )
    for entity_id in energy.price_entities:
        found[(Signal.PRICE, entity_id)] = Found(
            Signal.PRICE, ENERGY_DASHBOARD, entity_id, adapter=ENERGY_DASHBOARD_KEY
        )
    if energy.fixed_price is not None:
        found[(Signal.PRICE, "fixed")] = Found(
            Signal.PRICE, ENERGY_DASHBOARD, adapter=ENERGY_DASHBOARD_KEY
        )

    by_signal: dict[Signal, list[Found]] = {}
    for item in found.values():
        by_signal.setdefault(item.signal, []).append(item)
    return by_signal


def unlocked_by(
    signals: Iterable[Signal], adapters: Iterable[Adapter] = ADAPTERS
) -> tuple[str, ...]:
    """Names of the integrations that would give any of ``signals``."""
    wanted = set(signals)
    return tuple(a.name for a in adapters if not a.generic and a.signals & wanted)


def _accepts(allowed: frozenset[str] | None, value: str | None) -> bool:
    return allowed is None or value in allowed


def count_found(found: Mapping[Signal, list[Found]]) -> dict[str, int]:
    """How many of each signal, for the coverage screen and diagnostics."""
    return {signal.value: len(items) for signal, items in sorted(found.items())}
