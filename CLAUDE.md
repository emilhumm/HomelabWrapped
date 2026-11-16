# Homelab Wrapped

Spotify-Wrapped-style story cards for a whole homelab: your longest uptime streak, what restarted most,
DNS blocks, media hours, power cost and a "homelab personality", ending in one shareable image.
Open source, meant for other homelabbers, not just this lab.

Names: display "Homelab Wrapped" · repo `emilhumm/HomelabWrapped` (public) · HA domain `homelab_wrapped`.

## Decisions (2026-11-11)

- **Version 1 is a Home Assistant custom integration in Python, installed through HACS** (built into HA as
  the Marketplace from 2026.11: *Add from link*; it needs a public repo with `hacs.json`). It works on
  every kind of HA install; add-ons only work on HA OS. A standalone Docker version for people without HA
  can come later and reuse the core.
- **Layout:**
  - `custom_components/homelab_wrapped/core/`: plain Python with no HA imports. Holds the source
    adapters, card logic and storage. It lives inside the integration because HACS only installs
    `custom_components/homelab_wrapped/`. Its modules import each other relatively, and
    `tests/core/test_purity.py` imports it with HA blocked, so a standalone version can lift it out as is.
  - `custom_components/homelab_wrapped/`: a thin HA layer plus the sidebar panel.
  - `frontend/`: TypeScript + Lit, built to one JS file in `custom_components/homelab_wrapped/frontend/`.
- **Reading data:**
  - Read HA's long-term statistics through the recorder API, not the database file, so it works on
    SQLite, MariaDB and Postgres.
  - Never block HA's event loop. Run heavy reads in the recorder's executor.
- **What HA keeps:** long-term statistics only exist for numeric sensors with a `state_class`. Events
  (restarts, updates, playback, DNS blocks) disappear after the recorder's retention period (default
  10 days). Wrapped records those itself from install, for example as its own `total_increasing`
  sensors, which HA then keeps forever.
- **Find data by what it is**, never by entity names: use the integration/platform, device_class, unit,
  and the Energy dashboard prefs (power + price sensors).
- **Adapters:** one small adapter per integration, checked against that integration's own code (servers:
  Proxmox VE, Glances, System Monitor, Synology DSM, QNAP; containers: Portainer; network gear: ASUS
  Router, ASUSWRT, OPNsense, UniFi, FRITZ!Box, MikroTik, Vodafone Station, devolo, Huawei LTE, Starlink,
  QNAP QSW, airOS; AdGuard, Pi-hole; Jellyfin, Plex; NUT, APC UPS Daemon; Uptime Kuma). Energy meters are
  whatever the user picks. The community adds more through PRs.
- **Cards:**
  - A card appears only when its data exists, and says how far back it goes ("since 13 May").
  - A missing card shows either "unlock" steps (connect X) or "counting" (needs time).
- **First screen is a coverage check:** "your lab can make these cards today". Its "copy diagnostics"
  button (names stripped) doubles as the support tool.
- **Trust and privacy:** read-only. Nothing leaves the network. The share image hides hostnames and IPs
  by default.
- **Screens:** wide (monitor / wall tablet) layout first, phone second. The share image stays portrait
  9:16.
- **Uptime Kuma** is a data source (it keeps per-service uptime history), not a competitor.

## Recording (how Wrapped counts what HA forgets)

- Own `total_increasing` sensors (`sensor.py`) on one "Homelab Wrapped" service device, hidden by
  default: restarts per uptime entity, blocked queries per DNS entity, playback hours per media server,
  power cuts per UPS. Unique ids use the source's entity-registry id, so renaming the source keeps the
  history.
- Counter state lives in `.storage/homelab_wrapped.tally` and is saved *before* the sensor shows a new
  count: a total that goes down after a crash would look like a meter reset to HA and be counted twice.
  Each record also keeps the source's `name` and, for restarts, its `machine` kind (server, container,
  network): history.py still shows a source that is gone or disabled (a retired server, a replaced DNS
  blocker) from Wrapped's own statistics. Records without a kind (kept before 2026-11-12, among them the
  old any-integration rule's phones and plugs) stay out, and so do left-out devices.
