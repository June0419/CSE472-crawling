"""Create a reproducible LLM-assisted keyword analysis and report figures."""

from __future__ import annotations

import csv
import html
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any

from config import DATA_DIR, ROOT_DIR


_MPL_CACHE = ROOT_DIR / "tmp" / "matplotlib"
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_CACHE))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from wordcloud import WordCloud


ANALYSIS_DIR = ROOT_DIR / "output" / "analysis"
FIGURE_DIR = ROOT_DIR / "output" / "figures"

# The semantic groups were selected in an OpenAI Codex (GPT-5) review of the
# frequency-ranked terms and bigrams. Explicit patterns make the final counts
# auditable and reproducible without sending the dataset to another API.
CONCEPTS: dict[str, dict[str, Any]] = {
    "Palisades Fire": {
        "group": "event",
        "patterns": [r"\bpalisades\s+fire\b", r"\bpalisadesfire\b"],
        "rationale": "Direct references to the focal disaster.",
    },
    "Eaton Fire": {
        "group": "event",
        "patterns": [r"\beaton\s+fire\b", r"\beatonfire\b"],
        "rationale": "A second Los Angeles fire frequently discussed alongside the focal event.",
    },
    "Pacific Palisades": {
        "group": "place",
        "patterns": [r"\bpacific\s+palisades\b", r"\bpacificpalisades\b"],
        "rationale": "The neighborhood at the center of the event.",
    },
    "Los Angeles": {
        "group": "place",
        "patterns": [
            r"\blos\s+angeles\b",
            r"\blosangeles\b",
            r"\bla\s+county\b",
            r"\blacounty\b",
        ],
        "rationale": "Regional references connecting the fire to Los Angeles.",
    },
    "California": {
        "group": "place",
        "patterns": [r"\bcalifornia\b", r"\bcalfire\b"],
        "rationale": "State-level location and response references.",
    },
    "Malibu": {
        "group": "place",
        "patterns": [r"\bmalibu\b"],
        "rationale": "Nearby community repeatedly discussed in the sample.",
    },
    "Wildfire": {
        "group": "hazard",
        "patterns": [r"\bwildfires?\b", r"\bwildfireseason\b"],
        "rationale": "Broader hazard framing beyond the event name.",
    },
    "Rain & Storm": {
        "group": "hazard",
        "patterns": [r"\brain(?:fall|fall)?\b", r"\bstorms?\b"],
        "rationale": "Post-fire weather conditions discussed in the sample.",
    },
    "Debris Flow & Flooding": {
        "group": "hazard",
        "patterns": [
            r"\bdebris\s+flows?\b",
            r"\bmudslides?\b",
            r"\bflood(?:s|ed|ing)?\b",
            r"\bflash\s+floods?\b",
        ],
        "rationale": "Secondary hazards affecting burned areas.",
    },
    "Burn Scar": {
        "group": "hazard",
        "patterns": [r"\bburn\s+scars?\b", r"\bburned\s+areas?\b"],
        "rationale": "Fire-damaged terrain vulnerable to later hazards.",
    },
    "Evacuation": {
        "group": "response",
        "patterns": [r"\bevacuat(?:e|ed|es|ing|ion|ions)\b"],
        "rationale": "Movement and safety instructions during the emergency.",
    },
    "Firefighters": {
        "group": "response",
        "patterns": [r"\bfirefighters?\b", r"\bfire\s+crews?\b"],
        "rationale": "Front-line emergency personnel.",
    },
    "Emergency Response": {
        "group": "response",
        "patterns": [
            r"\bemergency\s+response\b",
            r"\bfirst\s+responders?\b",
            r"\bemergency\s+services?\b",
        ],
        "rationale": "Coordinated response and emergency-service discussion.",
    },
    "Containment & Acres": {
        "group": "response",
        "patterns": [r"\bcontainment\b", r"\bacres?\b"],
        "rationale": "Operational fire-size and containment updates.",
    },
    "Damage & Loss": {
        "group": "impact",
        "patterns": [
            r"\bdamag(?:e|ed|es)\b",
            r"\bdestroy(?:ed|s|ing)\b",
            r"\bdestruction\b",
            r"\bloss(?:es)?\b",
        ],
        "rationale": "Descriptions of physical and personal losses.",
    },
    "Homes & Property": {
        "group": "impact",
        "patterns": [
            r"\bhomes?\b",
            r"\bproperties?\b",
            r"\bbuildings?\b",
            r"\bresidences?\b",
        ],
        "rationale": "Built-environment impacts in affected communities.",
    },
    "Smoke & Air Quality": {
        "group": "impact",
        "patterns": [r"\bsmoke\b", r"\bair\s+quality\b"],
        "rationale": "Environmental and health-related fire impacts.",
    },
    "Recovery & Rebuilding": {
        "group": "recovery",
        "patterns": [
            r"\brecover(?:y|ies|ed|ing)?\b",
            r"\brebuild(?:s|ing|able)?\b",
            r"\breconstruction\b",
        ],
        "rationale": "Longer-term recovery after the immediate disaster.",
    },
    "Insurance": {
        "group": "recovery",
        "patterns": [r"\binsurance\b", r"\binsurers?\b", r"\binsured\b"],
        "rationale": "Financial recovery and coverage concerns.",
    },
    "Community Support": {
        "group": "community",
        "patterns": [
            r"\bcommunity\s+support\b",
            r"\bdonat(?:e|ed|es|ing|ion|ions)\b",
            r"\bfundrais(?:er|ers|ing)\b",
            r"\brelief\s+fund\b",
        ],
        "rationale": "Mutual aid, donations, and organized support.",
    },
    "Climate Change": {
        "group": "cause & policy",
        "patterns": [
            r"\bclimate\s+change\b",
            r"\bclimate\s+crisis\b",
            r"\bglobal\s+warming\b",
        ],
        "rationale": "Climate-related interpretation of wildfire risk.",
    },
    "Government & FEMA": {
        "group": "cause & policy",
        "patterns": [
            r"\bfema\b",
            r"\bgovernment\b",
            r"\bgovernor\b",
            r"\bmayor\b",
        ],
        "rationale": "Public institutions, officials, and recovery policy.",
    },
    "Investigation & Arson": {
        "group": "cause & policy",
        "patterns": [
            r"\barson\b",
            r"\binvestigat(?:e|ed|es|ing|ion|ions)\b",
            r"\bcause\s+of\s+the\s+fire\b",
        ],
        "rationale": "Discussion of the fire's origin and investigation.",
    },
}

