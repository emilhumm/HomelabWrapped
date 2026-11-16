"""Where Wrapped's counters keep their state: ``.storage``, so HA backups include it."""

from __future__ import annotations

from typing import Any

from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

STORAGE_VERSION = 1


class TallyStore:
    """The counters' state, by sensor unique id.

    A count is saved before its sensor shows it. Otherwise, after a crash at the
    wrong moment, the sensor would come back lower than HA last recorded, HA would
    take the drop for a meter reset, and count the whole value a second time.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Nothing is read until ``async_load``."""
        self._store: Store[dict[str, dict[str, Any]]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.tally"
        )
        self._data: dict[str, dict[str, Any]] = {}

    async def async_load(self) -> None:
        """Read what was saved."""
        self._data = await self._store.async_load() or {}

    def get(self, key: str) -> dict[str, Any] | None:
        """One counter's saved state."""
        return self._data.get(key)

    def update(self, key: str, value: dict[str, Any]) -> None:
        """Change a counter's state without saving now.

        For details a crash may lose (such as the latest boot time seen); they are
        saved with the next count, on unload and when HA stops.
        """
        self._data[key] = value

    async def async_commit(self, key: str, value: dict[str, Any]) -> None:
        """Change a counter's state and save it now."""
        self._data[key] = value
        await self._store.async_save(self._data)

    async def async_save(self, event: Event | None = None) -> None:
        """Save everything (also used as the listener for HA stopping)."""
        await self._store.async_save(self._data)
