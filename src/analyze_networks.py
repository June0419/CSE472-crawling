"""Calculate report-ready statistics and centrality rankings for both networks."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any, Callable

import networkx as nx

from config import ROOT_DIR


NETWORK_DIR = ROOT_DIR / "output" / "networks"
ANALYSIS_DIR = ROOT_DIR / "output" / "analysis"


def _finite(value: Any) -> float | int | None:
    """Convert NetworkX numeric output to JSON-safe Python values."""
    if isinstance(value, bool):
        return int(value)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return int(number) if number.is_integer() else number


def _safe_metric(function: Callable[[], Any]) -> float | int | None:
    try:
        return _finite(function())
    except (nx.NetworkXError, ZeroDivisionError, ValueError):
        return None


def _average_degree(graph: nx.Graph) -> float:
    if graph.number_of_nodes() == 0:
        return 0.0
    return sum(dict(graph.degree()).values()) / graph.number_of_nodes()


def _largest_component(graph: nx.Graph) -> nx.Graph:
    if graph.number_of_nodes() == 0:
        return graph.copy()
    component_nodes = (
        max(nx.weakly_connected_components(graph), key=len)
        if graph.is_directed()
        else max(nx.connected_components(graph), key=len)
    )
    return graph.subgraph(component_nodes).copy()


def _rank(scores: dict[str, float | int]) -> dict[str, int]:
    ordered = sorted(scores, key=lambda node: (-float(scores[node]), str(node)))
    return {node: index + 1 for index, node in enumerate(ordered)}


def _base_metrics(graph: nx.Graph) -> dict[str, float | int | None]:
    largest = _largest_component(graph)
    largest_undirected = largest.to_undirected()
    components = (
        list(nx.weakly_connected_components(graph))
        if graph.is_directed()
        else list(nx.connected_components(graph))
    )
    undirected = graph.to_undirected()
    nodes = graph.number_of_nodes()
    largest_size = largest.number_of_nodes()
    return {
        "nodes": nodes,
        "edges": graph.number_of_edges(),
        "average_degree": _average_degree(graph),
        "density": nx.density(graph),
        "isolates": nx.number_of_isolates(graph),
        "components": len(components),
        "largest_component_nodes": largest_size,
        "largest_component_share": largest_size / nodes if nodes else 0.0,
        "average_clustering": _safe_metric(
            lambda: nx.average_clustering(undirected, weight=None)
        ),
        "transitivity": _safe_metric(lambda: nx.transitivity(undirected)),
        "degree_assortativity": _safe_metric(
            lambda: nx.degree_assortativity_coefficient(undirected)
        ),
        "largest_component_average_shortest_path": _safe_metric(
            lambda: nx.average_shortest_path_length(largest_undirected)
        ),
        "largest_component_diameter": _safe_metric(
            lambda: nx.diameter(largest_undirected)
        ),
    }


def _information_analysis(graph: nx.DiGraph) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    metrics = _base_metrics(graph)
    metrics.update(
        {
            "component_type": "weakly connected",
            "strongly_connected_components": nx.number_strongly_connected_components(
                graph
            ),
            "reciprocity": _safe_metric(lambda: nx.reciprocity(graph)),
        }
    )

    degree = dict(graph.degree())
    in_degree = dict(graph.in_degree())
    out_degree = dict(graph.out_degree())
    pagerank = nx.pagerank(graph, weight="weight")
    betweenness = nx.betweenness_centrality(graph, normalized=True, weight=None)
    # NetworkX directed closeness follows incoming paths. Reversing gives outward
    # reach from a parent/original post toward its replies and descendants.
    outward_closeness = nx.closeness_centrality(graph.reverse(copy=False))
    ranks = {
        "degree": _rank(degree),
        "pagerank": _rank(pagerank),
        "betweenness": _rank(betweenness),
    }

    rows: list[dict[str, Any]] = []
    for node, attributes in graph.nodes(data=True):
        rows.append(
            {
                "id": node,
                "account": attributes.get("account", ""),
                "created_at": attributes.get("created_at", ""),
                "content": attributes.get("content", ""),
                "degree": degree[node],
                "in_degree": in_degree[node],
                "out_degree": out_degree[node],
                "pagerank": pagerank[node],
                "betweenness_centrality": betweenness[node],
                "outward_closeness_centrality": outward_closeness[node],
                "degree_rank": ranks["degree"][node],
                "pagerank_rank": ranks["pagerank"][node],
                "betweenness_rank": ranks["betweenness"][node],
                "best_rank": min(
                    ranks["degree"][node],
                    ranks["pagerank"][node],
                    ranks["betweenness"][node],
                ),
            }
        )
    rows.sort(
        key=lambda row: (
            row["best_rank"],
            row["degree_rank"],
            row["pagerank_rank"],
            str(row["id"]),
        )
    )
    return metrics, rows[:30]


def _user_analysis(graph: nx.Graph) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    metrics = _base_metrics(graph)
    communities = nx.community.louvain_communities(graph, weight="weight", seed=42)
    metrics.update(
        {
            "component_type": "connected",
            "communities_louvain": len(communities),
            "modularity_louvain": _safe_metric(
                lambda: nx.community.modularity(graph, communities, weight="weight")
            ),
        }
    )

    degree = dict(graph.degree())
    weighted_degree = dict(graph.degree(weight="weight"))
    degree_centrality = nx.degree_centrality(graph)
    pagerank = nx.pagerank(graph, weight="weight")
    betweenness = nx.betweenness_centrality(graph, normalized=True, weight=None)
    closeness = nx.closeness_centrality(graph)
    ranks = {
        "degree": _rank(degree),
        "pagerank": _rank(pagerank),
        "betweenness": _rank(betweenness),
    }

    rows: list[dict[str, Any]] = []
    for node, attributes in graph.nodes(data=True):
        rows.append(
            {
                "id": node,
                "account": attributes.get("acct", attributes.get("label", "")),
                "display_name": attributes.get("display_name", ""),
                "seed": int(attributes.get("seed", 0)),
                "event_post_count": int(attributes.get("event_post_count", 0)),
                "degree": degree[node],
                "weighted_degree": weighted_degree[node],
                "degree_centrality": degree_centrality[node],
                "pagerank": pagerank[node],
                "betweenness_centrality": betweenness[node],
                "closeness_centrality": closeness[node],
                "degree_rank": ranks["degree"][node],
                "pagerank_rank": ranks["pagerank"][node],
                "betweenness_rank": ranks["betweenness"][node],
                "best_rank": min(
                    ranks["degree"][node],
                    ranks["pagerank"][node],
                    ranks["betweenness"][node],
                ),
            }
        )
    rows.sort(
        key=lambda row: (
            row["best_rank"],
            row["degree_rank"],
            row["pagerank_rank"],
            str(row["id"]),
        )
    )
    return metrics, rows[:30]


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _metrics_rows(results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    notes = {
        "components": "weakly connected for information; connected for users",
        "largest_component_average_shortest_path": "largest component only; direction ignored for information network",
        "largest_component_diameter": "largest component only; direction ignored for information network",
        "degree_assortativity": "degree correlation across connected node pairs",
        "modularity_louvain": "weighted Louvain communities, seed=42",
    }
    return [
        {
            "network": network,
            "metric": metric,
            "value": "" if value is None else value,
            "note": notes.get(metric, ""),
        }
        for network, metrics in results.items()
        for metric, value in metrics.items()
        if metric != "component_type"
    ]


def _format(value: Any, digits: int = 4) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _summary_markdown(
    info: dict[str, Any],
    users: dict[str, Any],
    info_nodes: list[dict[str, Any]],
    user_nodes: list[dict[str, Any]],
) -> str:
    top_posts = sorted(info_nodes, key=lambda row: row["degree_rank"])[:5]
    top_users = sorted(user_nodes, key=lambda row: row["degree_rank"])[:5]
    post_lines = "\n".join(
        f"{index}. @{row['account']} — degree {row['degree']} "
        f"(in {row['in_degree']}, out {row['out_degree']})"
        for index, row in enumerate(top_posts, 1)
    )
    user_lines = "\n".join(
        f"{index}. @{row['account']} — degree {row['degree']}, "
        f"weighted degree {_format(row['weighted_degree'], 0)}"
        for index, row in enumerate(top_users, 1)
    )
    return f"""# Network Analysis Summary

