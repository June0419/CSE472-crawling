"""Calculate and plot the three required user-network measure distributions."""

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
import networkx as nx
import numpy as np


NETWORK_PATH = ROOT_DIR / "output" / "networks" / "user_network.graphml"
ANALYSIS_DIR = ROOT_DIR / "output" / "analysis"
FIGURE_DIR = ROOT_DIR / "output" / "figures"

INK = "#172033"
GRID = "#dbe3ee"
PURPLE = "#6d28d9"
BLUE = "#2563eb"
ORANGE = "#ea580c"


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _style_axis(axis: plt.Axes) -> None:
    axis.grid(axis="y", color=GRID, linewidth=0.8)
    axis.set_axisbelow(True)
    axis.spines[["top", "right"]].set_visible(False)
    axis.spines[["left", "bottom"]].set_color("#94a3b8")
    axis.tick_params(colors=INK)


def _plot_pagerank(values: list[float], path: Path) -> None:
    positive = np.asarray([value for value in values if value > 0], dtype=float)
    bins = np.geomspace(positive.min() * 0.95, positive.max() * 1.05, 24)
    mean = float(np.mean(positive))
    median = float(np.median(positive))

    figure, axis = plt.subplots(figsize=(10, 6.2), facecolor="white")
    axis.hist(positive, bins=bins, color=PURPLE, alpha=0.9, edgecolor="white")
    axis.axvline(mean, color=ORANGE, linewidth=2, label=f"Mean = {mean:.4f}")
    axis.axvline(
        median,
        color=BLUE,
        linewidth=2,
        linestyle="--",
        label=f"Median = {median:.4f}",
    )
    axis.set_xscale("log")
    axis.set_yscale("log")
    axis.set_title(
        "PageRank Distribution in the User Network",
        fontsize=17,
        fontweight="bold",
        color=INK,
    )
    axis.set_xlabel("PageRank score (log scale)")
    axis.set_ylabel("Number of users (log scale)")
    axis.legend(frameon=False, fontsize=10)
    _style_axis(axis)
    figure.tight_layout()
    figure.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def _plot_degree(values: list[int], top_account: str, path: Path) -> None:
    counts = Counter(values)
    observed = sorted(counts)
    mean = float(np.mean(values))

    figure, axis = plt.subplots(figsize=(10, 6.2), facecolor="white")
    axis.bar(
        observed,
        [counts[value] for value in observed],
        width=0.85,
        color=BLUE,
        alpha=0.9,
    )
    axis.axvline(mean, color=ORANGE, linewidth=2, label=f"Global mean degree = {mean:.2f}")
    axis.set_yscale("log")
    axis.set_title(
        "Degree Distribution and 1-Hop Connectivity",
        fontsize=17,
        fontweight="bold",
        color=INK,
    )
    axis.set_xlabel("Immediate relations per user (degree)")
    axis.set_ylabel("Number of users (log scale)")
    axis.text(
        0.98,
        0.92,
        f"Highest degree: {max(values)}\n@{top_account}",
        transform=axis.transAxes,
        ha="right",
        va="top",
        color=INK,
        fontsize=10,
        bbox={"facecolor": "white", "edgecolor": GRID, "boxstyle": "round,pad=0.5"},
    )
    axis.legend(frameon=False, fontsize=10)
    _style_axis(axis)
    figure.tight_layout()
    figure.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def _plot_betweenness(values: list[float], path: Path) -> None:
    zero_count = sum(value <= 0 for value in values)
    positive = np.asarray([value for value in values if value > 0], dtype=float)
    bins = np.geomspace(positive.min() * 0.95, positive.max() * 1.05, 20)

    figure, axes = plt.subplots(
        1,
        2,
        figsize=(11.5, 5.8),
        facecolor="white",
        gridspec_kw={"width_ratios": [0.9, 2.4]},
    )
    axes[0].bar(
        ["Zero", "Non-zero"],
        [zero_count, len(positive)],
        color=["#cbd5e1", ORANGE],
        width=0.65,
    )
    for index, value in enumerate([zero_count, len(positive)]):
        axes[0].text(index, value + 2, str(value), ha="center", color=INK, fontsize=10)
    axes[0].set_ylabel("Number of users")
    axes[0].set_title("Bridge participation", fontsize=12, color=INK)
    _style_axis(axes[0])

    axes[1].hist(positive, bins=bins, color=ORANGE, alpha=0.9, edgecolor="white")
    axes[1].set_xscale("log")
    axes[1].set_yscale("log")
    axes[1].set_xlabel("Positive betweenness centrality (log scale)")
    axes[1].set_ylabel("Number of users (log scale)")
    axes[1].set_title("Distribution among users that bridge paths", fontsize=12, color=INK)
    _style_axis(axes[1])

    figure.suptitle(
        "Betweenness Centrality Distribution",
        fontsize=17,
        fontweight="bold",
        color=INK,
        y=1.02,
    )
    figure.tight_layout()
    figure.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def _summary(
    rows: list[dict[str, Any]], global_average: float, isolate_count: int
) -> str:
    by_degree = sorted(rows, key=lambda row: (-row["one_hop_relations"], row["account"]))[:5]
    by_pagerank = sorted(rows, key=lambda row: (-row["pagerank"], row["account"]))[:5]
    by_betweenness = sorted(
        rows, key=lambda row: (-row["betweenness_centrality"], row["account"])
    )[:5]

    def ranking(items: list[dict[str, Any]], field: str, digits: int) -> str:
        return "\n".join(
            f"{index}. @{row['account']}: {row[field]:.{digits}f}"
            for index, row in enumerate(items, 1)
        )

    return f"""# User Network Measures

## Measures selected

1. **PageRank** estimates structural influence while considering the importance of connected accounts.
2. **Degree / 1-hop relations** counts each user's immediate distinct interaction partners.
3. **Betweenness centrality** identifies users that lie on shortest paths and may bridge groups.

## Local and global connectivity

- Local level: `user_node_measures.csv` reports `one_hop_relations` for every one of the 200 users.
- Global level: the average number of immediate relations is **{global_average:.2f}**.
- Isolates: **{isolate_count} users** have zero relations in the collected graph.

The degree distribution is strongly right-skewed: most users have few immediate relations, while a small number of hubs connect to many accounts. This explains why the mean exceeds the typical user's degree.

## Highest degree

{ranking(by_degree, 'one_hop_relations', 0)}

## Highest PageRank

{ranking(by_pagerank, 'pagerank', 6)}

## Highest betweenness

{ranking(by_betweenness, 'betweenness_centrality', 6)}

## Interpretation

The PageRank histogram is concentrated at low values with a long upper tail, indicating that structural influence is concentrated in a small set of accounts. Betweenness is even more zero-inflated: many sampled users do not bridge shortest paths, while a few accounts connect otherwise separated parts of the largest interaction component. These measures describe prominence inside the collected sample, not trustworthiness or population-wide influence.
"""


