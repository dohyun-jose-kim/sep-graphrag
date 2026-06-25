#!/usr/bin/env python3
"""023 — Related Entries 그래프 빌더.

data/metadata/entries_meta.json 의 related_entries로 **방향 그래프**를 만들고
edgelist / 분석 / pyvis 시각화를 산출한다. GraphRAG(Type A)의 재료.

노드 = 전체 contents entry(1,861). 엣지 = entry → related entry (out-link).
재실행 가능; 메타가 부분만 있어도(크롤 진행 중) 있는 만큼으로 그린다.

출력(gitignored):
  data/graph/edges.csv        - source,target
  data/graph/graph.json       - networkx node-link (속성 포함)
  data/graph/graph.html       - pyvis 인터랙티브 시각화
  data/graph/hubs.json        - 중심성 상위 + 커뮤니티 요약

사용 (repo 루트에서):
  python 02_scrape/023_graph_builder/build_graph.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import networkx as nx
from pyvis.network import Network

ROOT = Path(__file__).resolve().parents[2]
_CONTENTS_PATH = ROOT / "data" / "contents" / "entries.json"
CONTENTS = json.loads(_CONTENTS_PATH.read_text(encoding="utf-8")) if _CONTENTS_PATH.exists() else []
META_PATH = ROOT / "data" / "metadata" / "entries_meta.json"
OUT = ROOT / "data" / "graph"


def build() -> nx.DiGraph:
    meta = {r["slug"]: r for r in json.loads(META_PATH.read_text(encoding="utf-8"))}
    G = nx.DiGraph()
    for e in CONTENTS:  # 노드 = 전체 코퍼스
        m = meta.get(e["slug"], {})
        G.add_node(e["slug"], title=e["title"], author=e.get("author"),
                   fetched=bool(m))
    nodes = set(G.nodes)
    for slug, m in meta.items():
        for tgt in m.get("related_entries", []):
            if tgt in nodes and tgt != slug:
                G.add_edge(slug, tgt)
    return G


def analyze(G: nx.DiGraph) -> dict:
    und = G.to_undirected()
    pr = nx.pagerank(G) if G.number_of_edges() else {n: 0.0 for n in G}
    indeg = dict(G.in_degree())
    try:
        communities = nx.community.louvain_communities(und, seed=42)
    except Exception:
        communities = nx.community.greedy_modularity_communities(und)
    comm_of = {n: i for i, c in enumerate(communities) for n in c}
    nx.set_node_attributes(G, comm_of, "community")
    nx.set_node_attributes(G, pr, "pagerank")

    def top(d, k=15):
        return [{"slug": s, "title": G.nodes[s]["title"], "value": round(v, 5)}
                for s, v in sorted(d.items(), key=lambda kv: kv[1], reverse=True)[:k]]

    # 커뮤니티별 상위 멤버(PageRank 기준) — 주제 클러스터를 읽을 수 있게
    members: dict[int, list[str]] = {}
    for n, d in G.nodes(data=True):
        members.setdefault(d["community"], []).append(n)
    community_summary = [
        {"community": cid, "size": len(ms),
         "top": [{"slug": s, "title": G.nodes[s]["title"]}
                 for s in sorted(ms, key=lambda n: pr[n], reverse=True)[:8]]}
        for cid, ms in sorted(members.items(), key=lambda kv: -len(kv[1]))
    ]

    return {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "fetched_nodes": sum(1 for _, d in G.nodes(data=True) if d["fetched"]),
        "communities": len(communities),
        "largest_community": max((len(c) for c in communities), default=0),
        "top_by_pagerank": top(pr),
        "top_by_in_degree": top(indeg),
        "community_summary": community_summary,
    }


def visualize(G: nx.DiGraph, path: Path) -> None:
    net = Network(height="800px", width="100%", directed=True, bgcolor="#111",
                  font_color="#eee", cdn_resources="in_line")  # 자기완결 HTML(외부 lib/ 미생성)
    net.barnes_hut(gravity=-8000, spring_length=120)
    palette = ["#e6194B", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#42d4f4",
               "#f032e6", "#bfef45", "#fabed4", "#469990", "#dcbeff", "#9A6324"]
    deg = dict(G.degree())
    for n, d in G.nodes(data=True):
        c = d.get("community", 0)
        net.add_node(n, label=d["title"], title=f"{d['title']}\n{n} · deg {deg[n]}",
                     color=palette[c % len(palette)], size=8 + deg[n] ** 0.5 * 3)
    for s, t in G.edges():
        net.add_edge(s, t, color="#444")
    net.toggle_physics(True)
    net.write_html(str(path), notebook=False)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    G = build()
    stats = analyze(G)

    with open(OUT / "edges.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source", "target"])
        w.writerows(G.edges())
    (OUT / "graph.json").write_text(
        json.dumps(nx.node_link_data(G, edges="links"), ensure_ascii=False), encoding="utf-8"
    )
    (OUT / "hubs.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    visualize(G, OUT / "graph.html")

    print(f"nodes {stats['nodes']} (fetched {stats['fetched_nodes']}) | edges {stats['edges']} "
          f"| communities {stats['communities']} (largest {stats['largest_community']})")
    print("top by PageRank:", [t["slug"] for t in stats["top_by_pagerank"][:8]])
    print("top by in-degree:", [t["slug"] for t in stats["top_by_in_degree"][:8]])
    print("communities (size · 상위 멤버):")
    for c in stats["community_summary"]:
        print(f"  #{c['community']:>3} ({c['size']:>4}): " + ", ".join(t["slug"] for t in c["top"][:6]))
    print(f"-> {OUT.relative_to(ROOT)}/ (edges.csv, graph.json, graph.html, hubs.json)")


if __name__ == "__main__":
    main()
