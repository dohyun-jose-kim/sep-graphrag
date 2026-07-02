#!/usr/bin/env python3
"""091 — 한 턴 코어. Streamlit(081) 계약 `{ans, thinking, sources, search_q}`를 그대로 반환.

test_the_2_package 스파이크 core.py 이식 — 차이는 하나: retrieve가 스텁이 아니라
실제 051 Retriever(Qdrant 인덱스 + rerank + graph 1홉)다. 백엔드(051/061)는 importlib 재사용만, 수정 0.
"""
from __future__ import annotations

import importlib.util
import json
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))["chatbot"]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


qa = _load("qa", "06_qa/061_qa/qa.py")

_retriever = None
_lock = threading.Lock()


def get_retriever():
    """Retriever는 무거움(임베더+리랭커 로드) — 첫 요청에 1회 생성 후 재사용."""
    global _retriever
    with _lock:
        if _retriever is None:
            retr_mod = _load("retrieve", "05_retrieve/051_retrieve/retrieve.py")
            _retriever = retr_mod.Retriever()
    return _retriever


def answer_turn(messages: list[dict], model: str | None = None,
                use_graph: bool = False, show_think: bool = False) -> dict:
    """messages=[{role,content}...], 마지막이 현재 질문."""
    if not messages:
        raise ValueError("messages가 비어있음")
    model = model or CFG["default_model"]
    history = messages[:-1]
    prompt = messages[-1]["content"]
    search_q = qa.condense_query(history, prompt, model=CFG["condense_model"])
    parents = get_retriever().retrieve(search_q, use_graph=use_graph)["parents"]
    think = show_think if model.startswith("qwen3") else None  # gemma는 think 키 생략(081 계약)
    ans, thinking = qa.ollama(model, qa.build_prompt(prompt, parents, history), think=think)
    sources = [{"slug": p["slug"], "section_path": p["section_path"], "url": p["url"]} for p in parents]
    return {"ans": ans, "thinking": thinking, "sources": sources, "search_q": search_q}
