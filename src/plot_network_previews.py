"""Create quick QA previews; final report images should be exported from Gephi."""

from __future__ import annotations

import os
import math
from pathlib import Path


_MPL_CACHE = Path(__file__).resolve().parents[1] / "tmp" / "matplotlib"
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_CACHE))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import networkx as nx

from config import ROOT_DIR


NETWORK_DIR = ROOT_DIR / "output" / "networks"
FIGURE_DIR = ROOT_DIR / "output" / "figures"


def _connected_subgraph(graph: nx.Graph) -> nx.Graph:
    connected_nodes = {
        node_id for source, target in graph.edges for node_id in (source, target)
    }
    return graph.subgraph(connected_nodes).copy()


def plot_information_diffusion(graph: nx.DiGraph, path: Path) -> None:
    connected = _connected_subgraph(graph)
    positions = nx.spring_layout(connected, seed=42, iterations=80)
    degrees = dict(connected.degree())
    node_sizes = [min(10 + 4 * degrees[node_id], 90) for node_id in connected]
    node_colors = [degrees[node_id] for node_id in connected]

    figure, axis = plt.subplots(figsize=(12, 8), facecolor="white")
    axis.set_facecolor("white")
    nx.draw_networkx_edges(
        connected,
        positions,
        ax=axis,
        width=0.35,
        alpha=0.18,
        edge_color="#64748b",
        arrows=True,
        arrowsize=5,
        connectionstyle="arc3,rad=0.03",
    )
    nodes = nx.draw_networkx_nodes(
        connected,
        positions,
        ax=axis,
        node_size=node_sizes,
        node_color=node_colors,
        cmap="viridis",
        alpha=0.85,
        linewidths=0,
    )
    colorbar = figure.colorbar(nodes, ax=axis, fraction=0.03, pad=0.02)
    colorbar.set_label("Degree")
    axis.set_title("Palisades Fire Information Diffusion Network", fontsize=15)
    axis.text(
        0.5,
        0.985,
        f"Connected posts only: {connected.number_of_nodes()} nodes, "
        f"{connected.number_of_edges()} directed reply edges",
        transform=axis.transAxes,
        ha="center",
        va="top",
        fontsize=9,
        color="#475569",
    )
    axis.set_axis_off()
    figure.tight_layout()
    figure.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(figure)


def plot_user_network(graph: nx.Graph, path: Path) -> None:
    positions = nx.spring_layout(graph, seed=42, iterations=120)
    degrees = dict(graph.degree())
    node_sizes = [min(25 + 12 * degrees[node_id], 260) for node_id in graph]
    node_colors = [
        "#f97316" if int(graph.nodes[node_id].get("seed", 0)) else "#2563eb"
        for node_id in graph
    ]
    top_nodes = sorted(degrees, key=degrees.get, reverse=True)[:6]

    figure, axis = plt.subplots(figsize=(12, 8), facecolor="white")
    axis.set_facecolor("white")
    nx.draw_networkx_edges(
        graph,
        positions,
        ax=axis,
        width=[min(0.25 + 0.08 * int(data.get("weight", 1)), 2.5) for _, _, data in graph.edges(data=True)],
        alpha=0.2,
        edge_color="#64748b",
    )
    nx.draw_networkx_nodes(
        graph,
        positions,
        ax=axis,
        node_size=node_sizes,
        node_color=node_colors,
        alpha=0.88,
        linewidths=0.3,
        edgecolors="white",
    )
    for index, node_id in enumerate(top_nodes):
        angle = 2 * math.pi * index / len(top_nodes)
        x_offset = 96 * math.cos(angle)
        y_offset = 68 * math.sin(angle)
        axis.annotate(
            graph.nodes[node_id].get("label", node_id),
            xy=positions[node_id],
            xytext=(x_offset, y_offset),
            textcoords="offset points",
            ha="center",
            va="center",
            fontsize=7,
            color="#0f172a",
            arrowprops={"arrowstyle": "-", "color": "#94a3b8", "lw": 0.5},
        )
    axis.scatter([], [], s=45, color="#f97316", label="Seed user")
    axis.scatter([], [], s=45, color="#2563eb", label="Other relevant user")
    axis.legend(loc="lower left", frameon=False, fontsize=9)
    axis.set_title("Palisades Fire User Network", fontsize=15)
    axis.text(
        0.5,
        0.985,
        f"{graph.number_of_nodes()} users, {graph.number_of_edges()} undirected interaction edges; node size = degree",
        transform=axis.transAxes,
        ha="center",
        va="top",
        fontsize=9,
        color="#475569",
    )
    axis.set_axis_off()
    figure.tight_layout()
    figure.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    info_path = NETWORK_DIR / "information_diffusion.gexf"
    user_path = NETWORK_DIR / "user_network.gexf"
    if not info_path.exists() or not user_path.exists():
        raise FileNotFoundError("Run build_networks.py before creating previews.")

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    info_graph = nx.read_gexf(info_path)
    user_graph = nx.read_gexf(user_path)
    plot_information_diffusion(
        info_graph,
        FIGURE_DIR / "information_diffusion_preview.png",
    )
    plot_user_network(user_graph, FIGURE_DIR / "user_network_preview.png")
    print(f"Preview figures saved to {FIGURE_DIR}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(f"Preview generation failed: {exc}") from exc
