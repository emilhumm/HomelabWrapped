"""Config flow: one click, nothing to fill in."""

from __future__ import annotations

from typing import Any

import probatio

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from .const import CONF_INSTALLED, CONF_LAB_METERS, CONF_LEFT_OUT, DOMAIN, TITLE
from .core.sources import ADAPTERS


class HomelabWrappedConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up Homelab Wrapped. Only one entry is allowed (see the manifest)."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Confirm, then remember the day Wrapped started collecting."""
        if user_input is not None:
            return self.async_create_entry(
                title=TITLE, data={CONF_INSTALLED: dt_util.now().date().isoformat()}
            )
        return self.async_show_form(step_id="user")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Options: which meters measure the lab."""
        return HomelabWrappedOptionsFlow()


class HomelabWrappedOptionsFlow(OptionsFlow):
    """Two questions.

    - The energy meters that measure the lab, for the Power card. Nothing is
      picked to begin with: the Energy dashboard's meters usually measure the
      house and its appliances, not the lab.
    - Devices to leave out: a second integration watching the same machine
      (Glances on the Proxmox host, System Monitor inside the HA VM), a test VM.
    """

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The lab's meters, and what to leave out."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        meters = selector.EntitySelector(
            selector.EntitySelectorConfig(
                filter=[{"domain": "sensor", "device_class": "energy"}], multiple=True
            )
        )
        # Only devices of integrations Wrapped reads (and that are set up here).
        here = {entry.domain for entry in self.hass.config_entries.async_entries()}
        readable = sorted({i for adapter in ADAPTERS for i in adapter.integrations} & here)
        devices = selector.DeviceSelector(
            selector.DeviceSelectorConfig(
                filter=[{"integration": integration} for integration in readable],
                multiple=True,
            )
        )
        options = self.config_entry.options
        schema = probatio.Schema(
            {
                probatio.Optional(
                    CONF_LAB_METERS, default=options.get(CONF_LAB_METERS, [])
                ): meters,
                probatio.Optional(CONF_LEFT_OUT, default=options.get(CONF_LEFT_OUT, [])): devices,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
