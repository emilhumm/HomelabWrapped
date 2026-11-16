"""Config flow, setup, unload and the sidebar panel."""

from __future__ import annotations

from datetime import date
import hashlib
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components import homelab_wrapped
from custom_components.homelab_wrapped import panel as wrapped_panel
from custom_components.homelab_wrapped.const import DOMAIN
from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.loader import async_get_integration

from .conftest import Panel


@pytest.mark.freeze_time("2026-11-11T12:00:00+00:00")
async def test_flow_remembers_the_install_day(deps: Panel, hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Homelab Wrapped"
    assert result["data"] == {"installed": "2026-11-11"}


async def test_only_one_entry(deps: Panel, hass: HomeAssistant, entry: MockConfigEntry) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_setup_reload_and_unload(
    deps: Panel, hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.installed == date(2026, 11, 9)
    deps.register.assert_awaited_once()
    panel = deps.register.await_args.kwargs
    assert panel["frontend_url_path"] == "homelab-wrapped"
    assert panel["webcomponent_name"] == "homelab-wrapped-panel"
    # The bundle's own hash: a browser loads it afresh after every update.
    bundle = Path(homelab_wrapped.__file__).parent / "frontend" / "homelab-wrapped-panel.js"
    fingerprint = hashlib.sha256(bundle.read_bytes()).hexdigest()[:12]
    assert (
        panel["module_url"] == f"/homelab_wrapped_static/homelab-wrapped-panel.js?v={fingerprint}"
    )
    assert panel["require_admin"] is False

    # The static path is registered once; a second registration would raise.
    assert await hass.config_entries.async_reload(entry.entry_id)
    assert entry.state is ConfigEntryState.LOADED
    assert deps.register.await_count == 2

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
    deps.remove.assert_called_with(hass, "homelab-wrapped", warn_if_unknown=False)


async def test_options_pick_the_lab_meters(
    deps: Panel, hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"lab_meters": ["sensor.rack_energy"]}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {"lab_meters": ["sensor.rack_energy"], "left_out": []}
    assert entry.runtime_data.lab_meters == ("sensor.rack_energy",)


async def test_taken_sidebar_address_leaves_nothing_running(
    deps: Panel, hass: HomeAssistant
) -> None:
    deps.register.side_effect = ValueError("Overwriting panel homelab-wrapped")
    entry = MockConfigEntry(domain=DOMAIN, data={"installed": "2026-11-09"})
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert not hass.states.async_entity_ids("sensor")


async def test_failed_platform_setup_removes_the_panel(deps: Panel, hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={"installed": "2026-11-09"})
    entry.add_to_hass(hass)
    with patch.object(
        hass.config_entries, "async_forward_entry_setups", side_effect=RuntimeError("boom")
    ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
    deps.remove.assert_called_with(hass, "homelab-wrapped", warn_if_unknown=False)


async def test_removing_deletes_wrappeds_files(
    deps: Panel, hass: HomeAssistant, entry: MockConfigEntry, hass_storage: dict[str, Any]
) -> None:
    hass_storage["homelab_wrapped.tally"] = {
        "version": 1,
        "key": "homelab_wrapped.tally",
        "data": {},
    }
    hass_storage["homelab_wrapped.first_days"] = {
        "version": 1,
        "key": "homelab_wrapped.first_days",
        "data": {},
    }
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert "homelab_wrapped.tally" not in hass_storage
    assert "homelab_wrapped.first_days" not in hass_storage


async def test_without_its_bundle_the_panel_address_carries_the_version(
    deps: Panel, hass: HomeAssistant, tmp_path: Path
) -> None:
    with patch.object(wrapped_panel, "FRONTEND_DIR", tmp_path):
        assert await wrapped_panel._async_fingerprint(hass) == "0.1.0"


async def test_it_brings_its_own_icon(deps: Panel, hass: HomeAssistant) -> None:
    """HA serves a custom integration's icon from its brand/ folder."""
    integration = await async_get_integration(hass, DOMAIN)
    assert integration.has_branding
    brand = Path(homelab_wrapped.__file__).parent / "brand"
    assert {path.name for path in brand.iterdir()} == {"icon.png", "icon@2x.png"}
