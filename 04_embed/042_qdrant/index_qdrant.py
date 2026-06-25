#!/usr/bin/env python3
"""042 — Qdrant 로컬 인덱싱 (도커 X).

data/embeddings/0.6B/ (vectors + ids) + children.jsonl payload → Qdrant 로컬 파일모드.
- QdrantClient(path=...) : 서버/도커 없이 디스크 영속.
- named vector "dense" : 나중에 "sparse"(hybrid) 추가해도 안 깨지게.
- payload에 청크 메타 + child text(리랭크/표시용). parent 본문은 sqlite docstore에서 별도 룩업.

사용 (repo 루트에서):
  python 04_embed/042_qdrant/index_qdrant.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[2]
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
MODEL, DIM = CFG["embed_model"], CFG["embed_dim"]
EMB = ROOT / "data" / "embeddings" / "0.6B"
CHILDREN = ROOT / "data" / "chunks" / "children.jsonl"
QD = CFG["qdrant"]
COLL = QD["collection"]


def make_client() -> QdrantClient:
    """config.qdrant.mode: 'local'(파일모드, 도커X) | 'server'(docker localhost). 코드 동일, 연결만 다름."""
    if QD["mode"] == "server":
        return QdrantClient(url=QD["url"])
    (ROOT / QD["path"]).mkdir(parents=True, exist_ok=True)
    return QdrantClient(path=str(ROOT / QD["path"]))


def load_vectors() -> np.ndarray:
    shards = sorted(EMB.glob("vectors_*.npy"))
    return np.concatenate([np.load(s) for s in shards], axis=0)


def main() -> None:
    ids = json.loads((EMB / "ids.json").read_text(encoding="utf-8"))
    vecs = load_vectors()
    rows = [json.loads(ln) for ln in open(CHILDREN, encoding="utf-8")][: len(ids)]
    assert len(ids) == len(vecs) == len(rows), (len(ids), len(vecs), len(rows))

    client = make_client()
    if client.collection_exists(COLL):
        client.delete_collection(COLL)
    client.create_collection(
        COLL, vectors_config={"dense": VectorParams(size=DIM, distance=Distance.COSINE)}
    )

    B = 1000
    for i in range(0, len(rows), B):
        pts = [
            PointStruct(id=j, vector={"dense": v.tolist()}, payload={
                "chunk_id": r["id"], "slug": r["slug"], "entry": r["entry"], "author": r["author"],
                "section_path": r["section_path"], "url": r["url"], "parent_id": r["parent_id"],
                "level": r["level"], "has_stripped_math": r["has_stripped_math"],
                "tokens": r["tokens"], "text": r["text"],
            })
            for j, (r, v) in enumerate(zip(rows[i : i + B], vecs[i : i + B], strict=False), start=i)
        ]
        client.upsert(COLL, points=pts)
        print(f"upserted {min(i + B, len(rows))}/{len(rows)}", flush=True)

    print("collection count:", client.count(COLL).count)

    # sanity: 쿼리 인코딩(prompt_name='query') → top-5
    model = SentenceTransformer(MODEL, device="mps")
    qv = model.encode("Why did Camus reject existentialism?",
                      prompt_name="query", normalize_embeddings=True).tolist()
    hits = client.query_points(COLL, query=qv, using="dense", limit=5).points
    print("sample query 'Why did Camus reject existentialism?':")
    for h in hits:
        print(f"  {h.score:.3f}  {h.payload['slug']:22} | {h.payload['section_path'][:45]}")


if __name__ == "__main__":
    main()