def main() -> None:
    if not NETWORK_PATH.exists():
        raise FileNotFoundError("Run build_networks.py before plotting measures.")
    graph = nx.read_graphml(NETWORK_PATH)
    if graph.is_directed():
        raise ValueError("The user network must be undirected.")

    degree = dict(graph.degree())
    weighted_degree = dict(graph.degree(weight="weight"))
    pagerank = nx.pagerank(graph, weight="weight")
    betweenness = nx.betweenness_centrality(graph, normalized=True, weight=None)
    closeness = nx.closeness_centrality(graph)
    clustering = nx.clustering(graph, weight=None)

    rows: list[dict[str, Any]] = []
    for node, attributes in graph.nodes(data=True):
        rows.append(
            {
                "id": node,
                "account": attributes.get("acct", attributes.get("label", node)),
                "display_name": attributes.get("display_name", ""),
                "seed": int(attributes.get("seed", 0)),
                "one_hop_relations": int(degree[node]),
                "weighted_relations": float(weighted_degree[node]),
                "pagerank": float(pagerank[node]),
                "betweenness_centrality": float(betweenness[node]),
                "closeness_centrality": float(closeness[node]),
                "local_clustering_coefficient": float(clustering[node]),
            }
        )
    rows.sort(key=lambda row: (-row["one_hop_relations"], row["account"]))

    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    _write_csv(ANALYSIS_DIR / "user_node_measures.csv", rows)
    global_average = float(np.mean(list(degree.values())))
    (ANALYSIS_DIR / "user_measures_summary.md").write_text(
        _summary(rows, global_average, nx.number_of_isolates(graph)), encoding="utf-8"
    )

    top_node = max(degree, key=degree.get)
    top_account = graph.nodes[top_node].get(
        "acct", graph.nodes[top_node].get("label", top_node)
    )
    _plot_pagerank(list(pagerank.values()), FIGURE_DIR / "user_pagerank_distribution.png")
    _plot_degree(list(degree.values()), str(top_account), FIGURE_DIR / "user_degree_distribution.png")
    _plot_betweenness(
        list(betweenness.values()), FIGURE_DIR / "user_betweenness_distribution.png"
    )

    print(f"User measures written for {len(rows)} users")
    print(f"Global average 1-hop relations: {global_average:.2f}")
    print(f"Distribution plots saved to {FIGURE_DIR}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(f"User-measure plotting failed: {exc}") from exc
