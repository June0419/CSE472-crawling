"""Build a relevant user dataset from seed users and collected disaster posts."""

from __future__ import annotations

import json
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import DATA_DIR, ensure_data_dir, load_settings
from data_helpers import account_record
from mastodon_api import MastodonAPI


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_path.replace(path)


def _load_posts() -> list[dict[str, Any]]:
    path = DATA_DIR / "posts.json"
    if not path.exists():
        raise FileNotFoundError("Run collect_posts.py before collect_users.py.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    posts = payload.get("posts")
    if not isinstance(posts, list):
        raise ValueError("data/posts.json does not contain a valid posts list.")
    return posts


def _blank_user(account_id: str, acct: str = "") -> dict[str, Any]:
    return {
        "id": account_id,
        "username": "",
        "acct": acct,
        "display_name": "",
        "url": None,
        "bot": None,
        "locked": None,
        "followers_count": None,
        "following_count": None,
        "statuses_count": None,
        "seed": False,
        "event_post_count": 0,
        "reply_post_count": 0,
        "mention_received_count": 0,
        "discovery_methods": [],
    }


def _upsert_user(
    users: dict[str, dict[str, Any]],
    account: dict[str, Any],
    *,
    discovery_method: str,
    seed: bool = False,
) -> dict[str, Any] | None:
    account_id = str(account.get("id", ""))
    if not account_id:
        return None

    user = users.setdefault(account_id, _blank_user(account_id))
    incoming = account_record(account, seed=seed)
    for field, value in incoming.items():
        if field == "seed":
            user["seed"] = bool(user["seed"] or value)
        elif value not in (None, ""):
            user[field] = value

    if discovery_method not in user["discovery_methods"]:
        user["discovery_methods"].append(discovery_method)
    return user


def _add_edge(
    edges: dict[tuple[str, str], dict[str, Any]],
    source_id: str,
    target_id: str,
    relationship: str,
    status_id: str,
) -> None:
    if not source_id or not target_id or source_id == target_id:
        return
    first, second = sorted((source_id, target_id))
    key = (first, second)
    edge = edges.setdefault(
        key,
        {
            "source": first,
            "target": second,
            "relationship_types": [],
            "weight": 0,
            "mention_count": 0,
            "reply_count": 0,
            "reblog_count": 0,
            "status_ids": [],
        },
    )
    if relationship not in edge["relationship_types"]:
        edge["relationship_types"].append(relationship)
    edge["weight"] += 1
    edge[f"{relationship}_count"] += 1
    if status_id and status_id not in edge["status_ids"]:
        edge["status_ids"].append(status_id)


def _activity_score(user: dict[str, Any], degree: int) -> int:
    return (
        int(user["event_post_count"])
        + 2 * int(user["reply_post_count"])
        + 2 * int(user["mention_received_count"])
        + degree
    )


def main() -> None:
    settings = load_settings(require_seed_users=True)
    posts = _load_posts()
    api = MastodonAPI(
        settings.base_url,
        settings.access_token,
        settings.request_delay_seconds,
    )

    users: dict[str, dict[str, Any]] = {}
    edges: dict[tuple[str, str], dict[str, Any]] = {}
    posts_by_id = {str(post.get("id", "")): post for post in posts}
    seed_names = {name.lower() for name in settings.seed_users}

    for post in posts:
        status_id = str(post.get("id", ""))
        author = post.get("account") or {}
        author_acct = str(author.get("acct", "")).lower()
        author_id = str(author.get("id", ""))
        author_user = _upsert_user(
            users,
            author,
            discovery_method="event_post_author",
            seed=author_acct in seed_names,
        )
        if author_user:
            author_user["event_post_count"] += 1
            if post.get("in_reply_to_id"):
                author_user["reply_post_count"] += 1
                if "reply_author" not in author_user["discovery_methods"]:
                    author_user["discovery_methods"].append("reply_author")

        for mention in post.get("mentions", []):
            mentioned_user = _upsert_user(
                users,
                mention,
                discovery_method="mentioned_in_event_post",
            )
            if mentioned_user:
                mentioned_user["mention_received_count"] += 1
                _add_edge(
                    edges,
                    author_id,
                    mentioned_user["id"],
                    "mention",
                    status_id,
                )

        parent = posts_by_id.get(str(post.get("in_reply_to_id", "")))
        if parent:
            parent_account = parent.get("account") or {}
            parent_user = _upsert_user(
                users,
                parent_account,
                discovery_method="reply_target",
            )
            if parent_user:
                _add_edge(edges, author_id, parent_user["id"], "reply", status_id)

        if post.get("is_reblog"):
            original_account = post.get("original_account") or {}
            original_user = _upsert_user(
                users,
                original_account,
                discovery_method="reblog_target",
            )
            if original_user:
                _add_edge(edges, author_id, original_user["id"], "reblog", status_id)

    # Refresh seed profiles and ensure every configured seed is included.
    for account_name in settings.seed_users:
        try:
            account = api.lookup_account(account_name)
            seed_user = _upsert_user(
                users,
                account,
                discovery_method="seed",
                seed=True,
            )
            if seed_user:
                print(f"Loaded seed account: @{seed_user['acct']}")
        except Exception as exc:
            print(f"Could not refresh seed account @{account_name}: {exc}")

    adjacency: dict[str, set[str]] = defaultdict(set)
    for source_id, target_id in edges:
        adjacency[source_id].add(target_id)
        adjacency[target_id].add(source_id)

    seed_ids = [user_id for user_id, user in users.items() if user["seed"]]
    queue: deque[str] = deque(seed_ids)
    connected_to_seeds = set(seed_ids)
    while queue:
        source_id = queue.popleft()
        for target_id in adjacency[source_id]:
            if target_id not in connected_to_seeds:
                connected_to_seeds.add(target_id)
                queue.append(target_id)

    def ranking(user_id: str) -> tuple[int, str]:
        user = users[user_id]
        score = _activity_score(user, len(adjacency[user_id]))
        return (-score, str(user.get("acct", "")).lower())

    seed_order = sorted(seed_ids, key=ranking)
    connected_order = sorted(connected_to_seeds - set(seed_ids), key=ranking)
    remaining_order = sorted(set(users) - connected_to_seeds, key=ranking)
    selected_order = (seed_order + connected_order + remaining_order)[
        : settings.target_user_count
    ]
    selected_ids = set(selected_order)

    selected_users: list[dict[str, Any]] = []
    for user_id in selected_order:
        user = users[user_id]
        user["degree_in_collected_graph"] = len(
            adjacency[user_id].intersection(selected_ids)
        )
        user["selection_score"] = _activity_score(
            user,
            user["degree_in_collected_graph"],
        )
        selected_users.append(user)

    selected_edges = [
        edge
        for (source_id, target_id), edge in edges.items()
        if source_id in selected_ids and target_id in selected_ids
    ]

    output = {
        "metadata": {
            "disaster_name": settings.disaster_name,
            "source_instance": settings.base_url,
            "seed_users": list(settings.seed_users),
            "requested_count": settings.target_user_count,
            "collected_count": len(selected_users),
            "candidate_user_count": len(users),
            "users_connected_to_seeds": len(connected_to_seeds),
            "edge_count": len(selected_edges),
            "collected_at_utc": datetime.now(timezone.utc).isoformat(),
            "edge_definition": (
                "An undirected edge connects two users when one mentioned, replied to, "
                "or reblogged the other in the collected Palisades Fire conversation."
            ),
            "selection_method": (
                "Start with relevant seed accounts, expand through mention/reply/reblog "
                "relations, then fill any remaining slots with the most active authors "
                "of verified event posts."
            ),
        },
        "users": selected_users,
        "edges": selected_edges,
    }
    output_path = ensure_data_dir() / "users.json"
    _write_json(output_path, output)
    print(
        f"Saved {len(selected_users)} users and {len(selected_edges)} "
        f"undirected edges to {output_path}"
    )

    if len(selected_users) < settings.target_user_count:
        print(
            "Warning: fewer relevant users were found than requested. "
            "Collect more event posts or add relevant seed accounts."
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(f"User collection failed: {exc}") from exc
