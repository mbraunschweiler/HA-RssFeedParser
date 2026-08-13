"""Persistent processed-entry storage."""

from __future__ import annotations

from collections import deque
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, MAX_SEEN_IDS, STORAGE_VERSION
from .models import FeedEntry


class SeenEntryStore:
    """Persist a bounded list of processed entry IDs and the latest match."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}"
        )
        self._ids: deque[str] = deque(maxlen=MAX_SEEN_IDS)
        self._id_set: set[str] = set()
        self.latest_entry: FeedEntry | None = None
        self.initialized = False

    async def async_load(self) -> None:
        """Load persisted state."""
        data = await self._store.async_load() or {}
        for entry_id in data.get("seen_ids", []):
            self._append(str(entry_id))
        if latest := data.get("latest_entry"):
            try:
                self.latest_entry = FeedEntry.from_dict(latest)
            except (KeyError, TypeError, ValueError):
                self.latest_entry = None
        self.initialized = bool(data.get("initialized", False))

    def contains(self, entry_id: str) -> bool:
        """Return whether an entry has already been processed."""
        return entry_id in self._id_set

    async def async_mark_processed(
        self, entries: tuple[FeedEntry, ...], latest_entry: FeedEntry | None
    ) -> None:
        """Persist processed entries and the latest accepted entry."""
        for entry in entries:
            self._append(entry.entry_id)
        self.initialized = True
        if latest_entry is not None:
            self.latest_entry = latest_entry
        await self._store.async_save(
            {
                "initialized": self.initialized,
                "seen_ids": list(self._ids),
                "latest_entry": (
                    self.latest_entry.as_dict() if self.latest_entry else None
                ),
            }
        )

    def _append(self, entry_id: str) -> None:
        if entry_id in self._id_set:
            return
        if len(self._ids) == self._ids.maxlen:
            self._id_set.discard(self._ids[0])
        self._ids.append(entry_id)
        self._id_set.add(entry_id)
