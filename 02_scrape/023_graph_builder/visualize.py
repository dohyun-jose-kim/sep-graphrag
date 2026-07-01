#!/usr/bin/env python3
"""023b — 그래프 정적 스냅샷 (matplotlib).

data/graph/graph.json → 세 PNG:
  data/graph/community_map.png  - 커뮤니티 메타그래프(10 클러스터가 어떻게 연결되나)
  data/graph/hub_subgraph.png   - PageRank 상위 허브 유도 부분그래프(가독성)
  data/graph/full_graph.png     - 전체 1,861 노드 개별 시각화(커뮤니티별로 뭉쳐 배치)

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
import numpy as np  # noqa: E402

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


def full_graph(G: nx.DiGraph, label_top: int = 60) -> None:
    """전체 노드를 한 장에: 커뮤니티를 은하 형태로 뭉쳐 배치 + 개별 노드 표시."""
    comm = {n: G.nodes[n].get("community", 0) for n in G}
    pr = {n: G.nodes[n].get("pagerank", 0) or 0 for n in G}
    mx_pr = max(pr.values()) or 1
    U = G.to_undirected()

    # 1) 커뮤니티 메타그래프로 클러스터 중심 좌표 계산 (community_map()과 동일한 배치 로직)
    ew = Counter()
    for u, v in G.edges():
        a, b = comm[u], comm[v]
        if a != b:
            ew[tuple(sorted((a, b)))] += 1
    meta = nx.Graph()
    meta.add_nodes_from(set(comm.values()))
    for (a, b), w in ew.items():
        meta.add_edge(a, b, weight=w)
    sizes = Counter(comm.values())
    centroid = nx.spring_layout(meta, weight="weight", seed=42, k=1.5)
    spread = 3.2  # 클러스터 간 간격
    centroid = {c: xy * spread for c, xy in centroid.items()}

    # 2) 각 노드를 소속 커뮤니티 중심 근방에 지터로 초기 배치 후 spring_layout으로 이완
    rng = np.random.RandomState(42)
    init_pos = {n: centroid[comm[n]] + rng.normal(scale=0.6, size=2) for n in G}
    pos = nx.spring_layout(U, pos=init_pos, k=0.12, iterations=40, seed=42)

    labels = {n: n for n in sorted(G, key=lambda n: pr[n], reverse=True)[:label_top]}

    fig, ax = plt.subplots(figsize=(24, 18))
    nx.draw_networkx_edges(U, pos, alpha=0.045, edge_color="#666", width=0.35, ax=ax)
    nx.draw_networkx_nodes(U, pos, node_size=[15 + 700 * (pr[n] / mx_pr) ** 0.5 for n in G],
                           node_color=[PALETTE[comm[n] % len(PALETTE)] for n in G], alpha=0.85, linewidths=0, ax=ax)
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=7, ax=ax)

    # 커뮤니티 범례(색 -> 대표 주제)
    members = defaultdict(list)
    for n in G:
        members[comm[n]].append(n)
    handles = []
    for c in sorted(sizes, key=lambda c: -sizes[c]):
        top3 = sorted(members[c], key=lambda n: pr[n], reverse=True)[:3]
        handles.append(plt.Line2D([0], [0], marker="o", color="none", markerfacecolor=PALETTE[c % len(PALETTE)],
                                   markersize=10, label=f"c{c} (n={sizes[c]}): " + ", ".join(top3)))
    ax.legend(handles=handles, loc="lower left", fontsize=8, framealpha=0.9, title="community")

    ax.set_title(f"SEP Related-Entries — Full graph ({G.number_of_nodes()} nodes / {G.number_of_edges()} edges, "
                 f"color=community, size=pagerank, top {label_top} labeled)", fontsize=14)
    ax.axis("off")
    plt.tight_layout()
    for ext in ("png", "svg"):
        plt.savefig(OUT / f"full_graph.{ext}", dpi=140)
    plt.close()
    print("-> data/graph/full_graph.png (+svg)")


def main() -> None:
    G = load()
    community_map(G)
    hub_subgraph(G)
    full_graph(G)


if __name__ == "__main__":
    main()
