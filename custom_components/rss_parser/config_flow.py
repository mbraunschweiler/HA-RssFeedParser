"""UI configuration flow for RSS Parser."""

from __future__ import annotations

import re
from hashlib import sha256
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult, OptionsFlowWithReload
from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_CASE_SENSITIVE,
    CONF_EXCLUDE_CATEGORIES,
    CONF_EXCLUDE_TERMS,
    CONF_FEED_NAME,
    CONF_FEED_URL,
    CONF_INCLUDE_CATEGORIES,
    CONF_INCLUDE_TERMS,
    CONF_MAX_AGE_HOURS,
    CONF_MAX_ENTRIES,
    CONF_NOTIFICATION_MESSAGE,
    CONF_NOTIFICATION_MODE,
    CONF_NOTIFICATION_TITLE,
    CONF_NOTIFICATIONS_ENABLED,
    CONF_NOTIFY_TARGETS,
    CONF_SCAN_INTERVAL,
    CONF_SEND_EXISTING,
    CONF_SUMMARY_LENGTH,
    CONF_TIMEOUT,
    CONF_USE_REGEX,
    DEFAULT_MAX_ENTRIES,
    DEFAULT_NOTIFICATION_MESSAGE,
    DEFAULT_NOTIFICATION_TITLE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SUMMARY_LENGTH,
    DEFAULT_TIMEOUT,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MAX_TIMEOUT,
    MIN_SCAN_INTERVAL,
    MIN_TIMEOUT,
    NOTIFICATION_MODE_DIGEST,
    NOTIFICATION_MODE_INDIVIDUAL,
)
from .feed_client import FeedClient, FeedClientError
from .filters import validate_regex_rules
from .parser import FeedParseError, parse_feed


def _normalize_url(value: str) -> str:
    parts = urlsplit(value.strip())
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError("invalid_url")
    if parts.username or parts.password:
        raise ValueError("credentials_not_supported")
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, "")
    )


def _unique_id(url: str) -> str:
    return sha256(url.encode("utf-8")).hexdigest()


async def _async_validate_feed(
    hass: HomeAssistant, name: str, url: str, timeout: int = DEFAULT_TIMEOUT
) -> None:
    client = FeedClient(async_get_clientsession(hass), timeout)
    result = await client.async_fetch(url)
    if result.content is None:
        raise FeedParseError("Empty response")
    await hass.async_add_executor_job(parse_feed, result.content, name)


def _user_schema(
    defaults: dict[str, Any] | None = None, *, include_send_existing: bool = False
) -> vol.Schema:
    defaults = defaults or {}
    fields: dict[Any, Any] = {
        vol.Required(
            CONF_FEED_NAME, default=defaults.get(CONF_FEED_NAME, "")
        ): selector.TextSelector(),
        vol.Required(
            CONF_FEED_URL, default=defaults.get(CONF_FEED_URL, "")
        ): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
        ),
    }
    if include_send_existing:
        fields[
            vol.Required(
                CONF_SEND_EXISTING,
                default=defaults.get(CONF_SEND_EXISTING, False),
            )
        ] = bool
    return vol.Schema(fields)


class RssParserConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle RSS Parser configuration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add one feed."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                url = _normalize_url(str(user_input[CONF_FEED_URL]))
                await self.async_set_unique_id(_unique_id(url))
                self._abort_if_unique_id_configured()
                await _async_validate_feed(
                    self.hass, str(user_input[CONF_FEED_NAME]), url
                )
            except FeedParseError:
                errors["base"] = "invalid_feed"
            except FeedClientError:
                errors["base"] = "cannot_connect"
            except TimeoutError:
                errors["base"] = "timeout"
            except ValueError as err:
                errors["base"] = str(err)
            except Exception:  # noqa: BLE001 - config flows must show a safe error.
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=str(user_input[CONF_FEED_NAME]),
                    data={
                        CONF_FEED_NAME: str(user_input[CONF_FEED_NAME]).strip(),
                        CONF_FEED_URL: url,
                    },
                    options={
                        CONF_SEND_EXISTING: bool(
                            user_input.get(CONF_SEND_EXISTING, False)
                        )
                    },
                )
        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input, include_send_existing=True),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the feed name or URL."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                url = _normalize_url(str(user_input[CONF_FEED_URL]))
                unique_id = _unique_id(url)
                if any(
                    other.entry_id != entry.entry_id and other.unique_id == unique_id
                    for other in self.hass.config_entries.async_entries(DOMAIN)
                ):
                    return self.async_abort(reason="already_configured")
                await _async_validate_feed(
                    self.hass,
                    str(user_input[CONF_FEED_NAME]),
                    url,
                    int(entry.options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)),
                )
            except FeedParseError:
                errors["base"] = "invalid_feed"
            except FeedClientError:
                errors["base"] = "cannot_connect"
            except TimeoutError:
                errors["base"] = "timeout"
            except ValueError as err:
                errors["base"] = str(err)
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    title=str(user_input[CONF_FEED_NAME]).strip(),
                    unique_id=unique_id,
                    data_updates={
                        CONF_FEED_NAME: str(user_input[CONF_FEED_NAME]).strip(),
                        CONF_FEED_URL: url,
                    },
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_user_schema(user_input or dict(entry.data)),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowWithReload:
        """Return the options flow."""
        return RssParserOptionsFlow()


