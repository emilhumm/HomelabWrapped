"""Shared fixtures."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
import pytest_socket

from custom_components.homelab_wrapped.const import CONF_INSTALLED, DOMAIN, TITLE
from homeassistant.components.recorder import Recorder
from homeassistant.core import HomeAssistant

pytest_plugins = "pytest_homeassistant_custom_component"

if sys.platform == "win32":  # pragma: no cover
    # Let the tests run locally on Windows too. The HA test plugin blocks every
    # socket but Unix sockets, and asyncio on Windows builds its event loop's
    # wake-up pipe from a local TCP socket pair. Connections to other hosts stay
    # blocked by socket_allow_hosts. CI runs on Linux, where nothing changes.
    def _keep_local_sockets(*args: Any, **kwargs: Any) -> None:
        """Leave sockets enabled."""

    pytest_socket.disable_socket = _keep_local_sockets

INSTALLED = "2026-11-09"


@dataclass
class Panel:
    """Mocks standing in for the frontend's panel functions."""

    register: AsyncMock
    remove: MagicMock


@pytest.fixture
async def deps(
    recorder_mock: Recorder, enable_custom_integrations: None, hass: HomeAssistant
) -> AsyncGenerator[Panel]:
    """Everything the integration depends on, with the frontend mocked (it isn't installed).

    Request it before ``hass``: the recorder must start before Home Assistant.
    """
    hass.config.components.update({"frontend", "panel_custom"})
    with (
        patch("homeassistant.components.panel_custom.async_register_panel") as register,
        patch("homeassistant.components.frontend.async_remove_panel") as remove,
    ):
        yield Panel(register, remove)


@pytest.fixture
async def entry(deps: Panel, hass: HomeAssistant) -> MockConfigEntry:
    """Homelab Wrapped, set up and loaded."""
    entry = MockConfigEntry(domain=DOMAIN, title=TITLE, data={CONF_INSTALLED: INSTALLED})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
