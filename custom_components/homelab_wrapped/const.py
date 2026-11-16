"""Constants for Homelab Wrapped."""

from datetime import time
from typing import Final

DOMAIN: Final = "homelab_wrapped"
TITLE: Final = "Homelab Wrapped"

CONF_INSTALLED: Final = "installed"
"""Date Wrapped was set up: it collects what HA doesn't keep itself from then on."""

CONF_LAB_METERS: Final = "lab_meters"
"""Energy meters that measure the lab (not the house), for the Power card."""

CONF_LEFT_OUT: Final = "left_out"
"""Devices Wrapped ignores: a second integration watching the same machine, a test VM ..."""

DNS_READ_AT: Final = time(23, 55)
"""When the rolling 24-hour blocked count is read: late, so it lands on the day it covers."""

PANEL_URL: Final = "homelab-wrapped"
PANEL_ELEMENT: Final = "homelab-wrapped-panel"
PANEL_ICON: Final = "mdi:gift-outline"
STATIC_URL: Final = "/homelab_wrapped_static"
