"""Adapters find data by what it is, never by name."""

from __future__ import annotations

from custom_components.homelab_wrapped.core.model import Device, EnergyPrefs, Entity, Inventory
from custom_components.homelab_wrapped.core.sources import (
    ADAPTERS,
    ENERGY_DASHBOARD,
    Adapter,
    EntityRule,
    Signal,
    find_signals,
    unlocked_by,
)


def signals_of(*entities: Entity, devices: tuple[Device, ...] = ()) -> dict[Signal, list[str]]:
    found = find_signals(Inventory(entities=entities, devices=devices))
    return {
        signal: sorted(f"{item.source}:{item.entity_id or item.device_id}" for item in items)
        for signal, items in found.items()
    }


def test_proxmox_nodes_are_hosts_and_their_guests_are_guests() -> None:
    """Storages hang off the node too, but they are no guests: told apart by their entities."""
    devices = (
        Device("node", frozenset({"proxmoxve"})),
        Device("vm", frozenset({"proxmoxve"}), via_device_id="node"),
        Device("lxc", frozenset({"proxmoxve"}), via_device_id="node"),
        Device("storage", frozenset({"proxmoxve"}), via_device_id="node"),
        Device("lamp", frozenset({"hue"})),
    )
    entities = (
        Entity("sensor.a", "sensor", "proxmoxve", "node", translation_key="node_status"),
        Entity("sensor.b", "sensor", "proxmoxve", "vm", translation_key="vm_status"),
        Entity("sensor.c", "sensor", "proxmoxve", "lxc", translation_key="container_status"),
        Entity("sensor.d", "sensor", "proxmoxve", "storage", translation_key="storage_used"),
    )
    assert signals_of(*entities, devices=devices) == {
        Signal.HOST: ["Proxmox VE:node"],
        Signal.GUEST: ["Proxmox VE:lxc", "Proxmox VE:vm"],
    }


def test_uptime_only_from_integrations_that_report_the_lab() -> None:
    """HA 2026.10's "uptime" device class: when the device last restarted. Lamps, plugs
    and lawn mowers report one too; only servers and network gear count."""
    proxmox = Entity(
        "sensor.a", "sensor", "proxmoxve", device_class="uptime", translation_key="vm_uptime"
    )
    monitor = Entity("sensor.b", "sensor", "systemmonitor", device_class="uptime")
    nas = Entity("sensor.c", "sensor", "synology_dsm", device_class="uptime")
    switch = Entity("sensor.d", "sensor", "mikrotik", device_class="uptime")
    lamp = Entity("sensor.e", "sensor", "wled", device_class="uptime")
    plug = Entity("sensor.f", "sensor", "shelly", device_class="uptime")
    mower = Entity(
        "sensor.g",
        "sensor",
        "husqvarna_automower",
        device_class="timestamp",
        translation_key="uptime",
    )
    assert signals_of(proxmox, monitor, nas, switch, lamp, plug, mower) == {
        Signal.UPTIME: ["Proxmox VE:sensor.a", "Synology DSM:sensor.c", "System Monitor:sensor.b"],
        Signal.NETWORK_UPTIME: ["MikroTik:sensor.d"],
    }


def test_more_network_gear_and_pi_hole_v6() -> None:
    """Checked in HA 2026.11's code; UPnP's "uptime" is the internet connection's."""
    starlink = Entity(
        "sensor.a", "sensor", "starlink", device_class="timestamp", translation_key="last_restart"
    )
    switch = Entity(
        "sensor.b",
        "sensor",
        "qnap_qsw",
        device_class="timestamp",
        translation_key="uptime_timestamp",
    )
    airmax = Entity(
        "sensor.c",
        "sensor",
        "airos",
        device_class="duration",
        unit="d",
        translation_key="host_uptime",
    )
    upnp = Entity(
        "sensor.d", "sensor", "upnp", device_class="duration", unit="s", translation_key="uptime"
    )
    asus = Entity(
        "sensor.e", "sensor", "asusrouter", device_class="duration", unit="h", state_class="total"
    )
    pihole = Entity("sensor.f", "sensor", "pi_hole", translation_key="ads_blocked")
    assert signals_of(starlink, switch, airmax, upnp, asus, pihole) == {
        Signal.NETWORK_UPTIME: [
            "ASUS Router:sensor.e",
            "QNAP QSW:sensor.b",
            "Starlink:sensor.a",
            "Ubiquiti airOS:sensor.c",
        ],
        Signal.DNS_BLOCKED: ["Pi-hole:sensor.f"],
    }


def test_proxmox_nodes_and_guests_by_any_of_their_sensors() -> None:
    """HA 2026.11 dropped the uptime sensors' keys, and node_status needs VM.Audit."""
    node = Device("node", frozenset({"proxmoxve"}))
    guest = Device("vm", frozenset({"proxmoxve"}), via_device_id="node")
    cpu = Entity("sensor.a", "sensor", "proxmoxve", device_id="node", translation_key="node_cpu")
    memory = Entity("sensor.b", "sensor", "proxmoxve", device_id="vm", translation_key="vm_memory")
    uptime = Entity("sensor.c", "sensor", "proxmoxve", device_id="vm", device_class="uptime")
    found = find_signals(Inventory(entities=(cpu, memory, uptime), devices=(node, guest)))
    assert [item.device_id for item in found[Signal.HOST]] == ["node"]
    assert [item.device_id for item in found[Signal.GUEST]] == ["vm"]
    assert [item.entity_id for item in found[Signal.UPTIME]] == ["sensor.c"]


