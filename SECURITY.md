# Security

## Reporting a vulnerability

Please don't open a public issue. Report it privately through GitHub instead: the repository's
**Security** tab → **Report a vulnerability**. Say what you found, how to reproduce it, and which
version of Homelab Wrapped and Home Assistant you saw it on.

You'll get an answer within a week. Once a fix is released, the advisory is published with
credit to you, unless you'd rather not be named.

## Supported versions

Fixes go into the newest release only.

## What Homelab Wrapped touches

Useful for judging the impact of a report:

- It reads Home Assistant's entity and device registries, states and long-term statistics, and
  the Energy dashboard's settings. It writes nothing outside its own sensors and its files in
  `.storage/` (`homelab_wrapped.*`).
- It adds a sidebar panel and websocket commands, open to every logged-in Home Assistant user
  (admins and non-admins). They return the lab's numbers and the most played titles.
- It makes no network connections of its own. The share image is drawn in the browser.
- The diagnostics report leaves out entity ids, unique ids, names, titles, hostnames and IPs.
  Anything that leaks one of those is a bug worth reporting.
