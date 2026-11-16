# Changelog

All notable changes to Homelab Wrapped. The version is the one in
`custom_components/homelab_wrapped/manifest.json`.

## [0.1.0] - 2026-11-16

The first version.

### The panel

- **Coverage check**, the first screen: which of the eight cards your lab can make today, how far
  back each one's data goes, when a counting card will be ready, and what would unlock a locked
  one. **Copy diagnostics** (and the integration's diagnostics download) describes the lab
  without entity ids, unique ids, names, titles, hostnames or IPs.
- **The story**, full screen: click or tap (the left third goes back) or press → or Space for the
  next card, ← to go back, Esc to close.
  - *Your lab*: hosts, guests and containers.
  - *Uptime*: the longest streak without a restart (exact when an uptime sensor knows the boot
    time, even from before Wrapped was installed), what's up right now, the year day by day, and
    how much of the past 365 days the services Uptime Kuma watches were up.
  - *Restarts*: what restarted most, the busiest day, the favourite hour, what never restarted;
    Docker containers and network gear (routers, access points, switches, the firewall) ranked
    apart.
  - *Blocked*: DNS queries blocked, per day and on the busiest day.
  - *Media*: hours played, by month, per media server, and the most played series, artists and
    films.
  - *Power*: kWh used by the meters you pick as the lab's, priced hour by hour with the Energy
    dashboard's price sensor or its fixed price, the average draw, and the power cuts the UPS
    rode out.
  - *Personality*: the Rock, the Tinkerer, the Night Owl, the Weekend Warrior, the Gatekeeper,
    the Cinephile, the Sipper, the Survivor, the Power Plant, the Collector or the All-Rounder,
    picked from the other cards, with the strongest reasons.
  - A closing summary with a **share image**: one portrait 1080×1920 picture of the year, drawn
    in the browser. Machine names are left out unless *Show machine names* is ticked; titles
    never are on it. *Save image* shares it where the browser can, and downloads it otherwise.
- **Choose the year:** in January the panel plays the year that just ended; once there is more
  than one year with data, it offers the others.
- English and Danish, following Home Assistant's language.

### Where the data comes from

- Found by what things are (integration, device class, unit, translation key), never by names.
- **Servers and NAS:** Proxmox VE (nodes, VMs, LXC containers), Glances, System Monitor,
  Synology DSM, QNAP. **Docker containers:** Portainer. **Network gear:** ASUS Router (custom),
  ASUSWRT, OPNsense (custom hass-opnsense), UniFi Network, FRITZ!Box, MikroTik, Vodafone Station,
  devolo Home Network, Huawei LTE, Starlink, QNAP QSW, Ubiquiti airOS. **DNS blocking:** AdGuard
  Home, Pi-hole (v5 and v6). **Media:** Jellyfin, Plex. **UPS:** Network UPS Tools, APC UPS
  Daemon. **Services:** Uptime Kuma. **Power:** any energy meter you pick, and the Energy
  dashboard's price.
- Smart-home devices never count as machines, even when they report an uptime. UniFi's client
  uptime, FRITZ!Box's connection uptime and UPnP's (the internet connection's) aren't restarts.
- **Leave out** in the options: devices Wrapped ignores, such as a second integration watching the
  same machine.

### Recording what Home Assistant forgets

- From the day Wrapped is installed, its own sensors count what the recorder forgets (10 days by
  default), as totals that only go up, so Home Assistant keeps their history forever:
  - *restarts* per server, container and piece of network gear: a counter that drops, or a boot
    time that moves forward (a Docker container crash-looping once a minute counts too); restarts
    while Home Assistant was down count when it's back. A VM that stops counts once and isn't
    "up" while stopped;
  - *blocked DNS queries* per AdGuard Home or Pi-hole: their rolling 24-hour count, read daily at
    23:55;
  - *playback* in hours per media server, over all its players (new Jellyfin sessions are
    followed within seconds), with the hours per title kept in Wrapped's own storage;
  - *power cuts* per UPS: when it switched to battery and for how long.
- Each count is saved in Wrapped's own storage before a sensor shows it, with the source's name,
  so a retired server or a replaced DNS blocker stays in its year's cards.
- **Looking back:** when Wrapped starts counting something, it reads once what the recorder still
  has from before, a minute after Home Assistant has started, one source and one week at a time.
- Uptime counters' own long-term statistics count back as far as Home Assistant kept them,
  stitched across a sensor whose history stopped when an integration update changed its type.

[0.1.0]: https://github.com/emilhumm/HomelabWrapped/releases/tag/v0.1.0
