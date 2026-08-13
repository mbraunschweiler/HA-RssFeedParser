"""RSS Parser custom integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_TIMEOUT, DEFAULT_TIMEOUT, PLATFORMS
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
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: RssParserConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
