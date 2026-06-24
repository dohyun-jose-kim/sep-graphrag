# CLAUDE.md — SEP GraphRAG 작업 정책

이 리포에서 작업할 때의 규칙. 전역 `~/.claude/CLAUDE.md` 위에 프로젝트 규칙을 더한다.
설계 전반은 [`Docs/PLAN.md`](./Docs/PLAN.md).

## 0. 저작권 가드레일 (불변, 최우선)

- SEP 본문·청크·벡터 인덱스는 **절대 커밋 금지** (`.gitignore`). 코드만 버전관리한다.
- 현재 리포는 **private**. SEP 본문을 public으로 내보내는 어떤 행위도 금지.
- **robots.txt 준수** — `/archives/`는 Disallow라 **금지**, 라이브 `/entries/`·`/contents.html`만 사용. **crawl-delay 5초** 준수. 소스/재현성 설정은 `config.json`.
- QA 출력은 **요약 + 짧은 인용 + 원문 딥링크**. 본문 통째 덤프 금지.
- blockquote(원전 인용)는 독립 인덱싱 금지 — 인접 분석 문단의 맥락으로만.
- 수식은 strip하되 `[MATH]` placeholder + `has_stripped_math` 플래그로 **명시**(조용한 누락 금지).

## 1. 문서 운영 (착실히 유지)

| 파일 | 역할 | 갱신 시점 |
|---|---|---|
| `README.md` | 외부 시점 요약(스택·데이터 미포함 고지) | 스택/구조 큰 변화 시 |
| `CLAUDE.md` (이 파일) | 작업 정책 | 규칙이 바뀌면 **여기 먼저** |
| `Docs/PLAN.md` | 전체 설계·단계·검증 기준 | 결정이 바뀔 때마다 |
| `Docs/` | 설계·결정 로그·작업 노트 | 수시 |

**순서: 계획을 먼저 문서화 → 그 다음 구현.** 코드가 문서를 앞서지 않는다.

## 2. 이슈 주도 개발 (모든 실작업)

크롤링·청킹·임베딩 등 실제 작업은 **반드시** 이 순서를 따른다:

1. **이슈 발행** — 작업 단위 1개 = GitHub 이슈 1개. 제목 / 목표 / 검증 기준(완료 조건)을 적는다.
2. **커밋** — 작업하며 커밋. 메시지에 이슈를 참조한다. 진행 중 커밋은 `refs #N`.
3. **해결 명시** — 작업을 끝내는 커밋 메시지에 `Closes #N` (또는 PR 본문에).
4. **이슈 닫기** — 검증 기준 충족을 확인한 뒤 close. (3에서 자동 close되면 충족 여부만 확인.)

이슈 번호와 디렉터리 서브번호를 가능한 한 맞춘다 (이슈 #21 ↔ `02_scrape/021_*`).
정책·문서 셋업 같은 부트스트랩 작업은 이 규칙의 예외다.

## 3. 디렉터리 컨벤션

- **최상위 = 파이프라인 단계**, `NN_이름` prefix.
- **하위 = 서브스텝/이슈 단위**, `NNM_이름` (상위 번호 + 일련).
- 루트 직속: `CLAUDE.md`, `README.md`, `Docs/`, `.gitignore` (단계 폴더 밖).

```
01_setup/        # 환경·의존성·에디션 고정
02_scrape/       # 스크래핑 + 그래프 (Phase 1)
  021_contents_parser/
  022_entry_fetcher/
  023_graph_builder/
03_chunk/        # 문단인식 + small-to-big (Phase 2)
04_embed/        # Qwen3 임베딩 → Qdrant (Phase 3)
05_retrieve/     # 검색 + rerank + graph 확장 (Phase 4)
06_qa/           # Gemma/Qwen 생성 (Phase 5)
07_eval/         # MRR/NDCG 평가 (Phase 6)
Docs/            # PLAN.md, 결정 로그
```

- 단계 폴더는 **해당 작업 착수 시 생성**(이슈와 함께). 빈 폴더를 미리 만들지 않는다.

## 4. 커밋 규칙

- 한 커밋 = 한 논리 변경. 가능하면 이슈를 참조한다.
- 커밋 메시지 끝에 `Co-Authored-By: Claude ...` 라인.
- 초기엔 `main`에 직접. 협업/리뷰가 필요해지면 그때 브랜치를 도입한다.
