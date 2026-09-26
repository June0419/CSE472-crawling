"""Collect disaster-related Mastodon posts from several hashtag timelines."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import ensure_data_dir, load_settings
from data_helpers import status_record
from mastodon_api import MastodonAPI


def _post_key(post: dict[str, Any]) -> str:
    return str(post.get("uri") or post.get("id"))


def _merge_post(
    posts: dict[str, dict[str, Any]],
    record: dict[str, Any],
) -> None:
    key = _post_key(record)
    if key not in posts:
        posts[key] = record
        return

    existing = posts[key]
    for field in ("collection_hashtags", "collection_methods"):
        for value in record[field]:
            if value not in existing[field]:
                existing[field].append(value)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_path.replace(path)


def main() -> None:
    settings = load_settings(require_hashtags=True)
    api = MastodonAPI(
        settings.base_url,
        settings.access_token,
        settings.request_delay_seconds,
    )

    posts: dict[str, dict[str, Any]] = {}
    next_pages: dict[str, str | None] = {tag: None for tag in settings.hashtags}
    active_tags = set(settings.hashtags)

    while active_tags and len(posts) < settings.target_post_count:
        for hashtag in settings.hashtags:
            if hashtag not in active_tags or len(posts) >= settings.target_post_count:
                continue

            page, next_url = api.hashtag_page(hashtag, next_pages[hashtag])
            if not page:
                active_tags.discard(hashtag)
                continue

            for raw_status in page:
                record = status_record(raw_status, hashtag)
                _merge_post(posts, record)

                if len(posts) >= settings.target_post_count:
                    break

            next_pages[hashtag] = next_url
            if not next_url:
                active_tags.discard(hashtag)
            print(f"Collected {len(posts)}/{settings.target_post_count} unique posts")

    hashtag_post_count = len(posts)
    context_requests = 0
    context_candidates = sorted(
        posts.values(),
        key=lambda post: int(post.get("replies_count") or 0),
        reverse=True,
    )
    for source_post in context_candidates:
        if context_requests >= settings.max_context_requests:
            break
        if int(source_post.get("replies_count") or 0) <= 0:
            break

        source_hashtag = source_post["collection_hashtags"][0]
        try:
            context = api.status_context(source_post["id"])
        except Exception as exc:
            print(f"Could not load context for status {source_post['id']}: {exc}")
            continue

        context_requests += 1
        for relationship in ("ancestors", "descendants"):
            for raw_status in context[relationship]:
                record = status_record(
                    raw_status,
                    source_hashtag,
                    collection_method=f"context_{relationship}",
                )
                _merge_post(posts, record)

    context_post_count = len(posts) - hashtag_post_count
    if context_requests:
        print(
            f"Added {context_post_count} conversation posts from "
            f"{context_requests} context requests"
        )

    output = {
        "metadata": {
            "disaster_name": settings.disaster_name,
            "source_instance": settings.base_url,
            "hashtags": list(settings.hashtags),
            "requested_count": settings.target_post_count,
            "collected_count": len(posts),
            "hashtag_post_count": hashtag_post_count,
            "context_post_count": context_post_count,
            "context_requests": context_requests,
            "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        },
        "posts": list(posts.values()),
    }
    output_path = ensure_data_dir() / "posts.json"
    _write_json(output_path, output)
    print(f"Saved {len(posts)} posts to {output_path}")

    if len(posts) < settings.target_post_count:
        print(
            "Warning: the configured server did not return enough unique posts. "
            "Add relevant hashtags or use a server that knows more of the event's posts."
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(f"Post collection failed: {exc}") from exc
