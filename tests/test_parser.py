"""Tests for RSS and Atom normalization."""

from datetime import UTC
from pathlib import Path

import pytest

from custom_components.rss_parser.parser import FeedParseError, parse_feed

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    ("fixture", "feed_title", "entry_id", "title", "category"),
    [
        (
            "rss.xml",
            "Example RSS",
            "rss-1",
            "Home Assistant 2026.8 veröffentlicht",
            "Smart Home",
        ),
        ("atom.xml", "Example Atom", "atom-1", "Neue Automation", "Automation"),
    ],
)
def test_parse_feed_formats(
    fixture: str, feed_title: str, entry_id: str, title: str, category: str
) -> None:
    parsed = parse_feed((FIXTURES / fixture).read_bytes(), "Configured name")

    assert parsed.title == feed_title
    assert len(parsed.entries) == 1
    entry = parsed.entries[0]
    assert entry.entry_id == entry_id
    assert entry.title == title
    assert entry.categories == (category,)
    assert entry.published is not None
    assert entry.published.tzinfo is UTC
    assert "<" not in entry.summary


def test_missing_id_gets_stable_hash() -> None:
    content = b"""<rss version='2.0'><channel><title>X</title><item>
        <title>Entry</title><link>https://example.com/1</link>
        </item></channel></rss>"""
    first = parse_feed(content, "X").entries[0]
    second = parse_feed(content, "X").entries[0]
    assert first.entry_id == second.entry_id
    assert len(first.entry_id) == 64


def test_empty_feed_is_rejected() -> None:
    with pytest.raises(FeedParseError):
        parse_feed(b"<rss><channel><title>Empty</title></channel></rss>", "Empty")
