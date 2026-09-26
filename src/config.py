"""Load and validate project settings from the local .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
ENV_FILE = ROOT_DIR / ".env"


def _csv_values(name: str) -> tuple[str, ...]:
    value = os.getenv(name, "")
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _positive_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, but received {raw_value!r}.") from exc
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero.")
    return value


def _nonnegative_float(name: str, default: float) -> float:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, but received {raw_value!r}.") from exc
    if value < 0:
        raise ValueError(f"{name} cannot be negative.")
    return value


@dataclass(frozen=True)
class Settings:
    base_url: str
    access_token: str
    disaster_name: str
    hashtags: tuple[str, ...]
    seed_users: tuple[str, ...]
    target_post_count: int
    target_user_count: int
    request_delay_seconds: float
    user_status_pages_per_hashtag: int
    max_context_requests: int


def load_settings(
    *,
    require_hashtags: bool = False,
    require_seed_users: bool = False,
) -> Settings:
    """Load .env values and validate the values needed by the selected script."""
    load_dotenv(ENV_FILE)

    base_url = os.getenv("MASTODON_BASE_URL", "").strip().rstrip("/")
    access_token = os.getenv("MASTODON_ACCESS_TOKEN", "").strip()
    disaster_name = os.getenv("DISASTER_NAME", "").strip()
    hashtags = tuple(value.lstrip("#") for value in _csv_values("DISASTER_HASHTAGS"))
    seed_users = tuple(value.lstrip("@") for value in _csv_values("SEED_USERS"))

    missing: list[str] = []
    if not base_url:
        missing.append("MASTODON_BASE_URL")
    if not access_token or access_token == "replace_with_your_access_token":
        missing.append("MASTODON_ACCESS_TOKEN")
    if missing:
        raise ValueError(
            "Fill in the following values in .env before running this script: "
            + ", ".join(missing)
        )

    if not base_url.startswith(("https://", "http://")):
        raise ValueError("MASTODON_BASE_URL must start with https:// or http://.")
    if require_hashtags and not hashtags:
        raise ValueError("Add at least one value to DISASTER_HASHTAGS in .env.")
    if require_seed_users and not seed_users:
        raise ValueError("Add at least one account to SEED_USERS in .env.")

    return Settings(
        base_url=base_url,
        access_token=access_token,
        disaster_name=disaster_name or "Unnamed disaster",
        hashtags=hashtags,
        seed_users=seed_users,
        target_post_count=_positive_int("TARGET_POST_COUNT", 500),
        target_user_count=_positive_int("TARGET_USER_COUNT", 200),
        request_delay_seconds=_nonnegative_float("REQUEST_DELAY_SECONDS", 0.5),
        user_status_pages_per_hashtag=_positive_int(
            "USER_STATUS_PAGES_PER_HASHTAG", 2
        ),
        max_context_requests=_positive_int("MAX_CONTEXT_REQUESTS", 100),
    )


def ensure_data_dir() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR
