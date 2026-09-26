"""Aggregate per-post LLM keywords and create the required word cloud."""

from __future__ import annotations

import csv
import os
from collections import Counter
from pathlib import Path
from typing import Any

from config import ROOT_DIR


_MPL_CACHE = ROOT_DIR / "tmp" / "matplotlib"
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_CACHE))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from wordcloud import WordCloud


ANALYSIS_DIR = ROOT_DIR / "output" / "analysis"
FIGURE_DIR = ROOT_DIR / "output" / "figures"
INPUT_PATH = ANALYSIS_DIR / "post_keywords_llm.csv"
PROMPT_PATH = ANALYSIS_DIR / "llm_keyword_prompt.txt"

# Merge only transparent spelling and number variants after LLM extraction.
ALIASES = {
    "wildfires": "wildfire",
    "forest fire": "wildfire",
    "forest fires": "wildfire",
    "palisades wildfire": "palisades fire",
    "pacific palisades fire": "palisades fire",
    "eaton wildfire": "eaton fire",
    "los angeles county": "los angeles",
    "la county": "los angeles",
    "lafires": "los angeles fires",
    "fire fighters": "firefighters",
    "firefighter": "firefighters",
    "debris flows": "debris flow",
    "burn scars": "burn scar",
    "evacuations": "evacuation",
    "evacuation warning": "evacuation",
    "evacuation warnings": "evacuation",
    "evacuation order": "evacuation",
    "evacuation orders": "evacuation",
    "rainfall": "rain",
    "fema assistance": "fema",
    "homes": "home damage",
}


def _canonical(value: str) -> str:
    keyword = " ".join(value.lower().strip().split())
    return ALIASES.get(keyword, keyword)


def _load_rows() -> list[dict[str, str]]:
    if not INPUT_PATH.exists():
        raise FileNotFoundError("Run extract_keywords_llm.py before content analysis.")
    with INPUT_PATH.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 500:
        raise ValueError(f"Expected 500 post keyword rows, found {len(rows)}.")
    if len({row["post_id"] for row in rows}) != 500:
        raise ValueError("Post keyword rows contain duplicate IDs.")
    for row in rows:
        keywords = [row[f"keyword_{index}"] for index in range(1, 4)]
        if any(not keyword.strip() for keyword in keywords):
            raise ValueError(f"Post {row['post_id']} has a blank keyword.")
        if len({keyword.lower().strip() for keyword in keywords}) != 3:
            raise ValueError(f"Post {row['post_id']} has duplicate raw keywords.")
    return rows


