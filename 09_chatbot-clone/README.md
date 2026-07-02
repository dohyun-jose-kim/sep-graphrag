# 09 — 챗봇 v2 (LibreChat)

08_chatbot(Streamlit)의 후속. LibreChat을 껍데기로 쓰고, 백엔드(051 retrieve + 061 qa)는 그대로 재사용.
설계와 결정 배경: [`Docs/plan-09-librechat.md`](../Docs/plan-09-librechat.md).

```
091_core_api/   answer_turn 코어 (FastAPI :9000, /api/turn) — 계약 {ans, thinking, sources, search_q}
092_librechat/  OpenAI-compat 셰임(:9001) + librechat.yaml + docker-compose (LibreChat :3080 + Mongo)
LibreChat/      upstream 소스 클론 — 참조 전용, gitignored (실행은 docker 이미지)
```

## 실행 (순서대로)

```bash
docker compose up -d qdrant                    # 1. 데이터 인프라 (루트 compose)
# Ollama 실행 중이어야 함 (qwen3:32b/14b, gemma3:4b)

.venv/bin/uvicorn app:app  --app-dir 09_chatbot-clone/091_core_api  --port 9000 &   # 2. 코어
.venv/bin/uvicorn shim:app --app-dir 09_chatbot-clone/092_librechat --host 0.0.0.0 --port 9001 &  # 3. 셰임

cd 09_chatbot-clone/092_librechat              # 4. UI 스택 (.env는 .env.example 참고해 생성)
docker compose up -d                           #    → http://localhost:3080 (첫 사용 시 계정 등록)
```

- 모델 목록의 단일 진실은 루트 `config.json`의 `chatbot.models` — 추가하면 셰임 프리셋 자동 반영
  (librechat.yaml의 models/modelSpecs만 손으로 맞춰주면 됨).
- graph/think 토글은 모델 프리셋 접미사(`+graph`/`+think`)로 전달 — UI에는 modelSpecs 카드 10개로 노출.
- 저작권 가드레일 동일: 요약 + 짧은 인용 + SEP 딥링크. 대화는 로컬 Mongo 볼륨에만 저장.
