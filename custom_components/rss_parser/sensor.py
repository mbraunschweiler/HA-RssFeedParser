"""Sensor platform for RSS Parser."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
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
    """Set up the feed sensors."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        [
            RssParserSensor(coordinator, entry),
            RssParserNewEntriesSensor(coordinator, entry),
            RssParserDiscardedSensor(coordinator, entry),
            RssParserNextRefreshSensor(coordinator, entry),
        ]
    )


class RssParserSensor(CoordinatorEntity[RssParserCoordinator], SensorEntity):
    """Represent the latest accepted item of one feed."""

    _attr_has_entity_name = True
    _attr_translation_key = "latest_entry"
    _attr_icon = "mdi:rss"

    def __init__(
        self, coordinator: RssParserCoordinator, entry: RssParserConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_latest_entry"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=str(entry.data[CONF_FEED_NAME]),
            manufacturer="RSS Parser",
            model="RSS/Atom Feed",
        )

    @property
    def native_value(self) -> str | None:
        """Return the latest entry title."""
        entry = self.coordinator.data.latest_entry
        return entry.title[:255] if entry else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return details of the latest accepted entry."""
        entry = self.coordinator.data.latest_entry
        attributes: dict[str, Any] = {
            "feed_title": self.coordinator.data.feed_title,
            "new_entries": len(self.coordinator.data.new_entries),
        }
        if entry is None:
            return attributes
        attributes.update(
            {
                "entry_id": entry.entry_id,
                "link": entry.link,
                "summary": entry.summary[:1000],
                "author": entry.author,
                "categories": list(entry.categories),
                "published": entry.published.isoformat() if entry.published else None,
            }
        )
        return attributes


class RssParserNewEntriesSensor(CoordinatorEntity[RssParserCoordinator], SensorEntity):
    """Count of new entries accepted in the last poll."""

    _attr_has_entity_name = True
    _attr_translation_key = "new_entries_count"
    _attr_icon = "mdi:rss-box"

    def __init__(
        self, coordinator: RssParserCoordinator, entry: RssParserConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_new_entries_count"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=str(entry.data[CONF_FEED_NAME]),
            manufacturer="RSS Parser",
            model="RSS/Atom Feed",
        )

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.new_entries)


class RssParserDiscardedSensor(CoordinatorEntity[RssParserCoordinator], SensorEntity):
    """Count of new feed entries discarded by filters in the last poll."""

    _attr_has_entity_name = True
    _attr_translation_key = "discarded_count"
    _attr_icon = "mdi:filter-remove"

    def __init__(
        self, coordinator: RssParserCoordinator, entry: RssParserConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_discarded_count"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=str(entry.data[CONF_FEED_NAME]),
            manufacturer="RSS Parser",
            model="RSS/Atom Feed",
        )

    @property
    def native_value(self) -> int:
        return self.coordinator.data.discarded_count


class RssParserNextRefreshSensor(CoordinatorEntity[RssParserCoordinator], SensorEntity):
    """Timestamp of the next scheduled feed poll."""

    _attr_has_entity_name = True
    _attr_translation_key = "next_refresh"
    _attr_icon = "mdi:clock-outline"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self, coordinator: RssParserCoordinator, entry: RssParserConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_next_refresh"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=str(entry.data[CONF_FEED_NAME]),
            manufacturer="RSS Parser",
            model="RSS/Atom Feed",
        )

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.next_refresh_at