## Information diffusion network

- Nodes: {info['nodes']:,}; directed edges: {info['edges']:,}
- Density: {_format(info['density'], 6)}; average degree: {_format(info['average_degree'])}
- Weak components: {info['components']:,}; isolates: {info['isolates']:,}
- Largest weak component: {info['largest_component_nodes']:,} nodes ({info['largest_component_share']:.1%})
- Largest-component average path length: {_format(info['largest_component_average_shortest_path'])}; diameter: {_format(info['largest_component_diameter'], 0)}

The low density and the large number of isolates/components indicate that the collected discussion is fragmented rather than one continuous repost cascade. Because the edge is defined as parent/original post → reply/reblog, out-degree represents direct downstream responses in this sample.

### Highest-degree posts

{post_lines}

## User interaction network

- Nodes: {users['nodes']:,}; undirected edges: {users['edges']:,}
- Density: {_format(users['density'], 6)}; average degree: {_format(users['average_degree'])}
- Connected components: {users['components']:,}; isolates: {users['isolates']:,}
- Largest component: {users['largest_component_nodes']:,} nodes ({users['largest_component_share']:.1%})
- Average clustering coefficient: {_format(users['average_clustering'])}
- Louvain communities: {users['communities_louvain']}; modularity: {_format(users['modularity_louvain'])}
- Largest-component average path length: {_format(users['largest_component_average_shortest_path'])}; diameter: {_format(users['largest_component_diameter'], 0)}

