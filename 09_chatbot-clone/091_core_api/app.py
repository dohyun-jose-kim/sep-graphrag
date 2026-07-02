#!/usr/bin/env python3
"""091 — core API 서버. /api/turn 하나로 한 턴 왕복(단일 진실). 셰임(092)이 이 위에 얹힌다.

실행: .venv/bin/uvicorn app:app --app-dir 09_chatbot-clone/091_core_api --port 9000
전제: Qdrant docker(루트 compose) + Ollama 기동.
"""
from __future__ import annotations

from core import CFG, answer_turn, get_retriever
from fastapi import FastAPI
from pydantic import BaseModel


class TurnReq(BaseModel):
    messages: list[dict]
    model: str | None = None
    use_graph: bool = False
    show_think: bool = False


app = FastAPI(title="SEP GraphRAG core API")


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "models": CFG["models"]}


@app.post("/api/turn")
def turn(req: TurnReq) -> dict:
    return answer_turn(req.messages, model=req.model,
                       use_graph=req.use_graph, show_think=req.show_think)


@app.on_event("startup")
def warmup() -> None:
    get_retriever()  # 임베더/리랭커 선로딩 — 첫 질문 지연 방지