STOPWORDS = set(
    """
    a about above after again against all am an and any are aren't as at be because
    been before being below between both but by can can't cannot could couldn't did
    didn't do does doesn't doing don't down during each few for from further had
    hadn't has hasn't have haven't having he he'd he'll he's her here here's hers
    herself him himself his how how's i i'd i'll i'm i've if in into is isn't it it's
    its itself just let's me more most mustn't my myself no nor not of off on once
    only or other ought our ours ourselves out over own same shan't she she'd she'll
    she's should shouldn't so some such than that that's the their theirs them
    themselves then there there's these they they'd they'll they're they've this
    those through to too under until up very was wasn't we we'd we'll we're we've
    were weren't what what's when when's where where's which while who who's whom
    why why's will with won't would wouldn't you you'd you'll you're you've your yours
    yourself yourselves http https www com org amp mastodon social
    """.split()
)


def _load_posts() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    path = DATA_DIR / "posts.json"
    if not path.exists():
        raise FileNotFoundError("Run collect_posts.py before content analysis.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    # Context replies are collected to complete network edges. Keyword popularity
    # uses the requested 500 hashtag-timeline posts so replies do not bias results.
    posts = [
        post
        for post in payload.get("posts", [])
        if "hashtag_timeline" in post.get("collection_methods", [])
    ]
    if not posts:
        raise ValueError("No hashtag-timeline posts were found.")
    return payload.get("metadata", {}), posts


def _clean_text(value: str) -> str:
    text = html.unescape(value or "").lower()
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"@[\w.:-]+", " ", text)
    text = text.replace("’", "'")
    return " ".join(text.split())


def _tokens(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z][a-z'-]{2,}", text)
        if token not in STOPWORDS and not token.startswith("http")
    ]


