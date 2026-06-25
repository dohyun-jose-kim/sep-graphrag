#!/usr/bin/env python3
"""01_setup — 서비스/데이터 가용성 점검. `make healthcheck` 또는 직접 실행."""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))


def check_qdrant() -> str:
    try:
        from qdrant_client import QdrantClient
        n = QdrantClient(url=CFG["qdrant"]["url"]).count(CFG["qdrant"]["collection"]).count
        return f"OK ({n} points)"
    except Exception as e:
        return f"DOWN → `docker compose up -d qdrant` ({type(e).__name__})"


def check_ollama() -> str:
    try:
        import httpx
        ms = [m["name"] for m in httpx.get("http://localhost:11434/api/tags", timeout=5).json()["models"]]
        return f"OK ({len(ms)} models)"
    except Exception as e:
        return f"DOWN → `ollama serve` ({type(e).__name__})"


def check_neo4j() -> str:
    try:
        from neo4j import GraphDatabase
        pw = os.getenv("NEO4J_PASSWORD", "sepgraph123")
        d = GraphDatabase.driver(CFG["neo4j"]["url"], auth=(CFG["neo4j"]["user"], pw))
        with d.session() as s:
            n = s.run("MATCH (n:Entry) RETURN count(n) AS c").single()["c"]
        d.close()
        return f"OK ({n} nodes)"
    except Exception as e:
        return f"DOWN → `docker compose up -d neo4j` ({type(e).__name__})"


def check_data() -> dict:
    paths = {
        "contents": ROOT / "data/contents/entries.json",
        "chunks": ROOT / "data/chunks/children.jsonl",
        "embeddings": ROOT / "data/embeddings/0.6B/ids.json",
        "docstore": ROOT / "data/docstore/parents.sqlite",
    }
    return {k: ("✅" if p.exists() else "❌ (파이프라인 미실행)") for k, p in paths.items()}


def main() -> None:
    print("=== SEP GraphRAG healthcheck ===")
    print(f"Qdrant : {check_qdrant()}")
    print(f"Ollama : {check_ollama()}")
    print(f"Neo4j  : {check_neo4j()}")
    for k, v in check_data().items():
        print(f"data/{k:11}: {v}")


if __name__ == "__main__":
    main()