class RssParserOptionsFlow(OptionsFlowWithReload):
    """Configure polling, filtering, and notifications."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input.get(CONF_USE_REGEX):
                try:
                    validate_regex_rules(
                        user_input.get(CONF_INCLUDE_TERMS),
                        user_input.get(CONF_EXCLUDE_TERMS),
                        user_input.get(CONF_INCLUDE_CATEGORIES),
                        user_input.get(CONF_EXCLUDE_CATEGORIES),
                    )
                except re.error:
                    errors["base"] = "invalid_regex"
            if not errors:
                return self.async_create_entry(data=user_input)

        defaults = dict(self.config_entry.options)
        if user_input:
            defaults.update(user_input)
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                ),
                vol.Required(
                    CONF_TIMEOUT,
                    default=defaults.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
                ): vol.All(
                    vol.Coerce(int), vol.Range(min=MIN_TIMEOUT, max=MAX_TIMEOUT)
                ),
                vol.Required(
                    CONF_SEND_EXISTING,
                    default=defaults.get(CONF_SEND_EXISTING, False),
                ): bool,
                vol.Required(
                    CONF_MAX_ENTRIES,
                    default=defaults.get(CONF_MAX_ENTRIES, DEFAULT_MAX_ENTRIES),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
                vol.Optional(
                    CONF_INCLUDE_TERMS,
                    default=defaults.get(CONF_INCLUDE_TERMS, ""),
                ): selector.TextSelector(selector.TextSelectorConfig(multiline=True)),
                vol.Optional(
                    CONF_EXCLUDE_TERMS,
                    default=defaults.get(CONF_EXCLUDE_TERMS, ""),
                ): selector.TextSelector(selector.TextSelectorConfig(multiline=True)),
                vol.Required(
                    CONF_CASE_SENSITIVE,
                    default=defaults.get(CONF_CASE_SENSITIVE, False),
                ): bool,
                vol.Required(
                    CONF_USE_REGEX, default=defaults.get(CONF_USE_REGEX, False)
                ): bool,
                vol.Required(
                    CONF_MAX_AGE_HOURS,
                    default=defaults.get(CONF_MAX_AGE_HOURS, 0),
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=8760)),
                vol.Optional(
                    CONF_INCLUDE_CATEGORIES,
                    default=defaults.get(CONF_INCLUDE_CATEGORIES, ""),
                ): selector.TextSelector(selector.TextSelectorConfig(multiline=True)),
                vol.Optional(
                    CONF_EXCLUDE_CATEGORIES,
                    default=defaults.get(CONF_EXCLUDE_CATEGORIES, ""),
                ): selector.TextSelector(selector.TextSelectorConfig(multiline=True)),
                vol.Required(
                    CONF_NOTIFICATIONS_ENABLED,
                    default=defaults.get(CONF_NOTIFICATIONS_ENABLED, False),
                ): bool,
                vol.Optional(
                    CONF_NOTIFY_TARGETS,
                    default=defaults.get(CONF_NOTIFY_TARGETS, []),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="notify", multiple=True)
                ),
                vol.Required(
                    CONF_NOTIFICATION_MODE,
                    default=defaults.get(
                        CONF_NOTIFICATION_MODE, NOTIFICATION_MODE_INDIVIDUAL
                    ),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            NOTIFICATION_MODE_INDIVIDUAL,
                            NOTIFICATION_MODE_DIGEST,
                        ],
                        translation_key="notification_mode",
                    )
                ),
                vol.Required(
                    CONF_NOTIFICATION_TITLE,
                    default=defaults.get(
                        CONF_NOTIFICATION_TITLE, DEFAULT_NOTIFICATION_TITLE
                    ),
                ): selector.TextSelector(),
                vol.Required(
                    CONF_NOTIFICATION_MESSAGE,
                    default=defaults.get(
                        CONF_NOTIFICATION_MESSAGE, DEFAULT_NOTIFICATION_MESSAGE
                    ),
                ): selector.TextSelector(selector.TextSelectorConfig(multiline=True)),
                vol.Required(
                    CONF_SUMMARY_LENGTH,
                    default=defaults.get(CONF_SUMMARY_LENGTH, DEFAULT_SUMMARY_LENGTH),
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=5000)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
