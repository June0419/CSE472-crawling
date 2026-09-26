"""Extract exactly three disaster-related keywords per post with local Llama 3.2."""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import time
from pathlib import Path
from typing import Any

import requests

from config import DATA_DIR, ROOT_DIR


ANALYSIS_DIR = ROOT_DIR / "output" / "analysis"
DEFAULT_OUTPUT = ANALYSIS_DIR / "post_keywords_llm.csv"
PROMPT_PATH = ANALYSIS_DIR / "llm_keyword_prompt.txt"
PROMPT_VERSION = "palisades-keywords-v1"

SYSTEM_PROMPT = """You are a precise content-analysis assistant for a disaster social-media study.
For every Mastodon post, return exactly three distinct, concise English keywords or short phrases that are explicitly supported by the post.

Prioritize disaster-related named events, affected places, hazards, impacts, emergency response, recovery, policy, and community actions. Use 1-3 words per keyword. Expand compressed hashtags and never split a proper name across separate keywords: #PalisadesFire becomes "palisades fire", #EatonFire becomes "eaton fire", and #LosAngeles becomes "los angeles". Do not return isolated fragments such as "los", "angeles", "palisades", "eaton", or the generic word "fire" when the post states a more specific event or place.

Example: a post saying "LA County sues State Farm over wildfire claims #EatonFire #PalisadesFire #insurance" should return ["eaton fire", "palisades fire", "insurance claims"]. A post saying "Palisades Fire burns in Los Angeles during a windstorm" should return ["palisades fire", "los angeles", "windstorm"].

Normalize obvious variants to a consistent form. Ignore URLs, account names, platform terms, engagement requests, timestamps, and non-topical boilerplate. Do not infer sentiment, causes, or facts that the post does not state. Return only data matching the supplied JSON schema."""

KNOWN_FORMS = {
    "palisadesfire": "palisades fire",
    "pacificpalisadesfire": "palisades fire",
    "eatonfire": "eaton fire",
    "losangeles": "los angeles",
    "pacificpalisades": "pacific palisades",
    "palisadesvillage": "palisades village",
    "willrogers": "will rogers",
    "airquality": "air quality",
    "debrisflow": "debris flow",
    "burnscar": "burn scar",
    "wildfires": "wildfire",
}

def _clean_text(value: str, limit: int = 1200) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"@[\w.:-]+", " ", text)
    text = " ".join(text.split())
    return text[:limit]


def _load_posts(limit: int | None = None) -> list[dict[str, str]]:
    payload = json.loads((DATA_DIR / "posts.json").read_text(encoding="utf-8"))
    posts = [
        {"id": str(post["id"]), "text": _clean_text(post.get("content_text", ""))}
        for post in payload.get("posts", [])
        if "hashtag_timeline" in post.get("collection_methods", [])
    ]
    return posts[:limit] if limit else posts


