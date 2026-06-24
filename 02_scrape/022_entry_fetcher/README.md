# 022 — Entry fetcher  (이슈 #2)

contents의 1,861 entry를 받아 메타데이터를 정리한다. `related_entries`가 023 그래프의 엣지.

## 두 단계 (받기 / 정리)
1. **`fetch_entries.py`** — robots 준수(crawl-delay 5s + jitter) 크롤 → `data/raw/entries/<slug>.html` 저장.
   checkpoint = HTML 파일 존재 여부 → 중간에 죽어도 resume. 429/타임아웃 backoff retry.
2. **`extract_meta.py`** — 저장된 HTML에서 메타 추출(오프라인·재실행 가능) → `data/metadata/entries_meta.json`.

## 실행 (repo 루트에서)
```bash
python 02_scrape/022_entry_fetcher/fetch_entries.py --limit 5   # 슬라이스 검증
python 02_scrape/022_entry_fetcher/fetch_entries.py             # 전체 (~1,861, ~2.8h → 백그라운드 권장)
python 02_scrape/022_entry_fetcher/extract_meta.py              # 메타 추출(언제든 재실행)
```

## entry별 메타 필드
`slug, title, author, url, first_published, last_modified, copyright,`
`related_entries (→ 그래프 엣지), sections[{id,level,title}], snapshot_date`

페이지 구조: `#pubinfo`(날짜), `#related-entries`(`../<slug>/` 링크), `#article-copyright`,
`#main-text` 내 h2/h3 `id` 앵커(섹션). 꼬리(`#bibliography`,`#academic-tools`)는 청킹 단계에서 제외.

## 검증 (표본 14개, 크롤 진행 중)
related edges 140 / related 누락 0 / dangling 타깃(contents 미존재) 0 / 메타 추출 정상.
전체 완료 시 `entries parsed == 1,861` 확인 후 #2 종료.
