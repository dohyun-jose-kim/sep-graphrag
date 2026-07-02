#!/usr/bin/env python3
"""092 — OpenAI 호환 셰임. 091 core(answer_turn) 위에 /v1/chat/completions를 얹어 LibreChat에 연결.

test_the_2_package 스파이크 shim.py 이식. OpenAI 스키마엔 sources/thinking/토글 칸이 없으므로:
- sources  → 답변 본문 끝 markdown 딥링크 목록
- thinking → message.reasoning_content (+ 스트리밍 시 delta.reasoning_content)
- search_q → 본문 상단 캡션 한 줄
- use_graph/show_think → 모델명 접미사 프리셋: `qwen3:14b+graph+think` (librechat.yaml modelSpecs가 라벨링)

프리셋은 config.json chatbot.models에서 자동 생성(모델 추가 시 셰임 수정 불요).
스트리밍은 pseudo-stream(전체 답 1청크) — 백엔드 ollama stream=False (스파이크 KL-04와 동일).

실행: .venv/bin/uvicorn shim:app --app-dir 09_chatbot-clone/092_librechat --host 0.0.0.0 --port 9001
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "091_core_api"))
from core import CFG, answer_turn  # noqa: E402


def build_presets(models: list[str]) -> list[str]:
    """모델별 +graph, qwen3 계열은 +think/+graph+think까지."""
    out = []
    for m in models:
        out += [m, f"{m}+graph"]
        if m.startswith("qwen3"):
            out += [f"{m}+think", f"{m}+graph+think"]
    return out


PRESETS = build_presets(CFG["models"])


def parse_model(name: str) -> tuple[str, bool, bool]:
    """`qwen3:14b+graph+think` → (base, use_graph, show_think)."""
    parts = name.split("+")
    base, flags = parts[0], set(parts[1:])
    return base, "graph" in flags, "think" in flags


def fold_content(ans: str, sources: list[dict], search_q: str, user_msg: str) -> str:
    head = f"*🔎 검색쿼리(맥락): {search_q}*\n\n" if search_q and search_q != user_msg else ""
    src = ""
    if sources:
        lines = "\n".join(f"- [{s['slug']} — {s['section_path']}]({s['url']})" for s in sources)
        src = f"\n\n**📖 출처 {len(sources)}개 (SEP 딥링크)**\n{lines}"
    return f"{head}{ans}{src}"


class ChatReq(BaseModel):
    model: str = ""
    messages: list[dict]
    stream: bool = False

    model_config = {"extra": "allow"}  # temperature 등 OpenAI 부가 파라미터 무시 허용


app = FastAPI(title="SEP GraphRAG — OpenAI-compat shim")


@app.get("/v1/models")
def list_models() -> dict:
    return {"object": "list",
            "data": [{"id": m, "object": "model", "owned_by": "sep-graphrag"} for m in PRESETS]}


def _run(req: ChatReq) -> tuple[str, str, str]:
    base, use_graph, show_think = parse_model(req.model or CFG["default_model"])
    user_msg = next((m["content"] for m in reversed(req.messages) if m.get("role") == "user"), "")
    res = answer_turn(req.messages, model=base, use_graph=use_graph, show_think=show_think)
    content = fold_content(res["ans"], res["sources"], res["search_q"], user_msg)
    return content, res["thinking"], req.model


@app.post("/v1/chat/completions")
def chat(req: ChatReq):
    content, thinking, model = _run(req)
    created = int(time.time())
    cid = f"chatcmpl-{created}"

    if not req.stream:
        msg = {"role": "assistant", "content": content}
        if thinking:
            msg["reasoning_content"] = thinking
        return {"id": cid, "object": "chat.completion", "created": created, "model": model,
                "choices": [{"index": 0, "message": msg, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}}

    def sse():
        def frame(delta, finish=None):
            return "data: " + json.dumps({
                "id": cid, "object": "chat.completion.chunk", "created": created, "model": model,
                "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}) + "\n\n"
        yield frame({"role": "assistant"})
        if thinking:
            yield frame({"reasoning_content": thinking})
        yield frame({"content": content})
        yield frame({}, finish="stop")
        yield "data: [DONE]\n\n"

    return StreamingResponse(sse(), media_type="text/event-stream")
