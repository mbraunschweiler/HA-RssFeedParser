"""Tests for entry filtering."""

import re
from datetime import UTC, datetime, timedelta

import pytest

from custom_components.rss_parser.filters import (
    EntryFilter,
    parse_rules,
    validate_regex_rules,
)
from custom_components.rss_parser.models import FeedEntry, newest_entries


def _entry(**changes: object) -> FeedEntry:
    values = {
        "entry_id": "1",
        "title": "Home Assistant Release",
        "link": "https://example.com/1",
        "summary": "Neue Funktionen",
        "author": "Anna",
        "categories": ("Smart Home",),
        "published": datetime.now(UTC),
        "fetched_at": datetime.now(UTC),
        "feed_name": "Test",
    }
    values.update(changes)
    return FeedEntry(**values)  # type: ignore[arg-type]


def test_parse_rules_accepts_commas_and_lines() -> None:
    assert parse_rules("alpha, beta\nalpha") == ("alpha", "beta")


def test_include_and_exclude_rules() -> None:
    assert EntryFilter(include_terms=("assistant",)).matches(_entry())
    assert not EntryFilter(exclude_terms=("release",)).matches(_entry())
    assert not EntryFilter(include_terms=("Matter",)).matches(_entry())


def test_category_and_age_filters() -> None:
    assert EntryFilter(include_categories=("smart",)).matches(_entry())
    assert not EntryFilter(exclude_categories=("home",)).matches(_entry())
    old = _entry(published=datetime.now(UTC) - timedelta(hours=25))
    assert not EntryFilter(max_age_hours=24).matches(old)


def test_regex_and_case_sensitivity() -> None:
    assert EntryFilter(include_terms=(r"Home\s+Assistant",), use_regex=True).matches(
        _entry()
    )
    assert not EntryFilter(include_terms=("assistant",), case_sensitive=True).matches(
        _entry()
    )
    with pytest.raises(re.error):
        validate_regex_rules("[")


def test_newest_entries_are_bounded_and_chronological() -> None:
    now = datetime.now(UTC)
    entries = tuple(
        _entry(entry_id=str(index), published=now - timedelta(hours=index))
        for index in range(5)
    )

    result = newest_entries(entries, 3)

    assert [entry.entry_id for entry in result] == ["2", "1", "0"]
