#!/usr/bin/env python3
"""061 — QA 생성. retrieval context → Ollama 생성(thinking off) → 요약+인용+딥링크.

저작권: 본문 통째 덤프 금지. 요약 + 짧은 인용 + url#anchor 출처.
CLI: python 06_qa/061_qa/qa.py "질문" [--graph] [--model qwen3:14b]
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
OLLAMA = "http://localhost:11434/api/generate"
MODELS = ["qwen3:14b", "gemma3:4b"]  # A/B. qwen3는 /no_think로 thinking off

SYS = (
    "You answer questions about philosophy using ONLY the provided SEP context. "
    "Give a concise answer, quote at most one short phrase per source, and cite each "
    "source by its URL. Do NOT reproduce long passages. If the context is insufficient, say so."
)


def load_retriever():
    spec = importlib.util.spec_from_file_location(
        "retrieve", ROOT / "05_retrieve" / "051_retrieve" / "retrieve.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.Retriever()


def build_prompt(query: str, parents: list[dict], no_think: bool) -> str:
    ctx = "\n\n".join(
        f"[{i+1}] ({p['slug']} — {p['section_path']})\nSOURCE: {p['url']}\n{p['text'][:1800]}"
        for i, p in enumerate(parents)
    )
    prefix = "/no_think\n" if no_think else ""
    return f"{prefix}{SYS}\n\n=== CONTEXT ===\n{ctx}\n\n=== QUESTION ===\n{query}\n\n=== ANSWER (with source URLs) ==="


def ollama(model: str, prompt: str) -> str:
    r = httpx.post(OLLAMA, json={"model": model, "prompt": prompt, "stream": False}, timeout=600)
    r.raise_for_status()
    return r.json().get("response", "").strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--graph", action="store_true")
    ap.add_argument("--models", nargs="*", default=MODELS)
    a = ap.parse_args()

    res = load_retriever().retrieve(a.query, use_graph=a.graph)
    parents = res["parents"]
    print(f"\nQ: {a.query}\ncontext: {len(parents)} sections\n" + "=" * 60)
    for model in a.models:
        prompt = build_prompt(a.query, parents, no_think=model.startswith("qwen3"))
        try:
            ans = ollama(model, prompt)
        except Exception as e:
            ans = f"[{model} 호출 실패: {e}]"
        print(f"\n### {model}\n{ans}")
    print("\n--- sources ---")
    for p in parents:
        print(f"  {p['url']}")


if __name__ == "__main__":
    main()
