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
    "Use the conversation so far to resolve references like 'this' / 'it'. "
    "Answer concisely in the SAME language as the question, quote at most one short phrase per "
    "source, and cite each source by its URL. Do NOT reproduce long passages. "
    "If the context is insufficient, say so."
)


def load_retriever():
    spec = importlib.util.spec_from_file_location(
        "retrieve", ROOT / "05_retrieve" / "051_retrieve" / "retrieve.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.Retriever()


def build_prompt(query: str, parents: list[dict], history: list[dict] | None = None) -> str:
    ctx = "\n\n".join(
        f"[{i+1}] ({p['slug']} — {p['section_path']})\nSOURCE: {p['url']}\n{p['text'][:1800]}"
        for i, p in enumerate(parents)
    )
    convo = ""
    if history:
        turns = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history[-6:])
        convo = f"\n=== CONVERSATION SO FAR ===\n{turns}\n"
    return (f"{SYS}\n\n=== CONTEXT (SEP) ===\n{ctx}\n{convo}\n"
            f"=== CURRENT QUESTION ===\n{query}\n\n=== ANSWER (with source URLs) ===")


def ollama(model: str, prompt: str, think: bool | None = None) -> tuple[str, str]:
    """(answer, thinking) 반환. Ollama는 추론을 별도 'thinking' 필드로 준다.
    think: True/False면 API에 그대로 전달(qwen3 등 reasoning 모델), None이면 키 생략(gemma 등)."""
    payload = {"model": model, "prompt": prompt, "stream": False}
    if think is not None:
        payload["think"] = think
    r = httpx.post(OLLAMA, json=payload, timeout=600)
    r.raise_for_status()
    j = r.json()
    return j.get("response", "").strip(), (j.get("thinking") or "").strip()


def condense_query(history: list[dict], question: str, model: str = "gemma3:4b") -> str:
    """후속 질문을 대화 맥락 포함 standalone 영어 검색 쿼리로 재작성(검색 정확도용).
    history 없으면 그대로. 가벼운 모델(gemma3:4b) 사용."""
    if not history:
        return question
    convo = "\n".join(f"{m['role']}: {m['content']}" for m in history[-6:])
    p = (f"Conversation:\n{convo}\n\nFollow-up question: {question}\n\n"
         "Rewrite the follow-up as ONE standalone English search query that includes the needed "
         "context from the conversation (resolve 'this'/'it'). Output ONLY the query text.")
    try:
        q, _ = ollama(model, p, think=False if model.startswith("qwen3") else None)
        return q.strip().strip('"').splitlines()[0] or question
    except Exception:
        return question


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--graph", action="store_true")
    ap.add_argument("--think", action="store_true", help="qwen3 추론 과정 표시")
    ap.add_argument("--models", nargs="*", default=MODELS)
    a = ap.parse_args()

    res = load_retriever().retrieve(a.query, use_graph=a.graph)
    parents = res["parents"]
    print(f"\nQ: {a.query}\ncontext: {len(parents)} sections\n" + "=" * 60)
    for model in a.models:
        think = a.think if model.startswith("qwen3") else None
        try:
            ans, thinking = ollama(model, build_prompt(a.query, parents), think=think)
        except Exception as e:
            ans, thinking = f"[{model} 호출 실패: {e}]", ""
        print(f"\n### {model}")
        if thinking:
            print(f"<thinking>\n{thinking}\n</thinking>")
        print(ans)
    print("\n--- sources ---")
    for p in parents:
        print(f"  {p['url']}")


if __name__ == "__main__":
    main()
