# Contributing to Homelab Wrapped

Thanks for helping. The most useful things you can send:

- **A diagnostics report** when something isn't found or a number looks wrong: open an
  [issue](https://github.com/emilhumm/HomelabWrapped/issues/new/choose) and paste the panel's
  **Copy diagnostics**. It has no entity ids, names, titles, hostnames or IPs.
- **An adapter** for an integration Wrapped doesn't read yet.
- **A translation** of the panel and of Home Assistant's texts.

## Setting up

Python 3.14 and Node (for the panel). See [Development](README.md#development) in the README for
the commands. On Windows, Home Assistant's test plugin needs two stand-ins in the virtual
environment; `CLAUDE.md` says which.

Before a pull request, these must pass (CI runs them against the newest Home Assistant and the
oldest supported one):

```sh
ruff check . && ruff format --check .
pytest --cov      # 95 % coverage at least
mypy              # strict
```

If you change anything in `frontend/src/`, build the panel (`cd frontend && npm ci && npm run
build`) and commit the bundle in `custom_components/homelab_wrapped/frontend/`: CI checks that it
matches the source.

## Adding an integration

An adapter is a few lines in
[`core/sources.py`](custom_components/homelab_wrapped/core/sources.py): which integration it is,
and which of its entities or devices give which kind of data (uptime or last boot, blocked DNS
queries, playback, a UPS's status ...).

- **Find data by what it is, never by what it's called:** the integration, `device_class`,
  unit, `state_class` and `translation_key`. Users rename entities.
- **Check it against the integration's own code** (Home Assistant core, or the custom
  integration's repository) and say in the pull request which version you checked. Many
  integrations put an uptime class on things that aren't servers (lamps, plugs, printers,
  chargers); those must not count.
- If the integration only tells two sensors apart by unique id, match a prefix or suffix
  (`EntityRule.unique_id_prefix`/`suffix`). Unique ids can hold MAC addresses or serial
  numbers, so they're matched against only, never reported.
- Add a test in `tests/core/test_sources.py` built from your lab's diagnostics report.

## Translations

- The panel's texts are in [`frontend/src/text.ts`](frontend/src/text.ts), one set per language.
  A new language is typed as the English set, so the build fails while a text is missing. Add it
  to `LANGUAGES` and to `useLanguage`, which picks the set by Home Assistant's language.
- Home Assistant's texts (setup, options, sensor names) are in
  [`translations/`](custom_components/homelab_wrapped/translations/), one JSON file per language
  with every key of `en.json` (a test checks).

## Ground rules

People run this on the Home Assistant their home depends on.

- **Read-only:** no service calls, and no writes to other entities, devices or Energy settings.
- **Never block the event loop:** statistics and recorder reads go through the recorder's
  executor, and the 15-minute rescan stays cheap.
- **`core/` never imports Home Assistant** (`tests/core/test_purity.py` checks), so a standalone
  version can reuse it.
- **No personal data in the repository:** use made-up names in tests and examples (`pve-01`,
  `nas`), fake MAC addresses (`02:42:ac:11:00:07`) and documentation IP ranges
  (`192.0.2.0/24`), never your own lab's.
- **Nothing leaves the network,** and the share image keeps machine names off unless the user
  ticks *Show machine names*.

By contributing, you agree that your contribution is licensed under the [MIT License](LICENSE).