def _schema(batch_size: int) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "posts": {
                "type": "array",
                "minItems": batch_size,
                "maxItems": batch_size,
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "keywords": {
                            "type": "array",
                            "minItems": 3,
                            "maxItems": 3,
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["id", "keywords"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["posts"],
        "additionalProperties": False,
    }


def _normalize_keyword(value: Any) -> str:
    keyword = html.unescape(str(value)).lower().strip()
    keyword = re.sub(r"^[#\-\d.\s]+", "", keyword)
    keyword = re.sub(r"[^a-z0-9\s'-]", " ", keyword)
    keyword = " ".join(keyword.split())
    keyword = KNOWN_FORMS.get(keyword.replace(" ", ""), keyword)
    return " ".join(keyword.split()[:3])


def _validate(response: Any, expected: list[dict[str, str]]) -> list[dict[str, Any]]:
    if not isinstance(response, dict) or not isinstance(response.get("posts"), list):
        raise ValueError("Response does not contain a posts array.")
    expected_ids = [post["id"] for post in expected]
    by_id = {
        str(item.get("id")): item
        for item in response["posts"]
        if isinstance(item, dict)
    }
    if set(by_id) != set(expected_ids):
        raise ValueError("Response post IDs do not match the requested batch.")

    validated: list[dict[str, Any]] = []
    for post in expected:
        raw = by_id[post["id"]].get("keywords")
        if not isinstance(raw, list) or len(raw) != 3:
            raise ValueError(f"Post {post['id']} does not have exactly three keywords.")
        keywords = [_normalize_keyword(value) for value in raw]
        if any(not keyword for keyword in keywords) or len(set(keywords)) != 3:
            raise ValueError(f"Post {post['id']} has empty or duplicate keywords.")
        validated.append({"id": post["id"], "text": post["text"], "keywords": keywords})
    return validated


def _call_ollama(
    base_url: str,
    model: str,
    batch: list[dict[str, str]],
    timeout: int,
    temperature: float = 0,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    user_prompt = (
        "Extract three keywords for every post in this JSON array. Preserve each id exactly.\n\n"
        + json.dumps(batch, ensure_ascii=False)
    )
    request_body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "format": _schema(len(batch)),
        "options": {"temperature": temperature, "top_p": 0.9, "num_predict": 700},
        "keep_alive": "15m",
    }
    response = requests.post(
        f"{base_url.rstrip('/')}/api/chat", json=request_body, timeout=timeout
    )
    response.raise_for_status()
    envelope = response.json()
    parsed = json.loads(envelope.get("message", {}).get("content", ""))
    return _validate(parsed, batch), envelope


def _load_existing(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return {row["post_id"]: row for row in csv.DictReader(stream)}


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "post_id",
        "keyword_1",
        "keyword_2",
        "keyword_3",
        "post_excerpt",
        "model",
        "prompt_version",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _server_ready(base_url: str, model: str) -> None:
    try:
        response = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(
            "Ollama is not reachable. Start Ollama, then rerun this script."
        ) from exc
    names = {item.get("name") for item in response.json().get("models", [])}
    if model not in names and f"{model}:latest" not in names:
        raise RuntimeError(f"Model {model!r} is not installed. Run: ollama pull {model}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=os.getenv("OLLAMA_MODEL", "llama3.2:3b"))
    parser.add_argument(
        "--base-url", default=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if args.batch_size < 1 or args.batch_size > 12:
        raise ValueError("batch-size must be between 1 and 12")
    _server_ready(args.base_url, args.model)
    posts = _load_posts(args.limit)
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    PROMPT_PATH.write_text(SYSTEM_PROMPT + "\n", encoding="utf-8")
    completed = {} if args.overwrite else _load_existing(args.output)
    pending = [post for post in posts if post["id"] not in completed]
    total_duration = 0.0

    for start in range(0, len(pending), args.batch_size):
        batch = pending[start : start + args.batch_size]
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                started = time.perf_counter()
                extracted, envelope = _call_ollama(
                    args.base_url,
                    args.model,
                    batch,
                    args.timeout,
                    temperature=0.1 * (attempt - 1),
                )
                total_duration += time.perf_counter() - started
                for item in extracted:
                    completed[item["id"]] = {
                        "post_id": item["id"],
                        "keyword_1": item["keywords"][0],
                        "keyword_2": item["keywords"][1],
                        "keyword_3": item["keywords"][2],
                        "post_excerpt": item["text"][:500],
                        "model": envelope.get("model", args.model),
                        "prompt_version": PROMPT_VERSION,
                    }
                break
            except (requests.RequestException, json.JSONDecodeError, ValueError) as exc:
                last_error = exc
                if attempt < 3:
                    time.sleep(attempt)
        else:
            if len(batch) > 1:
                for post in batch:
                    single_error: Exception | None = None
                    for single_attempt in range(1, 6):
                        try:
                            extracted, envelope = _call_ollama(
                                args.base_url,
                                args.model,
                                [post],
                                args.timeout,
                                temperature=0.15 * single_attempt,
                            )
                            break
                        except (
                            requests.RequestException,
                            json.JSONDecodeError,
                            ValueError,
                        ) as exc:
                            single_error = exc
                    else:
                        raise RuntimeError(
                            f"Keyword extraction failed for post {post['id']}: {single_error}"
                        ) from single_error
                    item = extracted[0]
                    completed[item["id"]] = {
                        "post_id": item["id"],
                        "keyword_1": item["keywords"][0],
                        "keyword_2": item["keywords"][1],
                        "keyword_3": item["keywords"][2],
                        "post_excerpt": item["text"][:500],
                        "model": envelope.get("model", args.model),
                        "prompt_version": PROMPT_VERSION,
                    }
            else:
                raise RuntimeError(f"Keyword extraction failed: {last_error}") from last_error

        ordered_rows = [completed[post["id"]] for post in posts if post["id"] in completed]
        _write_rows(args.output, ordered_rows)
        print(f"Completed {len(ordered_rows)}/{len(posts)} posts", flush=True)

    if len([post for post in posts if post["id"] in completed]) != len(posts):
        raise RuntimeError("Not every requested post has keyword output.")
    print(f"Saved exactly three LLM keywords for {len(posts)} posts to {args.output}")
    if total_duration:
        print(f"New inference time: {total_duration:.1f} seconds")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(f"LLM keyword extraction failed: {exc}") from exc
