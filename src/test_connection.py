"""Check that the Mastodon server URL and access token work."""

from __future__ import annotations

from config import load_settings
from mastodon_api import MastodonAPI


def main() -> None:
    settings = load_settings()
    api = MastodonAPI(
        settings.base_url,
        settings.access_token,
        settings.request_delay_seconds,
    )
    account = api.verify_credentials()
    account_name = account.get("acct") or account.get("username") or "unknown"
    print(f"Connection successful: @{account_name} on {settings.base_url}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(f"Connection test failed: {exc}") from exc
