#!/usr/bin/env python3
"""023c — Related-Entries 그래프를 Neo4j에 적재.

data/graph/graph.json → (:Entry {slug,title,author,community,pagerank})-[:RELATED_TO]->(:Entry).
Neo4j Browser(http://localhost:7474)에서 Cypher로 탐색 + 시각화.

사용: docker compose up -d neo4j → python 02_scrape/023_graph_builder/to_neo4j.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from neo4j import GraphDatabase

ROOT = Path(__file__).resolve().parents[2]
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))["neo4j"]
PW = os.getenv("NEO4J_PASSWORD", "sepgraph123")  # 로컬 dev 기본값, .env로 override
G = json.loads((ROOT / "data" / "graph" / "graph.json").read_text(encoding="utf-8"))


def main() -> None:
    driver = GraphDatabase.driver(CFG["url"], auth=(CFG["user"], PW))
    with driver.session() as s:
        s.run("MATCH (n) DETACH DELETE n")
        s.run("CREATE CONSTRAINT entry_slug IF NOT EXISTS FOR (e:Entry) REQUIRE e.slug IS UNIQUE")

        nodes = [{"slug": n["id"], "title": n.get("title"), "author": n.get("author"),
                  "community": n.get("community"), "pagerank": n.get("pagerank")} for n in G["nodes"]]
        for i in range(0, len(nodes), 1000):
            s.run("UNWIND $rows AS r MERGE (e:Entry {slug:r.slug}) "
                  "SET e.title=r.title, e.author=r.author, e.community=r.community, e.pagerank=r.pagerank",
                  rows=nodes[i:i + 1000])

        edges = [{"s": l["source"], "t": l["target"]} for l in G["links"]]
        for i in range(0, len(edges), 2000):
            s.run("UNWIND $rows AS r MATCH (a:Entry {slug:r.s}),(b:Entry {slug:r.t}) "
                  "MERGE (a)-[:RELATED_TO]->(b)", rows=edges[i:i + 2000])

        nc = s.run("MATCH (n:Entry) RETURN count(n) AS c").single()["c"]
        rc = s.run("MATCH ()-[r:RELATED_TO]->() RETURN count(r) AS c").single()["c"]
        print(f"Entry nodes: {nc} | RELATED_TO rels: {rc}")
    driver.close()


if __name__ == "__main__":
    main()
