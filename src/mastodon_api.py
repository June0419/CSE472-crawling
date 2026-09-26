"""Small Mastodon REST API client used by the project collectors."""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import quote, urlparse

import requests


class MastodonAPI:
    """Call only the read-only Mastodon endpoints needed by this project."""

    def __init__(self, base_url: str, access_token: str, delay_seconds: float = 0.5):
        self.base_url = base_url.rstrip("/")
        self.delay_seconds = delay_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "User-Agent": "CSE472-Social-Media-Data-Analysis/1.0",
            }
        )

    def _safe_url(self, path_or_url: str) -> str:
        if path_or_url.startswith(("https://", "http://")):
            expected_host = urlparse(self.base_url).netloc.lower()
            actual_host = urlparse(path_or_url).netloc.lower()
            if actual_host != expected_host:
                raise ValueError("Refusing to send the access token to another server.")
            return path_or_url
        return f"{self.base_url}/{path_or_url.lstrip('/')}"

    def get_json(
        self,
        path_or_url: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> tuple[Any, str | None]:
        """Return parsed JSON and the next-page URL from the HTTP Link header."""
        url = self._safe_url(path_or_url)

        for attempt in range(5):
            response = self.session.get(url, params=params, timeout=30)
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "5")
                try:
                    wait_seconds = max(float(retry_after), 1.0)
                except ValueError:
                    wait_seconds = 5.0
                print(f"Rate limited. Waiting {wait_seconds:.1f} seconds...")
                time.sleep(min(wait_seconds, 60.0))
                continue

            if response.status_code in {500, 502, 503, 504} and attempt < 4:
                wait_seconds = float(2**attempt)
                print(
                    f"Mastodon returned {response.status_code}. "
                    f"Retrying in {wait_seconds:.1f} seconds..."
                )
                time.sleep(wait_seconds)
                continue

            response.raise_for_status()
            payload = response.json()
            next_url = response.links.get("next", {}).get("url")
            if self.delay_seconds:
                time.sleep(self.delay_seconds)
            return payload, next_url

        raise RuntimeError("The Mastodon server kept rate limiting the request.")

    def verify_credentials(self) -> dict[str, Any]:
        payload, _ = self.get_json("/api/v1/accounts/verify_credentials")
        if not isinstance(payload, dict):
            raise TypeError("Unexpected response from verify_credentials.")
        return payload

    def hashtag_page(
        self,
        hashtag: str,
        next_url: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        path = next_url or f"/api/v1/timelines/tag/{quote(hashtag, safe='')}"
        params = None if next_url else {"limit": 40}
        payload, new_next_url = self.get_json(path, params=params)
        if not isinstance(payload, list):
            raise TypeError("Unexpected response from the hashtag timeline.")
        return payload, new_next_url

    def lookup_account(self, account_name: str) -> dict[str, Any]:
        payload, _ = self.get_json(
            "/api/v1/accounts/lookup",
            params={"acct": account_name},
        )
        if not isinstance(payload, dict):
            raise TypeError("Unexpected response from account lookup.")
        return payload

    def get_account(self, account_id: str) -> dict[str, Any]:
        payload, _ = self.get_json(f"/api/v1/accounts/{quote(account_id, safe='')}")
        if not isinstance(payload, dict):
            raise TypeError("Unexpected response while loading an account.")
        return payload

    def account_statuses_page(
        self,
        account_id: str,
        hashtag: str,
        next_url: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        path = next_url or f"/api/v1/accounts/{quote(account_id, safe='')}/statuses"
        params = None if next_url else {"limit": 40, "tagged": hashtag}
        payload, new_next_url = self.get_json(path, params=params)
        if not isinstance(payload, list):
            raise TypeError("Unexpected response while loading account statuses.")
        return payload, new_next_url

    def status_context(self, status_id: str) -> dict[str, list[dict[str, Any]]]:
        payload, _ = self.get_json(
            f"/api/v1/statuses/{quote(status_id, safe='')}/context"
        )
        if not isinstance(payload, dict):
            raise TypeError("Unexpected response while loading status context.")
        ancestors = payload.get("ancestors", [])
        descendants = payload.get("descendants", [])
        if not isinstance(ancestors, list) or not isinstance(descendants, list):
            raise TypeError("Unexpected ancestor or descendant data in status context.")
        return {"ancestors": ancestors, "descendants": descendants}
