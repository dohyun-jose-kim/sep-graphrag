# 041 — child 임베딩 (Qwen3-Embedding-0.6B, MPS)  (이슈 #6)

152,611 child를 Qwen3-Embedding-0.6B로 인코딩 → 벡터 저장. → 042 입력.

## 실행 (repo 루트에서)
```bash
python 04_embed/041_embed/embed_chunks.py --limit 200   # 슬라이스 검증
python 04_embed/041_embed/embed_chunks.py               # 전체(~152k, 백그라운드 권장)
```

## 입출력 (data/ gitignored)
- in : `data/chunks/children.jsonl`
- out: `data/embeddings/0.6B/vectors_NNN.npy` (shard 10k) + `ids.json`(children 순서)

## 규칙
- **문서(child)는 instruction 없이** 인코딩(Qwen3 권장). 쿼리는 검색단에서 `prompt_name="query"`.
- `normalize_embeddings=True`(코사인). dim 1024. `max_seq_length=2048`(최대 청크 1585 tok 안 잘림).
- **shard 단위 저장 → checkpoint/resume**(있는 shard 스킵). device 기본 `mps`.

## 전략
0.6B로 **전체** 임베딩(베이스라인). 4B/8B는 평가셋 subset에서만 비교(Phase 6) 후 승자만 전체 재임베딩.

## 슬라이스 검증
200 child → (200,1024) 정상. MPS 동작 확인.
