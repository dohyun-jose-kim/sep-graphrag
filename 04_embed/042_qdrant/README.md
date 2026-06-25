# 042 — Qdrant 로컬 인덱싱  (이슈 #7)

041 벡터 + children payload → Qdrant 컬렉션 upsert + 샘플 검색.

## 실행 (repo 루트에서)
```bash
python 04_embed/042_qdrant/index_qdrant.py
```
`config.qdrant.mode`: `server`(docker, 현재) | `local`(파일모드). `make_client()`가 분기.

## 스키마
- named vector **`dense`** (size 1024, cosine) — 나중에 `sparse` 추가해도 안 깨짐(hybrid-ready).
- payload: `chunk_id, slug, entry, author, section_path, url(#anchor), parent_id, level, has_stripped_math, tokens, text`.
- point id = children 순서 정수, `chunk_id`는 payload에.

## 검증
collection count == children(~152,611), 샘플 쿼리 top-5가 말 되는지.