- Restarts: a counter that drops, or a boot time that moves forward by more than the reading's tolerance:
  45 s for a reported boot/start time (exact, or "now - uptime"; a container crash-looping once a minute
  must count, and 5 minutes counted none), 90 s for HA's uptime class (it holds drift up to 60 s), 5 min
  or the unit for counters (a drop catches those). Compared as boot times, so a counter that becomes a
  timestamp carries on, and restarts while HA was down are caught. A boot time in the future is ignored.
- Stopped guests: Proxmox VE reports a stopped VM's uptime as 0, so its boot time is about now. HA holds an
  uptime-class boot time until it moves 60 s: a running machine's is written once after a (re)boot and
  then never, a stopped guest's every minute or two. So "stopped" needs two fresh readings (under
  `FRESH_AGE`, 3 min) at most `FOLLOW_GAP` (5 min) apart whose boot times move with the clock
  (`CLOCK_SLACK`); one fresh reading is a reboot, and it counts. No reading for `FOLLOW_GAP` means running
  (the sensor's settle timer; the look-back sees the gap). The stop counts once (its boot time jumped),
  nothing while stopped (across HA restarts: touching stopped periods are joined) or when it starts.
  Stopped periods (`downs`, the latest 100) are saved, and `Machine.down` cuts every streak in any year;
  counters have no stopped state (a stopped guest's counter sits at 0, so HA writes nothing). The first
  version of this (one fresh reading = stopped) stuck after every reboot and lost later restarts:
  model HA's hold in tests (`tests/core/test_tally.py` `run_uptime_class`).
- A machine whose sources are all unavailable now (HA keeps a deleted VM's entities) or gone ends its
  last streak then (`Machine.down` with an open end): from the source's `last_changed`, or the last row of
  Wrapped's own sensor's statistics. Per source, the look-back's restarts and the sensor's increases are
  one record (they meet at the sensor's creation), not two sources for `merge_restarts` to match.
- Docker start times (Portainer) are exact: `EXACT_TOLERANCE` 10 s, passed as `exact` by the restarts
  sensor and the look-back's `Request` for containers.
- AdGuard and Pi-hole report rolling 24-hour counts: read once a day at 23:55 local, never summed as changes.
  AdGuard's count covers its statistics period, which must stay at 24 hours (README says so).
- Look-back (`backfill.py`, `core/backfill.py`): each sensor once, the recorder's states of its sources
  from `keep_days` (max 366) before the sensor's registry `created_at` up to it, read the same way the
  sensor counts. Kept in `.storage/homelab_wrapped.backfill` by unique id; history.py adds it to the
  cards, `Inventory.backfilled` to the coverage. Uptime counters with a `state_class` are skipped (their
  long-term statistics have it all). Restarts are dated when HA saw them, like every other source, so
  `merge_restarts` matches them.
- While HA is down the recorder keeps nothing, so the last state before an outage seems to carry on, and the
  recorder doesn't record when an unclean shutdown happened. The look-back bounds it: a 23:55 reading needs
  a state less than a day old, and one stretch of "playing" counts for at most 12 hours.
- Portainer containers: `container_started_at` (a timestamp) feeds a restarts sensor per container
  (`Signal.CONTAINER_UPTIME`). Its `container_restart_count` only counts restart-policy restarts and
  resets on a manual start: 0 for every container on the first real lab, though they restarted often.
- Media: HA's Jellyfin makes one media player per app or TV the first time it connects (an old one comes
  back from unavailable, still followed). A new media player in the entity registry starts a scan 2 s later
  (`NEW_PLAYER_DELAY`; players added together make one), so its first play counts: on the first real lab a
  TV's short play before the 15-minute rescan was lost. A player a scan finds already playing counts from
  its `last_changed` (at most 20 minutes back). Hours per title (series of an episode, else artist, else
  title; `core.tally.media_title`; a series name ending in the season playing, "Slow Horses S01" from an
  unmatched Jellyfin folder, loses it) are kept per year in the playback sensor's own storage, the longest 100: HA's statistics only keep the
  total. The look-back gives each stretch to the title playing when it began. Titles stay off the share
  image and out of diagnostics.

## Cards

01 Intro (hosts / guests / containers) · 02 Uptime (longest streak, year grid) · 03 Restarts ·
04 Blocked (DNS) · 05 Media · 06 Power (kWh priced with hourly spot prices) · 07 Personality ·
08 Summary + share image.

- Built: 01–07 and a summary slide. `core/cards.py` builds each card's dict from plain histories;
  `history.py` reads them from long-term statistics (one recorder job); websocket `homelab_wrapped/cards`
  (optional `year`). The panel's story view is `frontend/src/story.ts` + `slides.ts`.
  Clicks and taps are handled on the slide itself (left 30 % back); the back/next buttons are only for
  keyboards and screen readers (`pointer-events: none`), so a slide taller than a phone still scrolls.
- One machine per device: its uptime sources' restarts are merged one-to-one (a restart another source saw
  less than 2 hours away is the same one; every restart one source saw is kept), and the exact last boot
  replaces the hourly restart it matches. A streak is reported at full length even when it began last year.
- What counts (decided 2026-11-12): the lab is the gear that serves the house. `Machine.kind`:
  servers (hosts, VMs, NAS) are everywhere; Docker containers and network gear (routers, access points,
  the firewall, switches: `Signal.NETWORK_UPTIME`) each get a ranking of their own on the Restarts card
  (`containers`, `network`), not in the Uptime card, the machine totals or the intro's "machines watched".
  On the first real lab two access points headed "up right now" above the servers. Smart-home devices
  never count, even with an uptime sensor.
- Uptime comes only from integrations with an adapter, each checked in its own code: the uptime device
  class and the uptime/last_boot translation keys are also on lamps, plugs, printers, EV chargers and lawn
  mowers (WLED, Shelly, ESPHome, Matter, IPP, Automower ...). Where an integration has two uptime sensors
  and no translation keys, `EntityRule.unique_id_prefix`/`suffix` picks the device's: UniFi's other one is a
  client's connected time, FRITZ!Box's the internet connection's. Unique ids can hold MACs or serials, so
  they are matched against only, never reported (diagnostics list fixed fields). UPnP/IGD has no adapter:
  its "uptime" is the internet connection's.
- A card's "since" comes from its main numbers (`coverage.DATED_BY`): the servers' for Uptime and
  Restarts, the meters' for Power. Blocked and Media aren't dated by the source's own statistics (the
  cards read Wrapped's sensors and the look-back), and a history break only matters for what the cards
  read from statistics (`coverage.FROM_STATISTICS`).
- Services (Uptime Kuma): each monitor's `uptime_365d` sensor (%, a measurement, so HA keeps its statistics);
  its last hourly mean at the end of the period is that year's uptime, else its state while the period is
  now. On the Uptime card (`services`); a lab with only services gets the card without streaks
  (`longest: null`).
- Power cuts: NUT's raw `ups_status` ("OL", "OB DISCHRG"; not `ups_status_display`) or APC UPS Daemon's
  `status` ("ONBATT"). Only an explicit mains word (OL/ONLINE) ends a cut: COMMLOST, SHUTTING DOWN, WAIT, OFF
  say nothing (`on_battery` → None), else one outage counts twice, for good (the count is `total_increasing`). A `power_cuts` sensor per UPS counts switches to battery; when and how long (the latest
  500, one cut counts for at most 12 hours) are in its own storage, a cut going on is saved too. On the Power
  card (`power_cuts`); a UPS without meters picked makes the card (`kwh: null`). Trait: survivor.
- Power: the user picks the lab's meters in the options flow (`lab_meters`; starts empty, because the
  Energy dashboard's meters are usually the house's). Priced per hour with the dashboard's first price
  sensor (hourly mean, per kWh/Wh/MWh; a `total` price such as Energi Data Service has no mean, so the
  hour's last price), hours without a price at the average ("about"), else its fixed price. Until meters are picked, the card is locked with the `pick_meters` hint.
- Personality: `personality_card` scores traits 0–1 from numbers on the other cards (needs 2+ data
  cards, and so does the coverage check); the best names the lab if it scores ≥ 0.35, else "all_rounder". Only keys and numbers leave the
  core; names, taglines and reasons are in `frontend/src/text.ts`. Icons use HA's `ha-icon` (MDI): emoji
  are missing on older devices (🪨 showed as a box on Windows 10).
- Share image: `frontend/src/share.ts` draws 1080×1920 on a canvas (no icons: ha-icon can't be drawn
  on a canvas). Names only with the *Show machine names* toggle (off by default). Save = Web Share with
  the file where the browser can (needs a secure context, so not over plain http), else a download.

## Gotchas found while checking a real HA (2026-11-11)

- Integration updates can silently change a sensor's type (an uptime counter became a timestamp), which
  ends its long-term history. Detect the break and stitch across it.
- When counting restarts from hourly min/max statistics, one restart shows up in two hours in a row.
  Count it once.
- Many integrations set no `state_class`, so HA keeps no long-term history for them (AdGuard until HA
  2026.11, which made its sensors measurements).

## Found in the first real diagnostics (2026-11-12)

- HA 2026.10 has `device_class: uptime`: the time a device last restarted, ISO, no state_class. HA holds the
  value until it drifts more than 60 s (`UPTIME_DEFAULT_TOLERANCE_SECONDS`). Proxmox VE (`node_uptime`,
  `vm_uptime`, `container_uptime` until HA 2026.10; 2026.11 dropped those translation keys, so a node or
  guest is recognised by any of its `node_*`/`vm_*`/`container_*` sensors) and System Monitor use it; their
  old counter statistics remain (history break). Only from integrations with an adapter (see What counts).
- Proxmox VE storages are devices hanging off the node, like guests: guests need a `vm_*`/`container_*`
  entity, the node a `node_*` one. Portainer's stacks and volumes hang off the endpoint like containers:
  containers need a `container_state`/`container_started_at`/`container_restart_count` entity.
- HA keeps the devices and entities of removed containers (Docker's random names, old test containers),
  marked unavailable at start: 6 of 15 on the first real lab. A device rule's key entity must be available
  (`Entity.available`; no state yet counts as available). Their restart history still counts.
- The panel's script URL carries the bundle's sha256 (`?v=`), not the version: a development copy keeps
  version 0.1.0 between installs, and browsers kept running the old panel.
- The custom `asusrouter` integration has no translation keys; its uptime is the only `duration`/`s`/`total`.
- The custom `opnsense` integration (hass-opnsense) has none either; its only `timestamp` sensor is the
  firewall's boot time (checked in v1.3.3's sensor.py). The first real lab's firewall restarted unseen.
- Same machine seen by two integrations (Glances on the Proxmox node, System Monitor in the HA VM) is counted
  twice unless the user leaves one out (options: `left_out`, device ids). Matching boot times was rejected:
  with 60 s of drift, VMs autostarting a minute apart would be merged. Left-out devices are filtered in
  `read_entities`/`read_devices`, so coverage, recording and cards all skip them; changing options reloads.

## Conventions

- Texts: the panel's are in `frontend/src/text.ts`, one set per language (`*_EN`, `*_DA` typed as the English
  ones, so a missing Danish text doesn't build); `useLanguage` picks by HA's language. HA's own are in
  `translations/` (`tests/test_translations.py` checks every file has every key).

- Checks: `ruff check`, `ruff format --check`, `pytest --cov` (95 % minimum), strict `mypy` on the
  integration. CI runs them on Linux against the newest HA and against the oldest supported one
  (2026.10.4), plus hassfest and the HACS action (its brands check is skipped: the icon ships in `brand/`).
- HA 2026.11 (checked 2026-11-12): runs on the first real lab's 2026.11.1; mypy and importing every module
  are clean against it. The test plugin had no 2026.11 release yet (0.13.375 pins 2026.10.4 and breaks
  on 2026.11: `httpx2.alias_httpx()`, `_clear_logger_overwrites` gone); CI installs the newest plugin.
- Built against HA 2026.10 (minimum in `hacs.json`). That HA uses `probatio`, not voluptuous, for
  schemas, and a device has one `config_entry_id` (`DeviceEntry.config_entries` is deprecated).
- The repo is public, so keep personal lab details (names, IPs, hostnames, MACs, what was watched) out of
  committed files, test fixtures and commit messages included. Commits use the GitHub noreply address.

## Safe on a live HA (reviewed 2026-11-11)

Users run this on the HA their home depends on. Keep these true; a review checks them before any
"ready to install":
- Nothing slow on the event loop: statistics reads only via `get_instance(hass).async_add_executor_job`;
  the 15-minute rescan stays cheap (adapters looked up per integration, 7 ms for 6,000 entities); the
  extra scan for a new media player is one per 2 s at most, and the registry listener's filter is a string test.
- Bounded reads: first days only for statistics a card dates (uptime, services, lab meters), stored once;
  the cards are computed one at a time and reused for 10 minutes, reading one statistic at a time (a year of
  hourly rows for 100 containers at once is hundreds of MB on a small box). The look-back runs once per sensor, a
  minute after HA has started (`CoreState.running`; `hass.is_running` is true while starting too), as an
  entry background task: one source and 7 days per recorder job, value changes only, no attributes, parsed
  in that job; saved once at the end; a failure is logged and retried after the next start, and a damaged
  `.storage` file is read past.
- Few writes: counters save only when a count changes. Playback acts on start/stop, never on attribute-only
  updates (Jellyfin reports the position every 10 s), and adds ongoing playback every 5 minutes; a new title
  (music: every track) and the end of a power cut change only what is kept in memory, saved with the next write.
- A year's cards only show what was watched in that year (`_watched_in`): the year switch can offer years
  from before Wrapped knew a container, UPS or machine.
- Wrapped's unique ids are `<kind>_<source>`, and a kind can hold an underscore (`power_cuts`): read them
  with `inventory.split_unique_id`, never `partition("_")`.
- Odd states never raise: unavailable/unknown/non-numeric/naive/absurd values are ignored.
- Setup leaves nothing half-done: panel first (a taken address is a clear ConfigEntryError), platforms
  after, panel removed again if they fail. Removing the integration deletes its `.storage` files.
- Read-only towards everything else: no service calls, no writes to other entities, devices or Energy prefs.

## Developing on this Windows laptop

- HA doesn't run on Windows, but its test plugin does with two stand-ins that live only in `.venv`
  (never committed): `.venv/Lib/site-packages/fcntl.py` and `resource.py`. Recreate them if the venv is
  rebuilt. `tests/conftest.py` keeps local sockets open on Windows only, for asyncio's event loop.
- In tests, request `deps` (or `entry`) before `hass`: the recorder must start before HA.
- Build the panel with `cd frontend && npm ci && npm run build` and commit the bundle; CI checks it matches.
  Node is in `C:\Program Files\nodejs` (a shell started before the install may need it added to PATH).
- To see the panel without HA: serve a page that imports the bundle and sets a stand-in `hass` whose
  `callWS` returns coverage JSON made by the core from a made-up lab.
