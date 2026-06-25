# 051 — 리트리벌  (이슈 #8)

`dense → [Qwen3-Reranker] → small-to-big(parent) → dedup → [graph 1홉]`. GraphRAG의 검색 코어.
`eval.py`(071)·`qa.py`(061)가 importlib로 `Retriever`를 재사용(번호 폴더라 일반 import 불가).

## 실행
```bash
python 05_retrieve/051_retrieve/retrieve.py "질문" [--graph]
```

## 흐름 / 파라미터
- query 인코딩(`prompt_name="query"`) → Qdrant dense top-50
- Qwen3-Reranker-0.6B(causal-LM yes/no, 실패 시 dense 폴백) → top-8
- 각 child의 parent(섹션)를 sqlite docstore에서 확장 → dedup → parent ~5
- `--graph`: 히트 entry의 1홉 이웃 slug로 필터검색 → 재랭크 합산(comparison용)

## 검증 (2026-06-25)
comparison 쿼리 "Camus vs Sartre" → 5 dedup parents + `url#anchor`, 리랭커 로드·동작,
graph 확장 동작. camus `#CriExi`(Criticism of Existentialists)를 정확히 surfaced.