def test_unifi_and_fritz_count_their_devices_not_clients_or_connections() -> None:
    """Both have a second uptime sensor: how long a client (a phone) has been connected,
    how long the internet connection has been up. Their unique ids tell them apart."""
    access_point = Entity(
        "sensor.a", "sensor", "unifi", device_class="uptime", unique_id="device_uptime-aa:bb"
    )
    phone = Entity("sensor.b", "sensor", "unifi", device_class="uptime", unique_id="uptime-cc:dd")
    box = Entity(
        "sensor.c", "sensor", "fritz", device_class="uptime", unique_id="1234-device_uptime"
    )
    internet = Entity(
        "sensor.d",
        "sensor",
        "fritz",
        device_class="uptime",
        translation_key="connection_uptime",
        unique_id="1234-connection_uptime",
    )
    assert signals_of(access_point, phone, box, internet) == {
        Signal.NETWORK_UPTIME: ["FRITZ!Box:sensor.c", "UniFi Network:sensor.a"]
    }


def test_asus_router_uptime_without_translation_keys() -> None:
    uptime = Entity(
        "sensor.a", "sensor", "asusrouter", device_class="duration", unit="s", state_class="total"
    )
    traffic = Entity(
        "sensor.b",
        "sensor",
        "asusrouter",
        device_class="data_size",
        unit="GB",
        state_class="total_increasing",
    )
    elsewhere = Entity(
        "sensor.c",
        "sensor",
        "nut",
        device_class="duration",
        unit="s",
        translation_key="battery_runtime",
    )
    assert signals_of(uptime, traffic, elsewhere) == {
        Signal.NETWORK_UPTIME: ["ASUS Router:sensor.a"]
    }


def test_opnsense_boot_time_without_translation_keys() -> None:
    """The firewall's boot time is hass-opnsense's only timestamp sensor (v1.3.3)."""
    boot = Entity(
        "sensor.a",
        "sensor",
        "opnsense",
        device_class="timestamp",
        unique_id="02_42_ac_11_00_07_telemetry_system_boottime",
    )
    expiry = Entity(
        "sensor.x", "sensor", "opnsense", device_class="timestamp", unique_id="cert_expiry"
    )
    traffic = Entity(
        "sensor.b",
        "sensor",
        "opnsense",
        device_class="data_rate",
        unit="kB/s",
        state_class="measurement",
    )
    leases = Entity("sensor.c", "sensor", "opnsense", unit="leases")
    firmware = Entity("update.d", "update", "opnsense", device_class="firmware")
    assert signals_of(boot, expiry, traffic, leases, firmware) == {
        Signal.NETWORK_UPTIME: ["OPNsense:sensor.a"]
    }


def test_matched_by_translation_key_not_entity_id() -> None:
    renamed = Entity(
        "sensor.my_renamed_thing", "sensor", "adguard", translation_key="dns_queries_blocked"
    )
    misleading = Entity("sensor.adguard_dns_queries_blocked", "sensor", "adguard")
    elsewhere = Entity("sensor.x", "sensor", "template", translation_key="dns_queries_blocked")
    assert signals_of(renamed, misleading, elsewhere) == {
        Signal.DNS_BLOCKED: ["AdGuard Home:sensor.my_renamed_thing"]
    }


def test_uptime_as_timestamp_or_counter() -> None:
    boot = Entity(
        "sensor.a", "sensor", "systemmonitor", device_class="timestamp", translation_key="last_boot"
    )
    counter = Entity(
        "sensor.b", "sensor", "asuswrt", device_class="duration", unit="s", translation_key="uptime"
    )
    backup = Entity(
        "sensor.c", "sensor", "proxmoxve", device_class="timestamp", translation_key="last_backup"
    )
    percent = Entity("sensor.d", "sensor", "kuma", unit="%", translation_key="uptime")
    assert signals_of(boot, counter, backup, percent) == {
        Signal.UPTIME: ["System Monitor:sensor.a"],
        Signal.NETWORK_UPTIME: ["ASUSWRT:sensor.b"],
    }


def test_energy_needs_long_term_statistics_and_price_needs_per_kwh() -> None:
    meter = Entity(
        "sensor.m",
        "sensor",
        "shelly",
        device_class="energy",
        unit="kWh",
        state_class="total_increasing",
    )
    no_history = Entity("sensor.n", "sensor", "shelly", device_class="energy", unit="kWh")
    price = Entity("sensor.p", "sensor", "nordpool", unit="DKK/kWh")
    power = Entity("sensor.w", "sensor", "shelly", device_class="power", unit="W")
    assert signals_of(meter, no_history, price, power) == {
        Signal.ENERGY: ["other integrations:sensor.m"],
        Signal.PRICE: ["other integrations:sensor.p"],
    }


