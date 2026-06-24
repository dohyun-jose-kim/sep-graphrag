# 021 — Contents 파서  (이슈 #1)

라이브 `/contents.html`에서 SEP **실제 entry 목록**(스텁 제외)을 산출한다. → 022 크롤 대상.

## 실행
```bash
.venv/bin/python 02_scrape/021_contents_parser/parse_contents.py   # repo 루트에서
```
`config.json`(소스 URL·UA·snapshot_date)을 읽는다.

## 입출력 (data/ 는 gitignored)
| | 경로 | 내용 |
|---|---|---|
| in  | `https://plato.stanford.edu/contents.html` | 없으면 `data/raw/contents.html`로 캐시 |
| out | `data/contents/entries.json` | 실제 entry `[{slug,title,author,url}]` |
| out | `data/contents/aliases.json` | 제외된 "see" cross-reference `[{alias,target_slug}]` |

## 스텁 판별
`<a>`가 `<strong>`을 감싸면 실제 entry. "see" 링크(`<strong>` 없음)는 다른 entry를 가리키는
cross-reference라 제외. 검증: "see" 타깃 553개가 모두 실제 entry에도 존재 → orphan 0.

## 결과 (2026-06-24, Summer 2026 Edition)
총 entry-link 2,511 → **실제 entry 1,861**, "see" 스텁 650 제외, 저자 누락 0.
