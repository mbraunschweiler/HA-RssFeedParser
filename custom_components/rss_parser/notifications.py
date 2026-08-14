"""Notification rendering and dispatch."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_NOTIFICATION_MESSAGE,
    CONF_NOTIFICATION_MODE,
    CONF_NOTIFICATION_TITLE,
    CONF_NOTIFICATIONS_ENABLED,
    CONF_NOTIFY_TARGETS,
    CONF_SUMMARY_LENGTH,
    DEFAULT_NOTIFICATION_MESSAGE,
    DEFAULT_NOTIFICATION_TITLE,
    DEFAULT_SUMMARY_LENGTH,
    NOTIFICATION_MODE_DIGEST,
)
from .models import FeedEntry

_LOGGER = logging.getLogger(__name__)


class _SafeValues(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def render_template(template: str, entry: FeedEntry, summary_length: int) -> str:
    """Render the documented safe placeholders without evaluating templates."""
    values = _SafeValues(
        title=entry.title,
        link=entry.link,
        summary=entry.summary[:summary_length],
        author=entry.author,
        feed_name=entry.feed_name,
        published=entry.published.isoformat() if entry.published else "",
    )
    return template.format_map(values)


async def async_send_notifications(
    hass: HomeAssistant, entries: tuple[FeedEntry, ...], options: dict[str, Any]
) -> None:
    """Send new entries to configured notify entities."""
    if not entries or not options.get(CONF_NOTIFICATIONS_ENABLED, False):
        _LOGGER.debug(
            "Skipping notifications: entries=%d, enabled=%s",
            len(entries),
            options.get(CONF_NOTIFICATIONS_ENABLED, False),
        )
        return
    targets = options.get(CONF_NOTIFY_TARGETS, [])
    if isinstance(targets, str):
        targets = [targets]
    if not targets:
        return

    title_template = str(
        options.get(CONF_NOTIFICATION_TITLE, DEFAULT_NOTIFICATION_TITLE)
    )
    message_template = str(
        options.get(CONF_NOTIFICATION_MESSAGE, DEFAULT_NOTIFICATION_MESSAGE)
    )
    summary_length = int(options.get(CONF_SUMMARY_LENGTH, DEFAULT_SUMMARY_LENGTH))

    payloads: list[tuple[str, str]]
    if options.get(CONF_NOTIFICATION_MODE) == NOTIFICATION_MODE_DIGEST:
        first = entries[0]
        title = render_template(title_template, first, summary_length)
        messages = [
            render_template(message_template, entry, summary_length)
            for entry in entries
        ]
        payloads = [(title, "\n\n".join(messages))]
    else:
        payloads = [
            (
                render_template(title_template, entry, summary_length),
                render_template(message_template, entry, summary_length),
            )
            for entry in entries
        ]

    for title, message in payloads:
        try:
            await hass.services.async_call(
                "notify",
                "send_message",
                {"title": title, "message": message},
                target={"entity_id": list(targets)},
                blocking=True,
            )
        except HomeAssistantError as err:
            _LOGGER.warning("Unable to send RSS notification: %s", err)
