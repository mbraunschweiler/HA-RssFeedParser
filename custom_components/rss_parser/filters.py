"""Filtering rules for normalized feed entries."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from .const import (
    CONF_CASE_SENSITIVE,
    CONF_EXCLUDE_CATEGORIES,
    CONF_EXCLUDE_TERMS,
    CONF_INCLUDE_CATEGORIES,
    CONF_INCLUDE_TERMS,
    CONF_MAX_AGE_HOURS,
    CONF_USE_REGEX,
)
from .models import FeedEntry


def parse_rules(value: str | Iterable[str] | None) -> tuple[str, ...]:
    """Parse newline- or comma-separated rules."""
    if value is None:
        return ()
    values = [value] if isinstance(value, str) else list(value)
    result: list[str] = []
    for item in values:
        result.extend(
            part.strip() for part in str(item).replace(",", "\n").splitlines()
        )
    return tuple(dict.fromkeys(item for item in result if item))


def validate_regex_rules(*values: str | Iterable[str] | None) -> None:
    """Raise re.error if one configured regular expression is invalid."""
    for value in values:
        for pattern in parse_rules(value):
            re.compile(pattern)


@dataclass(frozen=True, slots=True)
class EntryFilter:
    """A compiled set of entry filters."""

    include_terms: tuple[str, ...] = ()
    exclude_terms: tuple[str, ...] = ()
    case_sensitive: bool = False
    use_regex: bool = False
    max_age_hours: int = 0
    include_categories: tuple[str, ...] = ()
    exclude_categories: tuple[str, ...] = ()

    @classmethod
    def from_options(cls, options: dict[str, Any]) -> EntryFilter:
        """Build a filter from config entry options."""
        return cls(
            include_terms=parse_rules(options.get(CONF_INCLUDE_TERMS)),
            exclude_terms=parse_rules(options.get(CONF_EXCLUDE_TERMS)),
            case_sensitive=bool(options.get(CONF_CASE_SENSITIVE, False)),
            use_regex=bool(options.get(CONF_USE_REGEX, False)),
            max_age_hours=int(options.get(CONF_MAX_AGE_HOURS, 0)),
            include_categories=parse_rules(options.get(CONF_INCLUDE_CATEGORIES)),
            exclude_categories=parse_rules(options.get(CONF_EXCLUDE_CATEGORIES)),
        )

    def matches(self, entry: FeedEntry, now: datetime | None = None) -> bool:
        """Return whether an entry satisfies all configured rules."""
        now = now or datetime.now(UTC)
        if (
            self.max_age_hours > 0
            and entry.published is not None
            and entry.published < now - timedelta(hours=self.max_age_hours)
        ):
            return False

        searchable = "\n".join(
            (entry.title, entry.summary, entry.author, entry.link, *entry.categories)
        )
        if self._any_matches(self.exclude_terms, searchable):
            return False
        if self.include_terms and not self._any_matches(self.include_terms, searchable):
            return False

        categories = "\n".join(entry.categories)
        if self._any_matches(self.exclude_categories, categories):
            return False
        return not self.include_categories or self._any_matches(
            self.include_categories, categories
        )

    def _any_matches(self, rules: tuple[str, ...], value: str) -> bool:
        flags = 0 if self.case_sensitive else re.IGNORECASE
        if self.use_regex:
            return any(
                re.search(pattern, value, flags=flags) is not None for pattern in rules
            )
        if not self.case_sensitive:
            value = value.casefold()
            return any(pattern.casefold() in value for pattern in rules)
        return any(pattern in value for pattern in rules)
