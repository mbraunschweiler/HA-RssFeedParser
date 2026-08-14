"""Button platform for RSS Parser."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import RssParserConfigEntry
from .const import CONF_FEED_NAME, DOMAIN
from .coordinator import RssParserCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RssParserConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the refresh button."""
    async_add_entities([RssParserRefreshButton(entry.runtime_data.coordinator, entry)])


class RssParserRefreshButton(CoordinatorEntity[RssParserCoordinator], ButtonEntity):
    """Button to trigger an immediate feed refresh."""

    _attr_has_entity_name = True
    _attr_translation_key = "refresh"
    _attr_icon = "mdi:refresh"

    def __init__(
        self, coordinator: RssParserCoordinator, entry: RssParserConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_refresh"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=str(entry.data[CONF_FEED_NAME]),
            manufacturer="RSS Parser",
            model="RSS/Atom Feed",
        )

    async def async_press(self) -> None:
        """Request an immediate feed refresh."""
        await self.coordinator.async_request_refresh()
