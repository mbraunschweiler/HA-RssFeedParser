"""Constants for the RSS Parser integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "rss_parser"
PLATFORMS: Final = ["sensor", "button"]

CONF_FEED_NAME: Final = "feed_name"
CONF_FEED_URL: Final = "feed_url"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_TIMEOUT: Final = "timeout"
CONF_SEND_EXISTING: Final = "send_existing"
CONF_MAX_ENTRIES: Final = "max_entries"
CONF_INCLUDE_TERMS: Final = "include_terms"
CONF_EXCLUDE_TERMS: Final = "exclude_terms"
CONF_CASE_SENSITIVE: Final = "case_sensitive"
CONF_USE_REGEX: Final = "use_regex"
CONF_MAX_AGE_HOURS: Final = "max_age_hours"
CONF_INCLUDE_CATEGORIES: Final = "include_categories"
CONF_EXCLUDE_CATEGORIES: Final = "exclude_categories"
CONF_NOTIFICATIONS_ENABLED: Final = "notifications_enabled"
CONF_NOTIFY_TARGETS: Final = "notify_targets"
CONF_NOTIFICATION_MODE: Final = "notification_mode"
CONF_NOTIFICATION_TITLE: Final = "notification_title"
CONF_NOTIFICATION_MESSAGE: Final = "notification_message"
CONF_SUMMARY_LENGTH: Final = "summary_length"

NOTIFICATION_MODE_INDIVIDUAL: Final = "individual"
NOTIFICATION_MODE_DIGEST: Final = "digest"

DEFAULT_SCAN_INTERVAL: Final = 15
DEFAULT_TIMEOUT: Final = 20
DEFAULT_MAX_ENTRIES: Final = 20
DEFAULT_SUMMARY_LENGTH: Final = 300
DEFAULT_NOTIFICATION_TITLE: Final = "Neuer Beitrag in {feed_name}"
DEFAULT_NOTIFICATION_MESSAGE: Final = "{title}\n{summary}\n{link}"

MIN_SCAN_INTERVAL: Final = 5
MAX_SCAN_INTERVAL: Final = 1440
MIN_TIMEOUT: Final = 5
MAX_TIMEOUT: Final = 120
MAX_RESPONSE_SIZE: Final = 5 * 1024 * 1024
MAX_SEEN_IDS: Final = 500
STORAGE_VERSION: Final = 1

EVENT_NEW_ENTRY: Final = "rss_parser_new_entry"

REPAIR_ISSUE_FEED_UNAVAILABLE: Final = "feed_unavailable"
MAX_CONSECUTIVE_FAILURES: Final = 3