The user graph is still sparse, but its largest component contains a majority of sampled users. High modularity means interactions are organized into distinguishable clusters. Degree shows how many different sampled users an account interacted with; weighted degree also counts repeated interactions.

### Highest-degree users

{user_lines}

## Interpretation limits

These statistics describe the posts visible to `mastodon.social` under the selected hashtags and seed-user expansion. They are not estimates of all Mastodon activity or of the public as a whole. Path length and diameter are reported only for the largest component because the full graphs are disconnected. Centrality identifies structural prominence in this sample, not credibility or real-world influence.
"""


def main() -> None:
    info_path = NETWORK_DIR / "information_diffusion.graphml"
    user_path = NETWORK_DIR / "user_network.graphml"
    if not info_path.exists() or not user_path.exists():
        raise FileNotFoundError("Run build_networks.py before network analysis.")

    info_graph = nx.read_graphml(info_path)
    user_graph = nx.read_graphml(user_path)
    if not info_graph.is_directed() or user_graph.is_directed():
        raise ValueError("Unexpected graph direction in the exported GraphML files.")

    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    info_metrics, info_nodes = _information_analysis(info_graph)
    user_metrics, user_nodes = _user_analysis(user_graph)
    results = {
        "information_diffusion": info_metrics,
        "user_interaction": user_metrics,
    }

    (ANALYSIS_DIR / "network_metrics.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_csv(ANALYSIS_DIR / "network_metrics.csv", _metrics_rows(results))
    _write_csv(ANALYSIS_DIR / "top_information_nodes.csv", info_nodes)
    _write_csv(ANALYSIS_DIR / "top_user_nodes.csv", user_nodes)
    (ANALYSIS_DIR / "network_analysis_summary.md").write_text(
        _summary_markdown(info_metrics, user_metrics, info_nodes, user_nodes),
        encoding="utf-8",
    )

    print(f"Network analysis saved to {ANALYSIS_DIR}")
    print(
        "Information network: "
        f"density={info_metrics['density']:.6f}, "
        f"largest weak component={info_metrics['largest_component_nodes']}"
    )
    print(
        "User network: "
        f"density={user_metrics['density']:.6f}, "
        f"modularity={user_metrics['modularity_louvain']:.4f}"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(f"Network analysis failed: {exc}") from exc
