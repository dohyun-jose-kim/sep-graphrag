# SEP GraphRAG

Stanford Encyclopedia of Philosophy(SEP) 전체를 대상으로 한 **로컬** 벡터 검색 + QA + GraphRAG 실험.
개인 학습/포트폴리오용. 설계·진행 상황은 [`Docs/PLAN.md`](./Docs/PLAN.md), 작업 정책은 [`CLAUDE.md`](./CLAUDE.md) 참고.

## ⚠️ 데이터 미포함 (라이선스)

SEP 본문은 저작권이 살아있고 **전자적 재배포가 금지**돼 있어, 이 리포에는 **코드만** 들어있고
긁은 본문·청크·벡터 인덱스는 일절 포함하지 않는다(`.gitignore` 처리).
재현하려면 `02_scrape/`의 스크래퍼로 직접 스크래핑해야 한다. 본 프로젝트는 로컬 개인 사용 전제다.

## 스택

- **벡터DB**: Qdrant (flat 단일 컬렉션)
- **임베딩**: Qwen3-Embedding (0.6B / 4B / 8B 비교), dense + hybrid
- **리랭커**: Qwen3-Reranker
- **청킹**: 문단 인식(paragraph-aware) + small-to-big (parent=서브섹션, child=문단)
- **생성 LLM**: Gemma · Qwen (thinking off 기본)
- **그래프**: Related Entries 방향 그래프 → 시각화 + GraphRAG(Type A)

## 파이프라인 (전 단계 동작 ✅)

```
02_scrape → 03_chunk → 04_embed → 05_retrieve → 06_qa → 07_eval → 08_chatbot
```

| 단계 | 산출물(로컬) |
|---|---|
| 02_scrape | entry 1,861 + 메타 + Related Entries 그래프(1,861노드·20,660엣지·10커뮤니티) |
| 03_chunk | child 152,611 / parent 31,371 (small-to-big, url#anchor 딥링크 97.4%) |
| 04_embed | Qwen3-Embedding-0.6B 임베딩(MPS fp16) → Qdrant(docker) |
| 05_retrieve | dense → Qwen3-Reranker → small-to-big → dedup → graph 1홉 |
| 06_qa | Ollama qwen3:14b/gemma3:4b → 요약+인용+딥링크 |
| 07_eval | 24쿼리 평가 → **dense+rerank hit@10 0.875** (dense 0.667) |
| 08_chatbot | Streamlit UI (모델선택 · graph 토글 · SEP 출처 딥링크) |

**실행**: `docker compose up -d qdrant` → `streamlit run 08_chatbot/app.py` (Ollama 필요).

평가 결과·결정은 [`Docs/eval-design.md`](./Docs/eval-design.md), 전체 설계는 [`Docs/PLAN.md`](./Docs/PLAN.md).
GraphRAG 그래프 확장은 현재 no-op(지배 entity 점유) → 이웃 슬롯 예약이 후속 과제(eval-design 참고).
