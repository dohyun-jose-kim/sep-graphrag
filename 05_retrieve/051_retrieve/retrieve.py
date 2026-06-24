#!/usr/bin/env python3
"""051 — 리트리벌: dense → [rerank] → small-to-big(parent) → dedup → [graph 1홉].

eval.py / qa.py 에서 importlib로 로드해 재사용(번호 폴더라 일반 import 불가).
리랭커는 best-effort: 로드/스코어 실패 시 dense 순서로 자동 폴백(블로킹 금지).

CLI: python 05_retrieve/051_retrieve/retrieve.py "질문" [--graph]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import numpy as np
import torch
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchAny
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[2]
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
QD = CFG["qdrant"]
COLL = QD["collection"]
DOCSTORE = ROOT / "data" / "docstore" / "parents.sqlite"
GRAPH = ROOT / "data" / "graph" / "graph.json"


def _client() -> QdrantClient:
    return QdrantClient(url=QD["url"]) if QD["mode"] == "server" else QdrantClient(path=str(ROOT / QD["path"]))


class Retriever:
    def __init__(self, device: str = "mps", use_rerank: bool = True):
        self.model = SentenceTransformer(CFG["embed_model"], device=device,
                                         model_kwargs={"torch_dtype": torch.float16})
        self.model.max_seq_length = 512
        self.client = _client()
        self.db = sqlite3.connect(str(DOCSTORE))
        self.db.row_factory = sqlite3.Row
        self.reranker = None
        if use_rerank:
            try:  # Qwen3-Reranker는 표준 CrossEncoder가 아닐 수 있음 → 실패 시 dense 폴백
                from sentence_transformers import CrossEncoder
                self.reranker = CrossEncoder("Qwen/Qwen3-Reranker-0.6B", device=device)
            except Exception as e:
                print(f"[retrieve] reranker 로드 실패 → dense 폴백: {e}")
        self.adj: dict[str, list[str]] = {}
        if GRAPH.exists():
            for l in json.loads(GRAPH.read_text(encoding="utf-8")).get("links", []):
                self.adj.setdefault(l["source"], []).append(l["target"])

    def encode_query(self, q: str):
        try:
            return self.model.encode(q, prompt_name="query", normalize_embeddings=True)
        except Exception:
            return self.model.encode(f"Instruct: Given a query, retrieve relevant passages\nQuery: {q}",
                                     normalize_embeddings=True)

    def dense(self, q: str, k: int = 50, slugs: list[str] | None = None) -> list[dict]:
        flt = Filter(must=[FieldCondition(key="slug", match=MatchAny(any=slugs))]) if slugs else None
        hits = self.client.query_points(COLL, query=self.encode_query(q).tolist(),
                                        using="dense", query_filter=flt, limit=k).points
        return [{"score": h.score, **h.payload} for h in hits]

    def rerank(self, q: str, hits: list[dict], top: int) -> list[dict]:
        if not self.reranker or not hits:
            return hits[:top]
        try:
            scores = self.reranker.predict([(q, h["text"]) for h in hits])
            return [hits[i] for i in np.argsort(scores)[::-1][:top]]
        except Exception as e:
            print(f"[retrieve] rerank 실패 → dense 순서: {e}")
            return hits[:top]

    def parents(self, hits: list[dict], n: int = 5) -> list[dict]:
        seen, out = set(), []
        for h in hits:
            pid = h["parent_id"]
            if pid in seen:
                continue
            seen.add(pid)
            row = self.db.execute("SELECT * FROM parents WHERE parent_id=?", (pid,)).fetchone()
            if row:
                out.append({"parent_id": pid, "slug": row["slug"], "section_path": row["section_path"],
                            "url": row["url"], "text": row["text"]})
            if len(out) >= n:
                break
        return out

    def graph_expand(self, q: str, hits: list[dict], add: int = 8) -> list[dict]:
        slugs = {h["slug"] for h in hits[:5]}
        neigh = {t for s in slugs for t in self.adj.get(s, [])} - slugs
        return self.dense(q, k=add, slugs=list(neigh)) if neigh else []

    def retrieve(self, q: str, k_dense: int = 50, k_rerank: int = 8,
                 n_parents: int = 5, use_graph: bool = False) -> dict:
        hits = self.dense(q, k_dense)
        ranked = self.rerank(q, hits, k_rerank)
        if use_graph:
            extra = self.graph_expand(q, ranked)
            ranked = self.rerank(q, ranked + extra, k_rerank + 4)
        return {"children": ranked, "parents": self.parents(ranked, n_parents)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--graph", action="store_true")
    a = ap.parse_args()
    res = Retriever().retrieve(a.query, use_graph=a.graph)
    print(f"\nQ: {a.query}\n--- parents ({len(res['parents'])}) ---")
    for p in res["parents"]:
        print(f"  [{p['slug']}] {p['section_path'][:55]}\n    {p['url']}")
