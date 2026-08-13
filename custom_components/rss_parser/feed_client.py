"""Asynchronous HTTP client for feeds."""

from __future__ import annotations

from dataclasses import dataclass

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import MAX_RESPONSE_SIZE
from .models import FetchResult


class FeedClientError(Exception):
    """Base error raised while fetching a feed."""


class FeedTooLargeError(FeedClientError):
    """Raised when a response exceeds the configured safety limit."""


@dataclass(slots=True)
class FeedClient:
    """Fetch RSS and Atom documents with conditional requests."""

    session: ClientSession
    timeout_seconds: int

    async def async_fetch(
        self,
        url: str,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> FetchResult:
        """Fetch a feed document."""
        headers = {
            "Accept": (
                "application/atom+xml, application/rss+xml, application/xml, "
                "text/xml;q=0.9, */*;q=0.1"
            )
        }
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified

        try:
            async with self.session.get(
                url,
                headers=headers,
                timeout=ClientTimeout(total=self.timeout_seconds),
            ) as response:
                if response.status == 304:
                    return FetchResult(None, etag, last_modified, not_modified=True)
                response.raise_for_status()
                if (
                    response.content_length
                    and response.content_length > MAX_RESPONSE_SIZE
                ):
                    raise FeedTooLargeError("Feed response is larger than 5 MiB")
                content = await response.content.read(MAX_RESPONSE_SIZE + 1)
                if len(content) > MAX_RESPONSE_SIZE:
                    raise FeedTooLargeError("Feed response is larger than 5 MiB")
                return FetchResult(
                    content=content,
                    etag=response.headers.get("ETag"),
                    last_modified=response.headers.get("Last-Modified"),
                )
        except FeedTooLargeError:
            raise
        except ClientError as err:
            raise FeedClientError(str(err)) from err