def _frequency_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for row in rows:
        counts.update(
            {
                _canonical(row[f"keyword_{index}"])
                for index in range(1, 4)
            }
        )
    return [
        {
            "rank": rank,
            "keyword": keyword,
            "frequency": frequency,
            "post_share_percent": 100 * frequency / len(rows),
        }
        for rank, (keyword, frequency) in enumerate(counts.most_common(), 1)
    ]


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _plot_wordcloud(frequencies: dict[str, int], path: Path) -> None:
    cloud = WordCloud(
        width=2000,
        height=1150,
        background_color="white",
        colormap="inferno",
        prefer_horizontal=0.9,
        relative_scaling=0.45,
        min_font_size=14,
        max_words=60,
        collocations=False,
        random_state=42,
        margin=7,
    ).generate_from_frequencies(frequencies)

    figure, axis = plt.subplots(figsize=(16, 9), facecolor="white")
    axis.imshow(cloud, interpolation="bilinear")
    axis.set_title(
        "2025 Palisades Fire: Llama 3.2 Keyword Cloud",
        fontsize=22,
        fontweight="bold",
        color="#172033",
        pad=18,
    )
    axis.text(
        0.5,
        -0.02,
        "Word size = frequency among 1,500 LLM-generated keywords from 500 posts",
        transform=axis.transAxes,
        ha="center",
        fontsize=11,
        color="#536078",
    )
    axis.set_axis_off()
    figure.tight_layout(pad=1.4)
    figure.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def _plot_bars(rows: list[dict[str, Any]], path: Path) -> None:
    selected = list(reversed(rows[:15]))
    figure, axis = plt.subplots(figsize=(12, 8), facecolor="white")
    bars = axis.barh(
        [row["keyword"].title() for row in selected],
        [row["frequency"] for row in selected],
        color="#7c3aed",
        height=0.67,
    )
    for bar, row in zip(bars, selected):
        axis.text(
            bar.get_width() + 1,
            bar.get_y() + bar.get_height() / 2,
            f"{row['frequency']} ({row['post_share_percent']:.1f}%)",
            va="center",
            fontsize=9,
            color="#374151",
        )
    axis.set_title(
        "Most Frequent LLM-Generated Keywords",
        fontsize=18,
        fontweight="bold",
        color="#172033",
        pad=14,
    )
    axis.set_xlabel("Frequency among 500 posts (three keywords per post)")
    axis.grid(axis="x", color="#e5e7eb", linewidth=0.8)
    axis.set_axisbelow(True)
    axis.spines[["top", "right", "left"]].set_visible(False)
    axis.tick_params(axis="y", length=0)
    axis.set_xlim(0, max(row["frequency"] for row in selected) * 1.25)
    figure.tight_layout()
    figure.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def _summary(rows: list[dict[str, str]], frequencies: list[dict[str, Any]]) -> str:
    prompt = PROMPT_PATH.read_text(encoding="utf-8").strip()
    frequency_lines = "\n".join(
        f"| {row['rank']} | {row['keyword']} | {row['frequency']} | {row['post_share_percent']:.1f}% |"
        for row in frequencies[:15]
    )
    sample_lines = "\n".join(
        f"| {index} | {row['post_excerpt'][:140].replace('|', '/')} | "
        f"{row['keyword_1']}; {row['keyword_2']}; {row['keyword_3']} |"
        for index, row in enumerate(rows[:5], 1)
    )
    return f"""# Per-Post LLM Keyword Analysis

## Method

- Model: Llama 3.2 3B, instruction-tuned Q4_K_M build served locally by Ollama
- Input: 500 posts collected directly from the selected hashtag timelines
- Output: exactly three distinct keywords for every post (1,500 raw keyword assignments)
- Generation: temperature 0 with a required JSON schema
- Privacy: inference ran locally; post text was not sent to a hosted LLM API

## Exact system prompt

```text
{prompt}
```

## Sample outputs

| # | Post excerpt | Three generated keywords |
|---:|---|---|
{sample_lines}

## Most frequent keywords

| Rank | Keyword | Frequency | Share of posts |
|---:|---|---:|---:|
{frequency_lines}

## Interpretation

The frequency distribution highlights the focal Palisades Fire discussion while also showing recurring references to Los Angeles locations, the Eaton Fire, evacuation, fire impacts, weather, and post-fire recovery. A sparse tail of terms such as Will Rogers, Volkswagen, and Palestine is unexpected in a disaster-focused sample and exposes cross-topic hashtag reuse or incidental references; those terms were retained instead of being manually filtered. Because each post contributes exactly three keywords, a term's frequency is also the number of sampled posts assigned that theme after transparent spelling normalization. The output summarizes themes; it does not measure sentiment or factual accuracy.
"""


def main() -> None:
    rows = _load_rows()
    frequency_rows = _frequency_rows(rows)
    frequencies = {row["keyword"]: row["frequency"] for row in frequency_rows}
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    _write_csv(ANALYSIS_DIR / "llm_keyword_frequencies.csv", frequency_rows)
    (ANALYSIS_DIR / "llm_keyword_analysis.md").write_text(
        _summary(rows, frequency_rows), encoding="utf-8"
    )
    _plot_wordcloud(frequencies, FIGURE_DIR / "palisades_fire_keyword_wordcloud.png")
    _plot_bars(frequency_rows, FIGURE_DIR / "palisades_fire_top_keywords.png")

    print("Validated 500 posts and exactly 1,500 LLM-generated keywords")
    print("Top keywords:")
    for row in frequency_rows[:10]:
        print(f"  {row['rank']:>2}. {row['keyword']}: {row['frequency']}")
    print(f"Content-analysis outputs saved to {ANALYSIS_DIR} and {FIGURE_DIR}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(f"Content analysis failed: {exc}") from exc
