"""Transform Mastodon API objects into compact, analysis-ready records."""

from __future__ import annotations

import html
from html.parser import HTMLParser
from typing import Any


class _PlainTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"br", "p"} and self.parts and not self.parts[-1].endswith(" "):
            self.parts.append(" ")

    def text(self) -> str:
        return " ".join("".join(self.parts).split())


def html_to_text(value: str | None) -> str:
    parser = _PlainTextParser()
    parser.feed(value or "")
    return html.unescape(parser.text())


def account_record(account: dict[str, Any], *, seed: bool = False) -> dict[str, Any]:
    return {
        "id": str(account.get("id", "")),
        "username": account.get("username", ""),
        "acct": account.get("acct", ""),
        "display_name": account.get("display_name", ""),
        "url": account.get("url"),
        "bot": account.get("bot", False),
        "locked": account.get("locked", False),
        "followers_count": account.get("followers_count"),
        "following_count": account.get("following_count"),
        "statuses_count": account.get("statuses_count"),
        "seed": seed,
    }


def status_record(
    status: dict[str, Any],
    source_hashtag: str,
    collection_method: str = "hashtag_timeline",
) -> dict[str, Any]:
    boosted_status = status.get("reblog")
    content_status = boosted_status if isinstance(boosted_status, dict) else status
    author = status.get("account") or {}
    original_author = content_status.get("account") or {}

    return {
        "id": str(status.get("id", "")),
        "uri": status.get("uri"),
        "url": status.get("url"),
        "created_at": status.get("created_at"),
        "language": content_status.get("language"),
        "visibility": status.get("visibility"),
        "content_html": content_status.get("content", ""),
        "content_text": html_to_text(content_status.get("content")),
        "account": account_record(author),
        "original_account": account_record(original_author),
        "in_reply_to_id": content_status.get("in_reply_to_id"),
        "in_reply_to_account_id": content_status.get("in_reply_to_account_id"),
        "is_reblog": isinstance(boosted_status, dict),
        "reblog_of_id": (
            str(content_status.get("id", "")) if isinstance(boosted_status, dict) else None
        ),
        "mentions": [
            {
                "id": str(mention.get("id", "")),
                "username": mention.get("username", ""),
                "acct": mention.get("acct", ""),
                "url": mention.get("url"),
            }
            for mention in content_status.get("mentions", [])
        ],
        "tags": [tag.get("name", "") for tag in content_status.get("tags", [])],
        "replies_count": content_status.get("replies_count", 0),
        "reblogs_count": content_status.get("reblogs_count", 0),
        "favourites_count": content_status.get("favourites_count", 0),
        "collection_hashtags": [source_hashtag],
        "collection_methods": [collection_method],
    }
