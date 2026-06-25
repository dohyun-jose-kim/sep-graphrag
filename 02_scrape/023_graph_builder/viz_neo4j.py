#!/usr/bin/env python3
"""023d — Neo4j 기반 SVG 스냅샷.

  data/graph/schema.svg       - 그래프 스키마 ((:Entry)-[:RELATED_TO]->(:Entry) + 속성)
  data/graph/camus_2hop.svg   - Neo4j에서 뽑은 Camus 2-hop 네트워크

사용: python 02_scrape/023_graph_builder/viz_neo4j.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch  # noqa: E402
from neo4j import GraphDatabase  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))["neo4j"]
PW = os.getenv("NEO4J_PASSWORD", "sepgraph123")  # 로컬 dev 기본값, .env로 override
OUT = ROOT / "data" / "graph"
PALETTE = ["#e6194B", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#42d4f4",
           "#f032e6", "#bfef45", "#469990", "#9A6324"]


def save(fig, name):
    for ext in ("svg", "png"):
        fig.savefig(OUT / f"{name}.{ext}", bbox_inches="tight", dpi=140)
    plt.close(fig)
    print(f"-> data/graph/{name}.svg (+png)")


def schema():
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.add_patch(Circle((0.35, 0.5), 0.13, color="#4363d8", alpha=0.85, zorder=2))
    ax.text(0.35, 0.5, ":Entry", ha="center", va="center", color="white", fontsize=15, fontweight="bold", zorder=3)
    # self relationship
    ax.add_patch(FancyArrowPatch((0.35, 0.63), (0.48, 0.5), connectionstyle="arc3,rad=1.6",
                                 arrowstyle="-|>", mutation_scale=18, color="#555", lw=1.8, zorder=1))
    ax.text(0.62, 0.74, ":RELATED_TO", ha="center", fontsize=12, color="#333", fontweight="bold")
    ax.text(0.35, 0.27, "properties:\nslug · title · author\ncommunity · pagerank",
            ha="center", va="top", fontsize=11, color="#222",
            bbox=dict(boxstyle="round", fc="#eef", ec="#88a"))
    ax.text(0.5, 0.97, "SEP GraphRAG — Neo4j schema", ha="center", fontsize=14, fontweight="bold")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    save(fig, "schema")


def camus_2hop(seed="camus"):
    driver = GraphDatabase.driver(CFG["url"], auth=(CFG["user"], PW))
    with driver.session() as s:
        nodes = {r["slug"]: (r["comm"], r["pr"]) for r in s.run(
            "MATCH (c:Entry{slug:$x})-[:RELATED_TO*0..2]-(n) "
            "RETURN DISTINCT n.slug AS slug, n.community AS comm, n.pagerank AS pr", x=seed)}
        slugs = list(nodes)
        elist = [(r["a"], r["b"]) for r in s.run(
            "MATCH (a:Entry)-[:RELATED_TO]->(b:Entry) WHERE a.slug IN $s AND b.slug IN $s "
            "RETURN a.slug AS a, b.slug AS b", s=slugs)]
    driver.close()

    G = nx.DiGraph(); G.add_nodes_from(slugs); G.add_edges_from(elist)
    hop = nx.single_source_shortest_path_length(G.to_undirected(), seed, cutoff=2)
    hop_color = {0: "#e6194B", 1: "#f58231", 2: "#9ecae1"}
    one_hop = [n for n in G if hop.get(n) == 1]
    pr = {n: nodes[n][1] or 0 for n in G}
    mx = max(pr.values()) or 1
    top2 = sorted([n for n in G if hop.get(n) == 2], key=lambda n: pr[n], reverse=True)[:10]
    labels = {n: n for n in [seed] + one_hop + top2}

    pos = nx.spring_layout(G.to_undirected(), seed=42, k=0.5, iterations=80)
    fig, ax = plt.subplots(figsize=(17, 13))
    nx.draw_networkx_edges(G, pos, alpha=0.18, edge_color="#888", arrowsize=6, width=0.5, ax=ax)
    nx.draw_networkx_nodes(G, pos, node_color=[hop_color.get(hop.get(n, 2), "#ccc") for n in G],
                           node_size=[120 + 4000 * pr[n] / mx for n in G], alpha=0.9, ax=ax)
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=9, ax=ax)
    ax.set_title(f"Camus 2-hop network (Neo4j) — {len(G)} entries · red=seed, orange=1-hop, blue=2-hop",
                 fontsize=14)
    ax.axis("off")
    save(fig, f"{seed}_2hop")


def main():
    schema()
    camus_2hop("camus")


if __name__ == "__main__":
    main()