def _candidate_counts(texts: list[str]) -> tuple[Counter[str], Counter[str]]:
    terms: Counter[str] = Counter()
    bigrams: Counter[str] = Counter()
    for text in texts:
        tokens = _tokens(text)
        terms.update(tokens)
        bigrams.update(" ".join(pair) for pair in zip(tokens, tokens[1:]))
    return terms, bigrams


def _concept_rows(texts: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for keyword, definition in CONCEPTS.items():
        compiled = [re.compile(pattern, re.IGNORECASE) for pattern in definition["patterns"]]
        support = sum(any(pattern.search(text) for pattern in compiled) for text in texts)
        rows.append(
            {
                "keyword": keyword,
                "post_count": support,
                "post_share_percent": 100 * support / len(texts),
                "semantic_group": definition["group"],
                "matched_patterns": " | ".join(definition["patterns"]),
                "rationale": definition["rationale"],
            }
        )
    rows.sort(key=lambda row: (-row["post_count"], row["keyword"]))
    for index, row in enumerate(rows, 1):
        row["rank"] = index
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames = ["rank", *[key for key in rows[0] if key != "rank"]]
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _candidate_rows(counter: Counter[str], limit: int = 100) -> list[dict[str, Any]]:
    return [
        {"rank": index, "candidate": candidate, "occurrences": occurrences}
        for index, (candidate, occurrences) in enumerate(counter.most_common(limit), 1)
    ]


def _plot_wordcloud(rows: list[dict[str, Any]], path: Path, post_count: int) -> None:
    frequencies = {
        row["keyword"]: row["post_count"]
        for row in rows
        if row["post_count"] > 0
    }
    cloud = WordCloud(
        width=2000,
        height=1150,
        background_color="white",
        colormap="inferno",
        prefer_horizontal=0.9,
        relative_scaling=0.5,
        min_font_size=18,
        max_words=18,
        collocations=False,
        random_state=42,
        margin=8,
    ).generate_from_frequencies(frequencies)

    figure, axis = plt.subplots(figsize=(16, 9), facecolor="white")
    axis.imshow(cloud, interpolation="bilinear")
    axis.set_title(
        "2025 Palisades Fire: LLM-Assisted Keyword Themes",
        fontsize=22,
        fontweight="bold",
        color="#172033",
        pad=18,
    )
    axis.text(
        0.5,
        -0.02,
        f"Word size = number of matching posts in the {post_count}-post hashtag sample",
        transform=axis.transAxes,
        ha="center",
        fontsize=11,
        color="#536078",
    )
    axis.set_axis_off()
    figure.tight_layout(pad=1.4)
    figure.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def _plot_bars(rows: list[dict[str, Any]], path: Path, post_count: int) -> None:
    selected = [row for row in rows[:15] if row["post_count"] > 0]
    selected.reverse()
    colors = {
        "event": "#7c3aed",
        "place": "#2563eb",
        "hazard": "#dc2626",
        "response": "#ea580c",
        "impact": "#ca8a04",
        "recovery": "#059669",
        "community": "#0891b2",
        "cause & policy": "#4f46e5",
    }
    figure, axis = plt.subplots(figsize=(12, 8), facecolor="white")
    bars = axis.barh(
        [row["keyword"] for row in selected],
        [row["post_count"] for row in selected],
        color=[colors[row["semantic_group"]] for row in selected],
        height=0.67,
    )
    for bar, row in zip(bars, selected):
        axis.text(
            bar.get_width() + max(1, post_count * 0.006),
            bar.get_y() + bar.get_height() / 2,
            f"{row['post_count']} ({row['post_share_percent']:.1f}%)",
            va="center",
            fontsize=9,
            color="#374151",
        )
    axis.set_title(
        "Top Keyword Themes in Palisades Fire Posts",
        fontsize=18,
        fontweight="bold",
        color="#172033",
        pad=14,
    )
    axis.set_xlabel(f"Posts containing theme (n = {post_count})")
    axis.grid(axis="x", color="#e5e7eb", linewidth=0.8)
    axis.set_axisbelow(True)
    axis.spines[["top", "right", "left"]].set_visible(False)
    axis.tick_params(axis="y", length=0)
    max_value = max(row["post_count"] for row in selected)
    axis.set_xlim(0, max_value * 1.28)
    figure.tight_layout()
    figure.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def _analysis_markdown(
    metadata: dict[str, Any], rows: list[dict[str, Any]], post_count: int
) -> str:
    table_lines = "\n".join(
        f"| {row['rank']} | {row['keyword']} | {row['post_count']} | "
        f"{row['post_share_percent']:.1f}% | {row['semantic_group']} |"
        for row in rows[:15]
    )
    return f"""# LLM-Assisted Keyword Analysis

## Scope

- Disaster: {metadata.get('disaster_name', '2025 Palisades Fire')}
- Source instance: {metadata.get('source_instance', 'mastodon.social')}
- Analysis sample: {post_count} posts collected directly from the selected hashtag timelines
- Context-only replies were excluded from keyword frequency so they do not change the requested post sample.

## LLM prompt and procedure

**Model used:** OpenAI Codex (GPT-5), in the project-development session.

**Prompt:** “Review the frequency-ranked unigrams and bigrams from public Mastodon posts about the 2025 Palisades Fire. Merge surface variants into clear disaster-related concepts, remove URL/platform artifacts, and retain interpretable themes covering the event, places, impacts, response, recovery, community, and policy. Do not infer sentiment or facts that are not present in the text. For every concept, provide transparent matching variants so its support can be counted reproducibly.”

The LLM was used for semantic grouping, not for inventing counts. `src/analyze_content.py` records each concept's regular-expression patterns and counts how many distinct posts contain at least one pattern. This lets the result be audited and rerun.

## Top themes

| Rank | Keyword/theme | Matching posts | Share | Group |
|---:|---|---:|---:|---|
{table_lines}

## Interpretation

The largest themes show what the collected posts mention most often; they do not measure approval, sentiment, or causal importance. Counts can overlap because one post may mention several themes. Results apply only to the collected public posts visible through the selected Mastodon instance and hashtags.
"""


def main() -> None:
    metadata, posts = _load_posts()
    texts = [_clean_text(post.get("content_text", "")) for post in posts]
    term_counts, bigram_counts = _candidate_counts(texts)
    concept_rows = _concept_rows(texts)

    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    _write_csv(ANALYSIS_DIR / "top_keywords.csv", concept_rows)
    _write_csv(
        ANALYSIS_DIR / "candidate_unigrams.csv", _candidate_rows(term_counts)
    )
    _write_csv(
        ANALYSIS_DIR / "candidate_bigrams.csv", _candidate_rows(bigram_counts)
    )
    (ANALYSIS_DIR / "llm_keyword_analysis.md").write_text(
        _analysis_markdown(metadata, concept_rows, len(posts)), encoding="utf-8"
    )
    (ANALYSIS_DIR / "keyword_analysis.json").write_text(
        json.dumps(
            {
                "metadata": {
                    "disaster_name": metadata.get("disaster_name"),
                    "source_instance": metadata.get("source_instance"),
                    "analyzed_post_count": len(posts),
                    "selection": "posts collected directly from hashtag timelines",
                    "context_posts_excluded": True,
                    "llm_role": "semantic grouping of frequency-ranked candidates",
                    "llm_model": "OpenAI Codex (GPT-5)",
                },
                "keywords": concept_rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    _plot_wordcloud(
        concept_rows,
        FIGURE_DIR / "palisades_fire_keyword_wordcloud.png",
        len(posts),
    )
    _plot_bars(
        concept_rows,
        FIGURE_DIR / "palisades_fire_top_keywords.png",
        len(posts),
    )

    print(f"Analyzed {len(posts)} hashtag-timeline posts")
    print("Top themes:")
    for row in concept_rows[:10]:
        print(
            f"  {row['rank']:>2}. {row['keyword']}: "
            f"{row['post_count']} posts ({row['post_share_percent']:.1f}%)"
        )
    print(f"Analysis files saved to {ANALYSIS_DIR}")
    print(f"Figures saved to {FIGURE_DIR}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(f"Content analysis failed: {exc}") from exc
