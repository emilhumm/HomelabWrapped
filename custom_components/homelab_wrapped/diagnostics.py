"""Diagnostics download: the same report as the panel's "copy diagnostics" button."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .runtime import WrappedConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: WrappedConfigEntry
) -> dict[str, Any]:
    """What the lab has, without entity ids, names, hostnames or IPs."""
    return await entry.runtime_data.async_diagnostics()
