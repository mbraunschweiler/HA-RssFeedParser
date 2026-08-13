"""Data models for RSS Parser."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class FeedEntry:
    """A normalized RSS or Atom entry."""

    entry_id: str
    title: str
    link: str
    summary: str
    author: str
    categories: tuple[str, ...]
    published: datetime | None
    fetched_at: datetime
    feed_name: str

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        result = asdict(self)
        result["categories"] = list(self.categories)
        result["published"] = self.published.isoformat() if self.published else None
        result["fetched_at"] = self.fetched_at.isoformat()
        return result

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> FeedEntry:
        """Restore an entry from storage."""
        return cls(
            entry_id=str(value["entry_id"]),
            title=str(value.get("title", "")),
            link=str(value.get("link", "")),
            summary=str(value.get("summary", "")),
            author=str(value.get("author", "")),
            categories=tuple(str(item) for item in value.get("categories", [])),
            published=(
                datetime.fromisoformat(value["published"])
                if value.get("published")
                else None
            ),
            fetched_at=datetime.fromisoformat(value["fetched_at"]),
            feed_name=str(value.get("feed_name", "")),
        )

    def event_data(self) -> dict[str, Any]:
        """Return a compact event payload."""
        return {
            "entry_id": self.entry_id,
            "feed_name": self.feed_name,
            "title": self.title,
            "link": self.link,
            "summary": self.summary[:1000],
            "author": self.author,
            "categories": list(self.categories),
            "published": self.published.isoformat() if self.published else None,
        }


@dataclass(frozen=True, slots=True)
class ParsedFeed:
    """A parsed feed response."""

    title: str
    entries: tuple[FeedEntry, ...]


@dataclass(frozen=True, slots=True)
class FetchResult:
    """The result of fetching a feed."""

    content: bytes | None
    etag: str | None
    last_modified: str | None
    not_modified: bool = False


@dataclass(frozen=True, slots=True)
class CoordinatorData:
    """Data exposed by the update coordinator."""

    latest_entry: FeedEntry | None
    new_entries: tuple[FeedEntry, ...]
    feed_title: str


def newest_entries(entries: tuple[FeedEntry, ...], limit: int) -> tuple[FeedEntry, ...]:
    """Return a chronological bounded set, preferring feed order on date ties."""
    indexed = enumerate(entries)
    ordered = sorted(
        indexed,
        key=lambda item: (item[1].published or item[1].fetched_at, -item[0]),
    )
    return tuple(entry for _, entry in ordered[-limit:])
