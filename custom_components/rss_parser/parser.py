"""RSS and Atom parsing helpers."""

from __future__ import annotations

import calendar
from datetime import UTC, datetime
from hashlib import sha256
from html import unescape
from html.parser import HTMLParser
from typing import Any

import feedparser

from .models import FeedEntry, ParsedFeed


class FeedParseError(ValueError):
    """Raised when a response is not a usable feed."""


class _TextExtractor(HTMLParser):
    """Extract readable text from a small HTML fragment."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if text := data.strip():
            self.parts.append(text)


def _plain_text(value: Any) -> str:
    if not value:
        return ""
    parser = _TextExtractor()
    try:
        parser.feed(str(value))
        parser.close()
        return " ".join(parser.parts)
    except Exception:  # A malformed fragment should not reject the entire feed.
        return unescape(str(value)).strip()


def _datetime_from_entry(entry: Any) -> datetime | None:
    parsed_time = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed_time is None:
        return None
    return datetime.fromtimestamp(calendar.timegm(parsed_time), tz=UTC)


def _entry_id(entry: Any, title: str, link: str, published: datetime | None) -> str:
    provided = str(entry.get("id") or entry.get("guid") or "").strip()
    if provided:
        return provided
    raw = "\x1f".join((link, title, published.isoformat() if published else ""))
    return sha256(raw.encode("utf-8")).hexdigest()


def parse_feed(
    content: bytes, feed_name: str, fetched_at: datetime | None = None
) -> ParsedFeed:
    """Parse an RSS or Atom document into normalized entries."""
    parsed = feedparser.parse(content)
    if not parsed.entries:
        detail = str(getattr(parsed, "bozo_exception", "Feed contains no entries"))
        raise FeedParseError(detail)

    fetched_at = fetched_at or datetime.now(UTC)
    entries: list[FeedEntry] = []
    for raw_entry in parsed.entries:
        title = _plain_text(raw_entry.get("title")) or "(Ohne Titel)"
        link = str(raw_entry.get("link") or "").strip()
        summary = _plain_text(
            raw_entry.get("summary")
            or raw_entry.get("description")
            or (
                raw_entry.get("content", [{}])[0].get("value", "")
                if raw_entry.get("content")
                else ""
            )
        )
        author = _plain_text(raw_entry.get("author"))
        published = _datetime_from_entry(raw_entry)
        categories = tuple(
            str(tag.get("term", "")).strip()
            for tag in raw_entry.get("tags", [])
            if str(tag.get("term", "")).strip()
        )
        entries.append(
            FeedEntry(
                entry_id=_entry_id(raw_entry, title, link, published),
                title=title,
                link=link,
                summary=summary,
                author=author,
                categories=categories,
                published=published,
                fetched_at=fetched_at,
                feed_name=feed_name,
            )
        )

    return ParsedFeed(
        title=_plain_text(parsed.feed.get("title")) or feed_name,
        entries=tuple(entries),
    )
