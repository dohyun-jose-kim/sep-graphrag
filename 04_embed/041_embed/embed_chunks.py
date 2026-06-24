#!/usr/bin/env python3
"""041 — child 임베딩 (Qwen3-Embedding-0.6B, MPS).

data/chunks/children.jsonl → data/embeddings/0.6B/ (shard별 vectors_NNN.npy + ids.json).
- 문서(child)는 instruction 없이 인코딩(Qwen3 권장). 쿼리는 검색단에서 prompt_name="query".
- shard 단위 저장 → checkpoint/resume(있는 shard 스킵).
- 임베딩 normalize(코사인용).

사용 (repo 루트에서):
  python 04_embed/041_embed/embed_chunks.py --limit 200   # 슬라이스 검증
  python 04_embed/041_embed/embed_chunks.py               # 전체(~152k, 백그라운드)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[2]
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
MODEL = CFG["embed_model"]
CHILDREN = ROOT / "data" / "chunks" / "children.jsonl"
OUT = ROOT / "data" / "embeddings" / "0.6B"
SHARD = 10000


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="앞에서 N개만(검증)")
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--device", default="mps")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    rows = [json.loads(l) for l in open(CHILDREN, encoding="utf-8")]
    if args.limit:
        rows = rows[: args.limit]
    (OUT / "ids.json").write_text(json.dumps([r["id"] for r in rows]), encoding="utf-8")

    model = SentenceTransformer(MODEL, device=args.device)
    model.max_seq_length = 2048  # 최대 청크(1585 tok)도 안 잘리게
    dim = model.get_sentence_embedding_dimension()
    n = len(rows)
    print(f"model {MODEL} dim {dim} device {args.device} | children {n}", flush=True)

    for s in range(0, n, SHARD):
        shard_path = OUT / f"vectors_{s // SHARD:03d}.npy"
        if shard_path.exists():
            print(f"shard {s//SHARD:03d}: cached, skip", flush=True)
            continue
        texts = [r["text"] for r in rows[s : s + SHARD]]
        vecs = model.encode(
            texts, batch_size=args.batch, normalize_embeddings=True,
            convert_to_numpy=True, show_progress_bar=True,
        ).astype(np.float32)
        np.save(shard_path, vecs)
        print(f"shard {s//SHARD:03d}: {vecs.shape} -> {shard_path.name}", flush=True)

    print(f"done: {n} children embedded, dim {dim}")


if __name__ == "__main__":
    main()