def test_energy_dashboard_settings() -> None:
    inventory = Inventory(
        energy=EnergyPrefs(
            grid_import=("sensor.grid",), price_entities=("sensor.price",), fixed_price=2.1
        )
    )
    found = find_signals(inventory)
    assert [(i.source, i.entity_id) for i in found[Signal.ENERGY]] == [
        (ENERGY_DASHBOARD, "sensor.grid")
    ]
    assert [(i.source, i.entity_id) for i in found[Signal.PRICE]] == [
        (ENERGY_DASHBOARD, "sensor.price"),
        (ENERGY_DASHBOARD, None),
    ]


def test_first_matching_adapter_gets_the_credit() -> None:
    rule = EntityRule(Signal.MEDIA, "media_player")
    adapters = (
        Adapter("jellyfin", "Jellyfin", frozenset({"jellyfin"}), entity_rules=(rule,)),
        Adapter("generic", "other integrations", frozenset(), entity_rules=(rule,)),
    )
    player = Entity("media_player.tv", "media_player", "jellyfin")
    found = find_signals(Inventory(entities=(player,)), adapters)
    assert [item.source for item in found[Signal.MEDIA]] == ["Jellyfin"]


def test_unlock_hints() -> None:
    assert unlocked_by({Signal.DNS_BLOCKED}) == ("AdGuard Home", "Pi-hole")
    assert unlocked_by({Signal.ENERGY}) == ()  # power is unlocked in the options


def test_adapters_are_unique_and_generic_comes_last() -> None:
    keys = [adapter.key for adapter in ADAPTERS]
    assert len(keys) == len(set(keys))
    assert [adapter.generic for adapter in ADAPTERS].index(True) == len(ADAPTERS) - 1
    assert all(adapter.signals for adapter in ADAPTERS)


def test_domains_no_adapter_reads_are_skipped() -> None:
    light = Entity("light.lab", "light", "hue", translation_key="uptime")
    assert signals_of(light) == {}


def test_portainer_containers_not_its_stacks_or_volumes() -> None:
    """Stacks and volumes hang off the endpoint like containers; only containers count."""
    devices = (
        Device("endpoint", frozenset({"portainer"})),
        Device("stack", frozenset({"portainer"}), via_device_id="endpoint"),
        Device("web", frozenset({"portainer"}), via_device_id="stack"),
        Device("db", frozenset({"portainer"}), via_device_id="endpoint"),
        Device("volume", frozenset({"portainer"}), via_device_id="endpoint"),
    )
    entities = (
        Entity("sensor.a", "sensor", "portainer", "web", translation_key="container_state"),
        Entity(
            "sensor.b",
            "sensor",
            "portainer",
            "web",
            device_class="timestamp",
            translation_key="container_started_at",
        ),
        Entity(
            "sensor.c",
            "sensor",
            "portainer",
            "web",
            device_class="timestamp",
            translation_key="image_created",
        ),
        Entity(
            "sensor.d",
            "sensor",
            "portainer",
            "db",
            state_class="total_increasing",
            translation_key="container_restart_count",
        ),
        Entity("sensor.e", "sensor", "portainer", "stack", translation_key="stack_type"),
        Entity("sensor.f", "sensor", "portainer", "volume", translation_key="volume_size"),
    )
    assert signals_of(*entities, devices=devices) == {
        Signal.CONTAINER: ["Portainer:db", "Portainer:web"],
        Signal.CONTAINER_UPTIME: ["Portainer:sensor.b"],
    }


def test_a_removed_container_isnt_counted() -> None:
    """HA keeps a removed container's device and entities, all unavailable."""
    devices = (
        Device("endpoint", frozenset({"portainer"})),
        Device("web", frozenset({"portainer"}), via_device_id="endpoint"),
        Device("stopped", frozenset({"portainer"}), via_device_id="endpoint"),
        Device("gone", frozenset({"portainer"}), via_device_id="endpoint"),
    )
    entities = (
        Entity("sensor.a", "sensor", "portainer", "web", translation_key="container_state"),
        Entity("sensor.b", "sensor", "portainer", "stopped", translation_key="container_state"),
        Entity(
            "sensor.c",
            "sensor",
            "portainer",
            "gone",
            translation_key="container_state",
            available=False,
        ),
    )
    assert signals_of(*entities, devices=devices) == {
        Signal.CONTAINER: ["Portainer:stopped", "Portainer:web"]
    }


def test_ups_status_from_nut_and_apcupsd() -> None:
    """NUT's raw ups.status, not its display text; APC UPS Daemon's status."""
    nut = Entity("sensor.a", "sensor", "nut", translation_key="ups_status")
    display = Entity("sensor.b", "sensor", "nut", translation_key="ups_status_display")
    apc = Entity("sensor.c", "sensor", "apcupsd", translation_key="status")
    assert signals_of(nut, display, apc) == {
        Signal.UPS: ["APC UPS Daemon:sensor.c", "Network UPS Tools:sensor.a"]
    }
