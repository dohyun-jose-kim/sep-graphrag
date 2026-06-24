#!/usr/bin/env python3
"""071 — 리트리벌 평가. eval_set.json → hit@k / MRR / coverage@k.

설정 A=dense, B=dense+rerank, C=dense+rerank+graph 비교. → data/eval/results.json + 표.
CLI: python 07_eval/eval.py
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KS = (5, 10, 20)


def load_retriever_module():
    spec = importlib.util.spec_from_file_location(
        "retrieve", ROOT / "05_retrieve" / "051_retrieve" / "retrieve.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def score_query(children: list[dict], q: dict) -> dict:
    slugs = [c["slug"] for c in children]
    gold = set(q["gold_entries"])
    req = set(q.get("required", q["gold_entries"]))
    first = next((i + 1 for i, s in enumerate(slugs) if s in gold), None)
    row = {"id": q["id"], "type": q["type"], "mrr": (1 / first) if first else 0.0}
    for k in KS:
        top = slugs[:k]
        row[f"hit@{k}"] = float(any(s in gold for s in top))
        row[f"cov@{k}"] = len(req & set(top)) / len(req)
    return row


def aggregate(rows: list[dict]) -> dict:
    keys = [k for k in rows[0] if k not in ("id", "type")]
    out = {"overall": {k: round(sum(r[k] for r in rows) / len(rows), 3) for k in keys}}
    for t in sorted({r["type"] for r in rows}):
        sub = [r for r in rows if r["type"] == t]
        out[t] = {k: round(sum(r[k] for r in sub) / len(sub), 3) for k in keys}
    return out


def main() -> None:
    rmod = load_retriever_module()
    queries = json.loads((ROOT / "07_eval" / "eval_set.json").read_text(encoding="utf-8"))["queries"]

    configs = {
        "A_dense": dict(use_rerank=False, use_graph=False),
        "B_rerank": dict(use_rerank=True, use_graph=False),
        "C_graph": dict(use_rerank=True, use_graph=True),
    }
    results = {}
    retr_cache = {}
    for name, cfg in configs.items():
        key = cfg["use_rerank"]
        retr = retr_cache.setdefault(key, rmod.Retriever(use_rerank=key))
        rows = [score_query(retr.retrieve(q["query"], use_graph=cfg["use_graph"])["children"], q)
                for q in queries]
        results[name] = {"per_query": rows, "agg": aggregate(rows)}
        a = results[name]["agg"]["overall"]
        print(f"\n[{name}] overall: " + "  ".join(f"{k}={a[k]}" for k in ("mrr", "hit@5", "hit@10", "cov@10")))
        for t in ("factoid", "synthesis", "comparison"):
            ta = results[name]["agg"][t]
            print(f"   {t:11} hit@10={ta['hit@10']} mrr={ta['mrr']} cov@10={ta['cov@10']}")

    out = ROOT / "data" / "eval"
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n-> data/eval/results.json")


if __name__ == "__main__":
    main()
