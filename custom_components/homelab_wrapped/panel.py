"""The sidebar panel: one JavaScript module built from ``frontend/`` in the repo."""

from __future__ import annotations

import hashlib
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, callback
from homeassistant.loader import async_get_integration
from homeassistant.util.hass_dict import HassKey

from .const import DOMAIN, PANEL_ELEMENT, PANEL_ICON, PANEL_URL, STATIC_URL, TITLE

FRONTEND_DIR = Path(__file__).parent / "frontend"
STATIC_REGISTERED: HassKey[bool] = HassKey(f"{DOMAIN}_static")


async def async_register_panel(hass: HomeAssistant) -> None:
    """Serve the panel's files and add it to the sidebar."""
    # A static path can't be removed again, so it is registered once per HA run.
    if not hass.data.get(STATIC_REGISTERED):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(FRONTEND_DIR), cache_headers=False)]
        )
        hass.data[STATIC_REGISTERED] = True
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL,
        webcomponent_name=PANEL_ELEMENT,
        sidebar_title=TITLE,
        sidebar_icon=PANEL_ICON,
        module_url=f"{STATIC_URL}/{PANEL_ELEMENT}.js?v={await _async_fingerprint(hass)}",
        require_admin=False,
    )


async def _async_fingerprint(hass: HomeAssistant) -> str:
    """What makes the browser load the panel afresh after an update: the bundle's own hash.

    The integration's version stays the same between installs of a development
    copy, and browsers keep a script they have seen under the same address.
    """
    try:
        bundle = await hass.async_add_executor_job(
            (FRONTEND_DIR / f"{PANEL_ELEMENT}.js").read_bytes
        )
    except OSError:
        return str((await async_get_integration(hass, DOMAIN)).version)
    return hashlib.sha256(bundle).hexdigest()[:12]


@callback
def async_unregister_panel(hass: HomeAssistant) -> None:
    """Take the panel out of the sidebar."""
    frontend.async_remove_panel(hass, PANEL_URL, warn_if_unknown=False)
