"""Construct the two project networks and export them for Gephi."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable

import networkx as nx

from config import DATA_DIR, ROOT_DIR


NETWORK_DIR = ROOT_DIR / "output" / "networks"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required data file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _clean_text(value: Any, limit: int | None = None) -> str:
    text = "" if value is None else str(value)
    text = "".join(
        character
        for character in text
        if character in "\t\n\r" or ord(character) >= 32
    )
    text = " ".join(text.split())
    if limit is not None and len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text


def _integer(value: Any, missing: int = -1) -> int:
    if value is None or value == "":
        return missing
    try:
        return int(value)
    except (TypeError, ValueError):
        return missing


def build_information_diffusion_graph(
    posts: list[dict[str, Any]],
) -> nx.DiGraph:
    graph = nx.DiGraph(
        name="2025 Palisades Fire Information Diffusion Network",
        edge_direction="parent post to reply or original post to reblog",
    )

    for post in posts:
        post_id = str(post["id"])
        account = post.get("account") or {}
        content = _clean_text(post.get("content_text"), 500)
        short_content = _clean_text(post.get("content_text"), 70)
        graph.add_node(
            post_id,
            label=f"@{_clean_text(account.get('acct'))}: {short_content}",
            account_id=_clean_text(account.get("id")),
            account=_clean_text(account.get("acct")),
            created_at=_clean_text(post.get("created_at")),
            language=_clean_text(post.get("language")),
            content=content,
            hashtags="|".join(_clean_text(value) for value in post.get("tags", [])),
            collection_methods="|".join(
                _clean_text(value) for value in post.get("collection_methods", [])
            ),
            replies_count=_integer(post.get("replies_count"), 0),
            reblogs_count=_integer(post.get("reblogs_count"), 0),
            favourites_count=_integer(post.get("favourites_count"), 0),
            is_reply=int(bool(post.get("in_reply_to_id"))),
            is_reblog=int(bool(post.get("is_reblog"))),
        )

    for post in posts:
        child_id = str(post["id"])
        parent_id = str(post.get("in_reply_to_id") or "")
        if parent_id in graph and child_id in graph and parent_id != child_id:
            graph.add_edge(
                parent_id,
                child_id,
                relationship="reply",
                weight=1,
            )

        original_id = str(post.get("reblog_of_id") or "")
        if original_id in graph and child_id in graph and original_id != child_id:
            graph.add_edge(
                original_id,
                child_id,
                relationship="reblog",
                weight=1,
            )

    for node_id, degree in graph.degree:
        graph.nodes[node_id]["degree"] = int(degree)
        graph.nodes[node_id]["in_degree"] = int(graph.in_degree(node_id))
        graph.nodes[node_id]["out_degree"] = int(graph.out_degree(node_id))

    return graph


def build_user_graph(
    users: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> nx.Graph:
    graph = nx.Graph(
        name="2025 Palisades Fire User Network",
        edge_definition="mention, reply, or reblog interaction",
    )

    for user in users:
        user_id = str(user["id"])
        graph.add_node(
            user_id,
            label=_clean_text(user.get("acct")) or user_id,
            acct=_clean_text(user.get("acct")),
            display_name=_clean_text(user.get("display_name")),
            url=_clean_text(user.get("url")),
            bot=int(bool(user.get("bot"))),
            seed=int(bool(user.get("seed"))),
            followers_count=_integer(user.get("followers_count")),
            following_count=_integer(user.get("following_count")),
            statuses_count=_integer(user.get("statuses_count")),
            event_post_count=_integer(user.get("event_post_count"), 0),
            reply_post_count=_integer(user.get("reply_post_count"), 0),
            mention_received_count=_integer(user.get("mention_received_count"), 0),
            discovery_methods="|".join(
                _clean_text(value) for value in user.get("discovery_methods", [])
            ),
        )

    for edge in edges:
        source_id = str(edge["source"])
        target_id = str(edge["target"])
        if source_id not in graph or target_id not in graph or source_id == target_id:
            continue
        graph.add_edge(
            source_id,
            target_id,
            relationship="|".join(
                _clean_text(value) for value in edge.get("relationship_types", [])
            ),
            weight=_integer(edge.get("weight"), 1),
            mention_count=_integer(edge.get("mention_count"), 0),
            reply_count=_integer(edge.get("reply_count"), 0),
            reblog_count=_integer(edge.get("reblog_count"), 0),
        )

    for node_id, degree in graph.degree:
        graph.nodes[node_id]["degree"] = int(degree)
        graph.nodes[node_id]["weighted_degree"] = int(
            sum(data.get("weight", 1) for _, _, data in graph.edges(node_id, data=True))
        )

    return graph


def _write_nodes_csv(graph: nx.Graph, path: Path) -> None:
    attributes = sorted(
        {key for _, data in graph.nodes(data=True) for key in data.keys()}
    )
    fieldnames = ["id", *attributes]
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for node_id, data in graph.nodes(data=True):
            writer.writerow({"id": node_id, **data})


def _write_edges_csv(graph: nx.Graph, path: Path) -> None:
    attributes = sorted(
        {key for _, _, data in graph.edges(data=True) for key in data.keys()}
    )
    fieldnames = ["source", "target", "type", *attributes]
    edge_type = "Directed" if graph.is_directed() else "Undirected"
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for source_id, target_id, data in graph.edges(data=True):
            writer.writerow(
                {
                    "source": source_id,
                    "target": target_id,
                    "type": edge_type,
                    **data,
                }
            )


def _component_sizes(graph: nx.Graph) -> list[int]:
    components: Iterable[set[str]]
    if graph.is_directed():
        components = nx.weakly_connected_components(graph)
    else:
        components = nx.connected_components(graph)
    return sorted((len(component) for component in components), reverse=True)


def _summary_text(info_graph: nx.DiGraph, user_graph: nx.Graph) -> str:
    info_components = _component_sizes(info_graph)
    user_components = _component_sizes(user_graph)
    info_average_degree = (
        sum(dict(info_graph.degree()).values()) / info_graph.number_of_nodes()
    )
    user_average_degree = (
        sum(dict(user_graph.degree()).values()) / user_graph.number_of_nodes()
    )

    return "\n".join(
        [
            "CSE 472 Network Export Summary",
            "================================",
            "",
            "Information Diffusion Network (directed)",
            f"Nodes: {info_graph.number_of_nodes()}",
            f"Edges: {info_graph.number_of_edges()}",
            f"Average degree: {info_average_degree:.4f}",
            f"Density: {nx.density(info_graph):.6f}",
            f"Weakly connected components: {len(info_components)}",
            f"Largest weak component: {info_components[0] if info_components else 0}",
            f"Isolates: {nx.number_of_isolates(info_graph)}",
            "Edge direction: parent/original post -> reply/reblog post",
            "",
            "User Network (undirected)",
            f"Nodes: {user_graph.number_of_nodes()}",
            f"Edges: {user_graph.number_of_edges()}",
            f"Average degree: {user_average_degree:.4f}",
            f"Density: {nx.density(user_graph):.6f}",
            f"Connected components: {len(user_components)}",
            f"Largest component: {user_components[0] if user_components else 0}",
            f"Isolates: {nx.number_of_isolates(user_graph)}",
            "Edge meaning: at least one mention, reply, or reblog interaction",
            "",
        ]
    )


def export_graph(graph: nx.Graph, stem: str) -> None:
    nx.write_gexf(graph, NETWORK_DIR / f"{stem}.gexf", encoding="utf-8")
    nx.write_graphml(graph, NETWORK_DIR / f"{stem}.graphml", encoding="utf-8")
    _write_nodes_csv(graph, NETWORK_DIR / f"{stem}_nodes.csv")
    _write_edges_csv(graph, NETWORK_DIR / f"{stem}_edges.csv")


def main() -> None:
    posts_payload = _load_json(DATA_DIR / "posts.json")
    users_payload = _load_json(DATA_DIR / "users.json")
    posts = posts_payload.get("posts", [])
    users = users_payload.get("users", [])
    user_edges = users_payload.get("edges", [])

    if not posts or not users:
        raise ValueError("The two data files must contain non-empty posts and users lists.")

    NETWORK_DIR.mkdir(parents=True, exist_ok=True)
    info_graph = build_information_diffusion_graph(posts)
    user_graph = build_user_graph(users, user_edges)

    export_graph(info_graph, "information_diffusion")
    export_graph(user_graph, "user_network")
    (NETWORK_DIR / "network_summary.txt").write_text(
        _summary_text(info_graph, user_graph),
        encoding="utf-8",
    )

    print(
        "Information diffusion network: "
        f"{info_graph.number_of_nodes()} nodes, {info_graph.number_of_edges()} edges"
    )
    print(
        f"User network: {user_graph.number_of_nodes()} nodes, "
        f"{user_graph.number_of_edges()} edges"
    )
    print(f"Gephi exports saved to {NETWORK_DIR}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(f"Network construction failed: {exc}") from exc
