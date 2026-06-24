# 032 — small-to-big 청킹 + docstore  (이슈 #5)

031 구조 → 검색용 **child 청크** + 생성용 **parent(섹션) docstore**. small-to-big의 핵심.

## 실행 (repo 루트에서)
```bash
python 03_chunk/032_chunker/build_chunks.py                 # 기본 target 320 / overlap 48
python 03_chunk/032_chunker/build_chunks.py --target 256 --overlap 40
```
길이는 **Qwen3-Embedding 토크나이저** 기준(임베더와 동일).

## 입출력 (data/ gitignored)
- in : `data/structure/structure.jsonl`
- out: `data/chunks/children.jsonl` — child + 메타
- out: `data/docstore/parents.sqlite` — `parent_id → 섹션 본문`

## 규칙
- **parent = 섹션**(서브섹션 그대로, preamble 포함). **child = 문단 길이보정**: 짧은 문단 머지 / 긴 문단 문장경계 split / 섹션 내 overlap. child는 **섹션 경계 안 넘음**.
- child 메타: `id, text, tokens, slug, entry, author, section_id, section_path, level, url(#anchor), parent_id, first_published, last_modified, has_stripped_math`.
- `url`은 섹션 앵커까지 딥링크(예: `…/entries/camus/#ParCamAbs`) → 인용/원문 복귀의 핵심.

## 파라미터 (Phase 6에서 튜닝)
target 320 / overlap 48 (≈15%)은 베이스라인. PLAN §5의 측정값.

## 결과 (target 320 / overlap 48)
parents **31,371** / children **152,611** (avg 4.86/parent).
child 토큰: min 6 / p25 213 / median 271 / p75 316 / p95 382 / max 1585.
url 앵커 보유 94.1%(나머지는 preamble 등 → entry 최상단 링크).
※ 512토큰 초과 134개(0.09%)는 문장경계 없는 긴 나열문 — Qwen3 32K라 임베딩엔 무해, Phase 6에서 재검토 가능.
