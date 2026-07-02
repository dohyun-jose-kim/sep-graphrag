# plan-09 — 챗봇 v2: Streamlit → LibreChat (09_chatbot-clone)

> 작성: 2026-07-02 · 근거: `test_the_2_package` 스파이크(외부 리포, LibreChat vs assistant-ui 비교)
> 결정(사용자, 2026-07-02): **LibreChat 채택** · **docker 이미지 + config 방식**(소스 클론은 참조용) · 08_chatbot(Streamlit)은 레거시로 유지 · 루트 compose/config는 "루트 유지 + 챗봇 스택 분리"로 정리.

## 0. 목적

08_chatbot(Streamlit, 로컬 단일유저)을 LibreChat 기반 v2로 교체한다. 스파이크에서 검증된 Path A
(코어 API → OpenAI-compat 셰임 → LibreChat 커스텀 엔드포인트)를 이식하되, 스파이크와의 차이는 하나:
**retrieve가 스텁이 아니라 실제**(051 Retriever + Qdrant 인덱스 + 그래프)다.

## 1. 아키텍처

```
05_retrieve/051 (Retriever) + 06_qa/061 (qa.py)     ← 기존 백엔드, 수정 없음(재사용만)
                  │ importlib
        ┌─────────▼──────────┐
        │ 091_core_api        │  answer_turn(messages, model, use_graph, show_think)
        │ (FastAPI :9000)     │  → {ans, thinking, sources[], search_q}   ← 스파이크와 동일 계약
        └─────────┬──────────┘
        OpenAI-compat 셰임 (:9001, /v1/chat/completions·/v1/models·SSE)
                  │
        LibreChat (docker 이미지 :3080) + Mongo — librechat.yaml로 연결
```

- 토글(use_graph/show_think)은 OpenAI 스키마에 칸이 없으므로 스파이크 방식 그대로 **모델 프리셋 접미사**
  (`qwen3:14b+graph+think`)로 전달하고, `modelSpecs` 카드로 라벨링해 어색함을 완화한다.
- sources → 본문 끝 markdown 딥링크 목록, thinking → `reasoning_content`, search_q → 본문 상단 캡션 (스파이크 검증 완료).

## 2. 디렉터리

```
09_chatbot-clone/
  LibreChat/           # upstream 소스 클론 — 참조 전용, gitignore (자체 .git 보유)
  091_core_api/        # core.py(answer_turn, 실제 retrieve) + app.py(FastAPI /api/turn)
  092_librechat/       # shim.py + librechat.yaml + docker-compose.yml + .env.example
  README.md
```

## 3. 이슈 계획 (각 이슈 = 검증 기준 포함)

| 이슈 | 내용 | 검증 기준 |
|---|---|---|
| #20 루트 정리 | config.json 구획 정리 + `chatbot` 섹션 신설(모델 목록 단일 진실 — 스파이크 §6에서 지적된 app.py/qa.py 모델 불일치 해소). 루트 docker-compose는 데이터 인프라(qdrant/neo4j) 전용임을 명시. `.gitignore`에 LibreChat 클론 추가. | config.json 소비자(retrieve/embed 등) 동작 불변(pytest), `git status`에 LibreChat/ 미노출 |
| #21 091 core API | 스파이크 core.py 이식, stub_retrieve → 실제 Retriever. 모델 목록은 config.json `chatbot`에서. | `curl /api/turn` 단일턴이 4키 계약 + **실제 SEP 출처** 반환 / 멀티턴 search_q 재작성 / use_graph 시 이웃 entry 출처 추가 |
| #22 092 LibreChat | 스파이크 shim.py + custom variant의 librechat.yaml(modelSpecs 카드·브랜딩·메뉴 정리) + docker-compose(mongo+librechat 이미지) 이식. README 갱신(09가 기본, 08은 레거시). | 셰임 `/v1/models`·비스트림·SSE curl OK / LibreChat `/api/config`에 엔드포인트+스펙 노출 / 컨테이너→셰임 도달 / 고정 질문 3개(스파이크 §5) 육안 확인 |

## 4. 모델 프리셋 (config.json `chatbot.models`가 단일 진실)

로컬 Ollama 보유: qwen3:32b/14b, gemma4:31b/26b, gemma3:4b/1b, exaone3.5:32b.
프리셋 폭발 방지를 위해 **qwen3:32b(고품질) · qwen3:14b(균형, 기본) · gemma3:4b(빠름)** 3종 × 플래그만 노출:
qwen3 계열은 `+graph`/`+think`/`+graph+think`, gemma는 `+graph`. (나머지 모델은 config에 추가하면 셰임이 자동 반영.)

## 5. 저작권/운영 주의

- 셰임 출력은 기존과 동일: 요약 + 짧은 인용 + SEP 딥링크. 본문 덤프 없음.
- LibreChat은 대화를 Mongo에 저장 — **로컬 전용**, mongo 볼륨은 gitignore 영역(도커 볼륨).
- LibreChat/Mongo/셰임/코어 모두 로컬 포트 바인딩만. 외부 노출 없음.

## 6. 범위 밖

토큰 단위 스트리밍(백엔드 ollama가 stream=False — 스파이크 KL-04와 동일), LibreChat 소스 커스텀(필요해지면
클론이 참조용으로 있음), 멀티유저/인증 튜닝, assistant-ui 경로.
