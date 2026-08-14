"""Update coordinator for an RSS feed."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_FEED_NAME,
    CONF_FEED_URL,
    CONF_MAX_ENTRIES,
    CONF_SCAN_INTERVAL,
    CONF_SEND_EXISTING,
    DEFAULT_MAX_ENTRIES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENT_NEW_ENTRY,
    MAX_CONSECUTIVE_FAILURES,
    MAX_SEEN_IDS,
    REPAIR_ISSUE_FEED_UNAVAILABLE,
)
from .feed_client import FeedClient, FeedClientError
from .filters import EntryFilter
from .models import CoordinatorData, FeedEntry, newest_entries
from .notifications import async_send_notifications
from .parser import FeedParseError, parse_feed
from .storage import SeenEntryStore

_LOGGER = logging.getLogger(__name__)


class RssParserCoordinator(DataUpdateCoordinator[CoordinatorData]):
    """Poll and process one configured feed."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: FeedClient,
        store: SeenEntryStore,
    ) -> None:
        self.entry = entry
        self.client = client
        self.store = store
        self.etag: str | None = None
        self.last_modified: str | None = None
        self.feed_title = str(entry.data[CONF_FEED_NAME])
        self._consecutive_failures: int = 0
        self.next_refresh_at: datetime | None = None
        interval = int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=str(entry.data[CONF_FEED_NAME]),
            update_interval=timedelta(minutes=interval),
            always_update=False,
        )

    async def _async_update_data(self) -> CoordinatorData:
        try:
            result = await self.client.async_fetch(
                str(self.entry.data[CONF_FEED_URL]),
                etag=self.etag,
                last_modified=self.last_modified,
            )
            if result.not_modified:
                self._handle_success()
                return CoordinatorData(self.store.latest_entry, (), self.feed_title)
            assert result.content is not None
            parsed = await self.hass.async_add_executor_job(
                parse_feed,
                result.content,
                str(self.entry.data[CONF_FEED_NAME]),
            )
        except (FeedClientError, FeedParseError, TimeoutError) as err:
            self._handle_failure()
            raise UpdateFailed(f"Unable to update feed: {err}") from err

        self._handle_success()
        self.etag = result.etag
        self.last_modified = result.last_modified
        self.feed_title = parsed.title
        candidates = newest_entries(parsed.entries, MAX_SEEN_IDS)
        all_unseen = tuple(
            item for item in candidates if not self.store.contains(item.entry_id)
        )
        if not self.store.initialized and not self.entry.options.get(
            CONF_SEND_EXISTING, False
        ):
            await self.store.async_mark_processed(candidates, None)
            return CoordinatorData(self.store.latest_entry, (), parsed.title)

        entry_filter = EntryFilter.from_options(dict(self.entry.options))
        accepted = [entry for entry in all_unseen if entry_filter.matches(entry)]
        accepted.sort(key=_sort_key)
        limit = int(self.entry.options.get(CONF_MAX_ENTRIES, DEFAULT_MAX_ENTRIES))
        accepted_tuple = tuple(accepted[-limit:])
        discarded_count = len(all_unseen) - len(accepted_tuple)
        latest = accepted_tuple[-1] if accepted_tuple else self.store.latest_entry

        # Mark every observed entry so permanently filtered entries are not reconsidered
        # during every poll. Changing filters applies to entries received afterwards.
        await self.store.async_mark_processed(candidates, latest)

        if accepted_tuple:
            for item in accepted_tuple:
                self.hass.bus.async_fire(EVENT_NEW_ENTRY, item.event_data())
            await async_send_notifications(
                self.hass, accepted_tuple, dict(self.entry.options)
            )
        return CoordinatorData(latest, accepted_tuple, parsed.title, discarded_count)

    def _handle_success(self) -> None:
        if self._consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            ir.async_delete_issue(self.hass, DOMAIN, REPAIR_ISSUE_FEED_UNAVAILABLE)
        self._consecutive_failures = 0
        self.next_refresh_at = datetime.now(UTC) + self.update_interval

    def _handle_failure(self) -> None:
        self._consecutive_failures += 1
        self.next_refresh_at = datetime.now(UTC) + self.update_interval
        if self._consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                REPAIR_ISSUE_FEED_UNAVAILABLE,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=REPAIR_ISSUE_FEED_UNAVAILABLE,
                translation_placeholders={
                    "feed_name": self.feed_title,
                    "feed_url": str(self.entry.data[CONF_FEED_URL]),
                },
            )


def _sort_key(entry: FeedEntry) -> datetime:
    """Sort undated entries after using their fetch time."""
    return entry.published or entry.fetched_at.replace(tzinfo=UTC)
