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

# Qwen3-Reranker = causal-LM yes/no 스코어러(표준 CrossEncoder 아님). 공식 포맷.
RERANK_MODEL = "Qwen/Qwen3-Reranker-0.6B"
RERANK_INSTRUCT = "Given a philosophy question, retrieve passages that help answer it"
RERANK_PREFIX = ('<|im_start|>system\nJudge whether the Document meets the requirements based on '
                 'the Query and the Instruct provided. Note that the answer can only be "yes" or '
                 '"no".<|im_end|>\n<|im_start|>user\n')
RERANK_SUFFIX = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"


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
            try:  # 실패 시 dense 폴백(블로킹 금지)
                from transformers import AutoModelForCausalLM, AutoTokenizer
                self.rk_tok = AutoTokenizer.from_pretrained(RERANK_MODEL, padding_side="left")
                self.rk_model = AutoModelForCausalLM.from_pretrained(
                    RERANK_MODEL, torch_dtype=torch.float16).to(device).eval()
                self.rk_yes = self.rk_tok.convert_tokens_to_ids("yes")
                self.rk_no = self.rk_tok.convert_tokens_to_ids("no")
                self.rk_pre = self.rk_tok.encode(RERANK_PREFIX, add_special_tokens=False)
                self.rk_suf = self.rk_tok.encode(RERANK_SUFFIX, add_special_tokens=False)
                self.reranker = True
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
            scores: list[float] = []
            for i in range(0, len(hits), 16):
                texts = [f"<Instruct>: {RERANK_INSTRUCT}\n<Query>: {q}\n<Document>: {h['text'][:1000]}"
                         for h in hits[i:i + 16]]
                enc = self.rk_tok(texts, add_special_tokens=False)["input_ids"]
                ids = [self.rk_pre + x + self.rk_suf for x in enc]
                tok = self.rk_tok.pad({"input_ids": ids}, padding=True, return_tensors="pt").to(self.rk_model.device)
                with torch.no_grad():
                    last = self.rk_model(**tok).logits[:, -1, :]
                pair = torch.stack([last[:, self.rk_no], last[:, self.rk_yes]], dim=1)
                scores.extend(torch.softmax(pair, dim=1)[:, 1].float().cpu().tolist())
            order = sorted(range(len(hits)), key=lambda j: scores[j], reverse=True)
            return [hits[j] for j in order[:top]]
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
                 n_parents: int = 5, use_graph: bool = False, reserve: int = 3) -> dict:
        hits = self.dense(q, k_dense)
        ranked = self.rerank(q, hits, k_rerank)
        if use_graph and reserve > 0:
            extra = self.graph_expand(q, ranked)
            if extra:
                have = {h["chunk_id"] for h in ranked}
                neigh = [e for e in self.rerank(q, extra, reserve) if e["chunk_id"] not in have][:reserve]
                if neigh:  # 이웃 entity 청크를 상위에 슬롯 예약(주체 top-2 뒤) → 비교 질문 다양성 보장
                    nset = {n["chunk_id"] for n in neigh}
                    rest = [h for h in ranked[2:] if h["chunk_id"] not in nset]
                    ranked = (ranked[:2] + neigh + rest)[:k_rerank]
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
