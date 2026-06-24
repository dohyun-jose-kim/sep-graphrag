# 자율 진행 런북 (임베딩 완료 후 → Phase 끝까지)

> **트리거**: 백그라운드 임베딩(`b0a4tlyqa`, `data/embeddings/0.6B/`) 완료 알림 시 이 파일을 읽고 순서대로 실행.
> 사용자는 자리 비움 → **블로킹 질문 금지, 결정은 아래대로, 각 단계 검증 후 커밋·이슈처리.**
> **원칙**: 단계마다 작동하면 즉시 커밋(롤백 가능). 어려운 단계(리랭커 등)가 막히면 **건너뛰고 베이스라인을 먼저 완성**, 막힌 건 노트로 남기고 계속.

## 상태 체크 (wake 시 먼저)
```bash
ls data/embeddings/0.6B/vectors_*.npy | wc -l         # 16이면 임베딩 완료
.venv/bin/python -c "from qdrant_client import QdrantClient as Q; print(Q(url='http://localhost:6333').get_collections())"
docker ps | grep qdrant                                # 없으면: docker compose up -d qdrant
```
완료된 단계는 산출물 존재로 판단하고 **건너뛴다**(idempotent).

## 사전 확정된 결정
- 임베더: Qwen3-Embedding-0.6B (전체). 4B/8B 비교는 시간/여력 남으면 평가셋 subset만.
- 리랭커: Qwen3-Reranker-0.6B. **로딩 까다로우면 dense-only로 폴백**하고 노트 남김(블로킹 금지).
- 생성 LLM: Ollama `qwen3:14b`(thinking off=프롬프트에 `/no_think`) + `gemma3:4b`. 로컬 `localhost:11434`.
- 검색 파라미터(베이스라인): child top-k=50 → 리랭크 top-8 → parent 확장(docstore) → dedup → parent ~5. graph는 comparison에서만 1홉, 베이스라인 eval은 graph OFF.
- 출력(QA): 요약 + 짧은 인용 + `url#anchor` 딥링크. 본문 덤프 금지(저작권).

## 실행 순서

### STEP 1 — 042 Qdrant 인덱싱 (#6, #7)
```bash
.venv/bin/python 04_embed/042_qdrant/index_qdrant.py
```
- 검증: collection count == children 수(~152,611), 샘플 쿼리 top-5가 말 되는지(camus 등).
- 16 shard 확인되면 **#6 close**(임베딩 완료), 인덱싱 검증되면 **#7 close**.
- 042 README 작성 + 커밋(`Closes #6` 별도/`Closes #7`).

### STEP 2 — Phase 4 리트리벌 (#8)  — `05_retrieve/051_retrieve/retrieve.py`
흐름: query 인코딩(prompt_name="query") → Qdrant dense top-50 → [리랭크 top-8] → parent 확장(sqlite docstore) → dedup → [graph 1홉 옵션] → context.
- 검증: 샘플 쿼리에 dedup된 parent 컨텍스트 + 출처(url) 반환. graph on/off 토글 동작.
- 리랭커 막히면 dense 순서로 진행 + 노트. 커밋(`refs #8`), 검증되면 close.

### STEP 3 — Phase 6 평가 (#10)  — `07_eval/eval.py`
`eval_set.json` 로드 → 각 쿼리 retrieval → hit@k(any gold), MRR, coverage@k(comparison required). 
- 설정 비교: (A) dense, (B) dense+rerank, (C) +graph. k=5/10/20.
- 출력: `data/eval/results.json` + 콘솔 표. README/Docs에 수치 기록. 커밋(`Closes #10`).
- 이 표로 PLAN §5 결정(임베더/hybrid/graph on-off) 1차 판단을 Docs/eval-design.md에 추가.

### STEP 4 — Phase 5 QA (#9)  — `06_qa/061_qa/qa.py`
retrieval context → Ollama 생성(qwen3:14b /no_think, gemma3:4b) → 요약+인용+딥링크.
- 검증: `python 06_qa/061_qa/qa.py "질문"` 엔드투엔드, 양 모델 답변 + 출처. 커밋(`Closes #9`).

### STEP 5 — 마무리
- README 갱신(파이프라인 완성 상태), Phase 6 결과 요약을 Docs에.
- 열린 이슈 정리, 최종 커밋·푸시.
- (옵션) graph.html 아티팩트, 4B/8B subset 비교 — 여력 남으면.

## 폴백 규칙
- 스크립트 에러 → 디버그하되 30분 이상 한 단계에 묶이면 그 단계 **노트 남기고 다음으로**. 핵심은 end-to-end 베이스라인 완성.
- Ollama 미응답 → `ollama serve` 확인 / 모델명 `ollama list`로 교정.
- Qdrant 미응답 → `docker compose up -d qdrant` 후 재시도.
- 커밋은 **세부 분리**(CLAUDE.md §4). 데이터 커밋 금지(.gitignore 확인).
- 각 단계 완료 시 사용자에게 보고 누적(다음 메시지에 진행상황 요약).
```
