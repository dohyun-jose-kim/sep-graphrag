# 031 — HTML 구조 추출  (이슈 #4)

저장된 entry HTML → 청킹 가능한 **구조화 텍스트**(JSONL). → 032 입력.

## 실행 (repo 루트에서)
```bash
python 03_chunk/031_structure/extract_structure.py
```

## 입출력 (data/ gitignored)
- in : `data/raw/entries/*.html`, `data/metadata/entries_meta.json`
- out: `data/structure/structure.jsonl` (entry당 1줄)

## entry 구조
```
{slug, url, title, author, first_published, last_modified, has_stripped_math,
 sections: [{id, level, title, paragraphs: [...]}]}
```

## 처리 규칙
- `#preamble`(intro) + `#main-text`(번호 섹션)만. 꼬리(bibliography/academic-tools/related-entries)는 별도 div라 자동 제외.
- 수식 `\(..\)`,`\[..\]` → `[MATH]` + `has_stripped_math` (제목·본문 모두).
- blockquote(원전 인용) → 직전 문단 흡수(독립 인덱싱 X) → 저작권/문맥 둘 다 안전.
- 섹션 경계 보존: 문단이 소속 섹션(id/level/title)에 매핑, 경계 안 넘김.

## 결과
entries 1,861 / sections 31,371(avg 16.9) / paragraphs 181,803(avg 97.7) / 수식 450 entry / 0 broken.
