"""Websocket commands the panel calls. All of them only read."""

from __future__ import annotations

from typing import Any

import probatio

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv

from .runtime import loaded

NOT_SET_UP = "Homelab Wrapped isn't set up"


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register the commands."""
    websocket_api.async_register_command(hass, ws_coverage)
    websocket_api.async_register_command(hass, ws_diagnostics)
    websocket_api.async_register_command(hass, ws_cards)


@websocket_api.websocket_command({probatio.Required("type"): "homelab_wrapped/coverage"})
@websocket_api.async_response
async def ws_coverage(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Which cards this lab can make today."""
    if (wrapped := loaded(hass)) is None:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, NOT_SET_UP)
        return
    connection.send_result(msg["id"], await wrapped.async_coverage_report())


@websocket_api.websocket_command({probatio.Required("type"): "homelab_wrapped/diagnostics"})
@websocket_api.async_response
async def ws_diagnostics(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """The "copy diagnostics" report, with names stripped."""
    if (wrapped := loaded(hass)) is None:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, NOT_SET_UP)
        return
    connection.send_result(msg["id"], await wrapped.async_diagnostics())


@websocket_api.websocket_command(
    {
        probatio.Required("type"): "homelab_wrapped/cards",
        probatio.Optional("year"): probatio.All(
            cv.positive_int, probatio.Range(min=2000, max=2100)
        ),
    }
)
@websocket_api.async_response
async def ws_cards(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """The story cards for a year (this year by default)."""
    if (wrapped := loaded(hass)) is None:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, NOT_SET_UP)
        return
    connection.send_result(msg["id"], await wrapped.async_cards(msg.get("year")))
