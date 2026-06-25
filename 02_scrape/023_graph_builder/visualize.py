#!/usr/bin/env python3
"""023b — 그래프 정적 스냅샷 (matplotlib).

data/graph/graph.json → 두 PNG:
  data/graph/community_map.png  - 커뮤니티 메타그래프(10 클러스터가 어떻게 연결되나)
  data/graph/hub_subgraph.png   - PageRank 상위 허브 유도 부분그래프(가독성)

사용: python 02_scrape/023_graph_builder/visualize.py
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "graph"
PALETTE = ["#e6194B", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#42d4f4",
           "#f032e6", "#bfef45", "#469990", "#9A6324", "#808000", "#000075"]


def load() -> nx.DiGraph:
    return nx.node_link_graph(json.loads((OUT / "graph.json").read_text(encoding="utf-8")), edges="links")


def community_map(G: nx.DiGraph) -> None:
    comm = {n: G.nodes[n].get("community", 0) for n in G}
    sizes = Counter(comm.values())
    members = defaultdict(list)
    for n in G:
        members[comm[n]].append(n)
    labels = {}
    for c, ms in members.items():
        ms.sort(key=lambda n: G.nodes[n].get("pagerank", 0), reverse=True)
        labels[c] = f"c{c} (n={sizes[c]})\n" + "\n".join(ms[:3])

    ew = Counter()
    for u, v in G.edges():
        a, b = comm[u], comm[v]
        if a != b:
            ew[tuple(sorted((a, b)))] += 1
    meta = nx.Graph()
    for c in sizes:
        meta.add_node(c)
    for (a, b), w in ew.items():
        meta.add_edge(a, b, weight=w)

    pos = nx.spring_layout(meta, weight="weight", seed=42, k=1.5)
    plt.figure(figsize=(15, 11))
    nx.draw_networkx_nodes(meta, pos, node_size=[sizes[c] * 9 for c in meta],
                           node_color=[PALETTE[c % len(PALETTE)] for c in meta], alpha=0.85)
    widths = [meta[a][b]["weight"] for a, b in meta.edges()]
    mx = max(widths)
    nx.draw_networkx_edges(meta, pos, width=[0.4 + 6 * w / mx for w in widths], alpha=0.35, edge_color="#555")
    nx.draw_networkx_labels(meta, pos, labels=labels, font_size=9)
    plt.title("SEP Related-Entries — Community Map (10 clusters, node∝size, edge∝inter-links)", fontsize=13)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(OUT / "community_map.png", dpi=140)
    plt.close()
    print("-> data/graph/community_map.png")


def hub_subgraph(G: nx.DiGraph, top: int = 35) -> None:
    hubs = sorted(G.nodes, key=lambda n: G.nodes[n].get("pagerank", 0), reverse=True)[:top]
    H = G.subgraph(hubs)
    comm = {n: G.nodes[n].get("community", 0) for n in H}
    pr = {n: G.nodes[n].get("pagerank", 0) for n in H}
    mx = max(pr.values())
    pos = nx.spring_layout(H.to_undirected(), seed=42, k=0.9)
    plt.figure(figsize=(16, 12))
    nx.draw_networkx_nodes(H, pos, node_size=[300 + 6000 * pr[n] / mx for n in H],
                           node_color=[PALETTE[comm[n] % len(PALETTE)] for n in H], alpha=0.85)
    nx.draw_networkx_edges(H, pos, alpha=0.25, edge_color="#666", arrowsize=8, width=0.6)
    nx.draw_networkx_labels(H, pos, font_size=8)
    plt.title(f"SEP Related-Entries — Top {top} hubs by PageRank (color=community)", fontsize=13)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(OUT / "hub_subgraph.png", dpi=140)
    plt.close()
    print("-> data/graph/hub_subgraph.png")


def main() -> None:
    G = load()
    community_map(G)
    hub_subgraph(G)


if __name__ == "__main__":
    main()
