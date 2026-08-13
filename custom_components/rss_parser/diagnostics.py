"""Diagnostics support for RSS Parser."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import RssParserConfigEntry
from .const import CONF_FEED_URL


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: RssParserConfigEntry
) -> dict[str, Any]:
    """Return redacted diagnostics for a config entry."""
    coordinator = entry.runtime_data.coordinator
    return {
        "data": async_redact_data(dict(entry.data), {CONF_FEED_URL}),
        "options": async_redact_data(dict(entry.options), set()),
        "last_update_success": coordinator.last_update_success,
        "latest_entry": (
            coordinator.data.latest_entry.event_data()
            if coordinator.data and coordinator.data.latest_entry
            else None
        ),
    }
