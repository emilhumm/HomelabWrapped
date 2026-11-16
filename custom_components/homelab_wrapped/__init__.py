"""Homelab Wrapped: Spotify-Wrapped-style story cards for a whole homelab.

This package is the thin Home Assistant layer. The logic lives in ``core``,
which never imports Home Assistant.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from . import websocket
from .backfill import BackfillStore
from .const import CONF_INSTALLED, DOMAIN, PANEL_URL
from .inventory import FirstDays
from .panel import async_register_panel, async_unregister_panel
from .runtime import Wrapped, WrappedConfigEntry
from .storage import STORAGE_VERSION, TallyStore

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS = [Platform.SENSOR]
STORES = (f"{DOMAIN}.tally", f"{DOMAIN}.first_days", f"{DOMAIN}.backfill")


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the websocket commands the panel uses."""
    websocket.async_register(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: WrappedConfigEntry) -> bool:
    """Start counting what HA doesn't keep, and add the panel to the sidebar."""
    tally = TallyStore(hass)
    await tally.async_load()
    backfill = BackfillStore(hass)
    await backfill.async_load()
    entry.runtime_data = Wrapped(
        hass,
        entry_id=entry.entry_id,
        installed=date.fromisoformat(entry.data[CONF_INSTALLED]),
        first_days=FirstDays(hass),
        tally=tally,
        backfill=backfill,
    )
    try:
        await async_register_panel(hass)
    except ValueError as err:  # another panel or dashboard has the address
        raise ConfigEntryError(
            f"The sidebar address /{PANEL_URL} is already used by another panel or dashboard"
        ) from err
    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except BaseException:
        async_unregister_panel(hass)
        raise
    entry.async_on_unload(hass.bus.async_listen(EVENT_HOMEASSISTANT_STOP, tally.async_save))
    entry.async_on_unload(entry.add_update_listener(_async_options_changed))
    return True


async def _async_options_changed(hass: HomeAssistant, entry: WrappedConfigEntry) -> None:
    """Lab meters or left-out devices changed: reload, so it all applies at once."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_entry(hass: HomeAssistant, entry: WrappedConfigEntry) -> None:
    """Removed for good: delete Wrapped's own files (counters, first days, look-back) too.

    The long-term statistics of its sensors stay in the recorder, as for any
    removed entity; they can be deleted under Developer tools → Statistics.
    """
    for store in STORES:
        await Store[Any](hass, STORAGE_VERSION, store).async_remove()


async def async_unload_entry(hass: HomeAssistant, entry: WrappedConfigEntry) -> bool:
    """Stop counting and take the panel out of the sidebar."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False  # pragma: no cover
    await entry.runtime_data.tally.async_save()
    async_unregister_panel(hass)
    return True
