"""RSS Parser custom integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    PLATFORMS,
)
from .coordinator import RssParserCoordinator
from .feed_client import FeedClient
from .storage import SeenEntryStore


@dataclass(slots=True)
class RssParserRuntimeData:
    """Runtime objects owned by a config entry."""

    coordinator: RssParserCoordinator


RssParserConfigEntry = ConfigEntry[RssParserRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: RssParserConfigEntry) -> bool:
    """Set up RSS Parser from a config entry."""
    session = async_get_clientsession(hass)
    timeout = int(entry.options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT))
    client = FeedClient(session, timeout)
    store = SeenEntryStore(hass, entry.entry_id)
    await store.async_load()
    coordinator = RssParserCoordinator(hass, entry, client, store)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = RssParserRuntimeData(coordinator)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: RssParserConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_options_updated(
    hass: HomeAssistant, entry: RssParserConfigEntry
) -> None:
    """Apply a changed scan interval immediately without waiting for the next reload."""
    interval = int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
    entry.runtime_data.coordinator.update_interval = timedelta(minutes=interval)
