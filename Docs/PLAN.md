# SEP GraphRAG — 초안 계획

> Stanford Encyclopedia of Philosophy(SEP)를 대상으로 한 **로컬** 벡터 검색 + QA 챗봇 + GraphRAG 실험.
> 포트폴리오/개인 학습용. 코드만 public, 데이터·인덱스는 로컬 전용.

---

## 진행 상태 (2026-06-25) — Phase 1–7 구현·검증 완료 ✅
entry 1,861 → child 152,611 → Qdrant 인덱싱 → dense+**rerank** 리트리벌(eval hit@10 **0.875**) → QA(Ollama qwen3/gemma) → Streamlit 챗봇.
그래프는 Neo4j 적재 + 시각화, **슬롯예약(comparison)으로 graph 확장 효과화**(#12, comparison cov 0.571→0.643).
실측으로 확정된 결정은 [`eval-design.md`](./eval-design.md) 우선(아래 §5·§6은 원안). 자율 실행 기록 [`autonomous-plan.md`](./autonomous-plan.md).
**미채택/보류**: hybrid(sparse), 4B/8B 전체 임베딩, MRL 차원축소 — rerank로 0.6B 충분해 보류.

---

## 0. 한눈에 보기

| 축 | 결정 |
|---|---|
| 용도 | 로컬 개인용 (공개 서비스 X) |
| 벡터DB | Qdrant, flat 단일 컬렉션 |
| 임베딩 | Qwen3-Embedding (0.6B → 4B → 8B 전부 비교) |
| 검색 방식 | dense **그리고** hybrid 둘 다 실험 |
| 리랭커 | Qwen3-Reranker (retrieve → rerank 2단계) |
| 청킹 | 문단 인식(paragraph-aware) + small-to-big |
| parent / child | parent = 서브섹션, child = 문단(길이 보정) |
| 생성 LLM | Gemma + Qwen 둘 다, **thinking off 기본** (Qwen은 trace 노출 옵션) |
| 코퍼스 | **전체 SEP 크롤** (~1,800–1,900 entry, 라이브 `/entries/`, robots 준수), 로컬 스냅샷(2026-06-24)으로 고정 |
| 수식/notation | **strip(제거) + 명시** — placeholder + 메타 플래그로 제거 사실 표시 |
| 그래프 | Related Entries = 방향 그래프 → 시각화 + GraphRAG(Type A) |
| GitHub | 코드만 public, 데이터/인덱스는 `.gitignore` |

---

## 1. 정책 / 저작권 (프로젝트의 전제)

SEP 본문은 무료지만 저작권이 살아있고, 핵심 금지사항은 **"인터넷을 통한 전자적 재배포"**.

- ✅ **로컬 개인용 RAG는 fair use 영역** — 긁어서 청킹·임베딩·로컬 검색 OK.
- ❌ **public repo에 SEP 본문/청크 커밋 = 재배포** — clone으로 본문이 통째로 새어나감.
- ❌ 공개 웹에 띄워서 본문을 그대로 토해내기 = 명백한 위반.
- ⚠️ blockquote(Camus/Knopf 번역본 인용 등)는 **이중 저작권**이라 제일 민감 → 독립 인덱싱 금지, 인접 분석 문단의 맥락으로만.

**가드레일 (코드에 내장):**
- 데이터·인덱스 전부 `.gitignore` (아래 §3).
- QA 답변은 **요약 + 짧은 인용 + 원문 섹션 딥링크** 형식 (본문 덤프 금지). 메타데이터의 `url#anchor`가 이 안전장치의 핵심.
- README에 "본문 미포함, 재현하려면 직접 스크래핑" 명시.

---

## 2. 스크래핑 매너 (반드시)

- **`robots.txt` 준수 (확인 완료, 2026-06-24):**
  - ❌ `/archives/` **Disallow** (모든 대소문자 조합) → 아카이브 에디션 크롤 금지.
  - ✅ `/entries/`, `/contents.html` 허용 → **라이브만 긁는다.**
  - ⏱️ `crawl-delay: 5` → 요청 간 **5초** 준수.
  - `ia_archiver` 전면 차단 = SEP가 아카이브 크롤을 명시적으로 원치 않음.
- `User-Agent` 명시.
- **전체(~1,900) 크롤 타이밍** — ~1,900 요청 @ 5s = 순수 지연만 ~2.6시간, retry/jitter 포함 **3~5시간**. 백그라운드 + checkpoint로.
- **checkpoint / resume 필수** — 진행 상태(완료 slug)를 디스크에 기록 → 중간에 죽어도 재개, 이미 받은 entry는 재요청 X. 한 번 긁어서 캐시.
- **재현성** — 아카이브 고정 대신 **로컬 스냅샷 + `snapshot_date`(2026-06-24) + entry별 fetched_at·SEP 최종수정일** 기록. (개정이 잦지 않으니 충분.)
- **공식 덤프/API 없음** → entry별 직접 스크래핑이 유일. 인터넷 아카이브 OCR 스캔본은 품질·저작권 애매 → 사용 금지.

---

## 3. Repo 구조 & gitignore

> 디렉터리 컨벤션 상세는 [`CLAUDE.md`](./CLAUDE.md) §3. 단계 폴더는 코드+문서를 함께 담고, 해당 작업 착수 시 생성한다.

```
sep-graphrag/
├── 01_setup/          # 환경·의존성·에디션 고정
├── 02_scrape/         # 스크래핑 + 그래프 (Phase 1)
│   ├── 021_contents_parser/
│   ├── 022_entry_fetcher/
│   └── 023_graph_builder/
├── 03_chunk/          # 문단인식 + small-to-big (Phase 2)
├── 04_embed/          # Qwen3 임베딩 → Qdrant (Phase 3)
├── 05_retrieve/       # 검색 + rerank + graph 확장 (Phase 4)
├── 06_qa/             # Gemma/Qwen 생성 (Phase 5)
├── 07_eval/           # MRR/NDCG 평가 (Phase 6)
├── Docs/              # PLAN.md, 결정 로그
├── data/              # gitignore (로컬 전용)
├── vectordb/          # gitignore
├── docstore/          # gitignore (parent 본문)
├── CLAUDE.md          # 작업 정책
├── README.md
└── .gitignore
```

`.gitignore` 핵심:
```gitignore
# SEP 원문 / 파생물 — 절대 커밋 X
data/
vectordb/
docstore/
*.faiss
*.sqlite3
*.jsonl
.env
.venv/
```

---

## 4. 단계별 실행 계획 (각 단계 = 검증 가능한 목표)

> 원칙: **벡터 + small-to-big 베이스라인부터 돌리고, 그래프 확장은 그 위에 얹어서 효과를 측정.**
> (먼저 다 합치면 뭐가 효과 있는지 분리가 안 됨.)

### Phase 0 — 셋업 & 스코프 확정
- repo 골격, `.gitignore`, 의존성 설치 (qdrant-client, transformers/sentence-transformers, beautifulsoup4, httpx, networkx, pyvis).
- **소스 고정:** robots 확인 → 라이브 `/entries/` + `config.json`에 `snapshot_date` 박제. (아카이브 폐기.)
- **검증:** 라이브 `/contents.html`에서 전체 slug 리스트 파싱 → 리다이렉트 스텁 제외한 실제 entry 수가 출력됨 (dry-run). 이게 크롤 대상 전체 목록.

### Phase 1 — 스크래핑 + 그래프 (한 번에)
- `scrape.py`: **전체 contents 목록 순회**. entry별 본문 HTML + **Related Entries** + 메타(저자, 발행/수정일, 섹션 앵커) 동시 수집. **"see X" 리다이렉트 스텁 제외.** checkpoint/resume(완료 slug 기록).
- `graph.py`: 전체 entry → related entries edgelist(json/csv), networkx로 degree/centrality(허브 entry 탐지) + community detection(주제 클러스터), pyvis 인터랙티브 HTML.
- **검증:** contents의 비-스텁 entry 전부 수집됨(완료 카운트 == 대상 카운트) / `graph.html` 렌더됨 / edgelist에 스텁 노드 없음 / 메타데이터(저자·날짜·앵커) 정상 추출.
- **개발 팁:** Phase 2~6 튜닝은 전체가 아니라 한 분야 **슬라이스**로 빠르게 반복 → 확정 후 전체에 배치.

### Phase 2 — 청킹 (문단 인식 + small-to-big)
- `chunk.py`: HTML 파싱(헤더/문단/blockquote 구분).
  - **parent = 서브섹션**, **child = 문단(길이 보정)**.
  - 섹션 경계 **절대 안 넘김**.
  - 짧은 문단 연속 → 목표 토큰까지 머지 / 너무 긴 문단 → 문장 경계 split.
  - blockquote → 인접 분석 문단에 흡수, 독립 인덱싱 X.
  - **수식/notation strip + 명시:** MathJax/LaTeX 노드 제거하되 **조용히 누락 금지** — 본문엔 `[MATH]` placeholder 삽입, 메타에 `has_stripped_math: true` 플래그. (검색·생성 양쪽에서 "여기 수식이 있었음"이 드러나야 함.)
  - 꼬리 섹션(Bibliography / Related Entries / Academic Tools) 제외.
  - 메타데이터 부착: `entry`, `section_path`, `url#anchor`, `author`, `date`, `parent_id`, `has_stripped_math`.
- parent 본문은 **docstore**에 `parent_id → text`로 보관 (Qdrant엔 child 벡터만).
- **검증:** 청크 수 합리적 / 어떤 청크도 entry 경계 안 넘음 / 모든 child에 `parent_id` + 메타 있음 / `parent_id`로 부모 본문 룩업됨.

### Phase 3 — 임베딩 & 인덱싱 (Qdrant)
- `embed.py`: Qwen3-Embedding로 **child만** 임베딩 → Qdrant 적재.
  - payload: `text`(child), `entry`, `section_path`, `url#anchor`, `parent_id`, `author`, `date`.
  - dense 컬렉션 먼저. **hybrid(sparse) 추가를 염두에 둔 스키마**로 설계.
  - instruction-aware: 태스크 instruction 영어로 부여.
- **검증:** 컬렉션 적재 완료 / 포인트 수 == child 수 / 샘플 유사도 검색이 말 되는 이웃 반환.

### Phase 4 — 리트리벌 (small-to-big + rerank + graph)
- `retrieve.py` 흐름:
  ```
  질문 → child dense 검색 top-k
       → Qwen3-Reranker로 rerank top-k
       → [small-to-big] 각 child의 부모 섹션으로 확장
       → [graph] 히트 entry의 Related 1홉 이웃 청크 추가 (옵션, 토글)
       → dedup
       → 컨텍스트
  ```
  - 베이스라인 수치(튜닝값): child top-20 → rerank top-5 → parent 확장 → dedup → 고유 parent 3~4개.
  - 그래프 확장은 1홉만, 이웃 청크도 재랭킹해서 상위 몇 개만 (확장 폭발 방지).
- **검증:** dedup된 parent 컨텍스트 + 출처(url#anchor) 반환 / graph on/off 토글 동작.

### Phase 5 — QA (Gemma + Qwen)
- `qa.py`: **모델 어댑터** 인터페이스 — 같은 retrieve 결과를 양쪽 모델에 먹임 (A/B 비교).
  - thinking **off 기본** (Qwen `enable_thinking=False`, Gemma는 native thinking 없음 → 분기 필요).
  - Qwen `<think>` trace를 화면에 노출하는 옵션 (Gemma엔 없는 비대칭 → UI에서 분기).
  - 프롬프트: **요약 + 짧은 인용 + 원문 섹션 딥링크** (본문 덤프 금지).
- **검증:** `python src/qa.py "질문"` 엔드투엔드 동작 / 양쪽 모델 답변 + 출처 인용.

### Phase 6 — 평가 & 튜닝
- `eval.py`: SEP 일부로 작은 평가셋(쿼리 + 기대 entry/섹션) → MRR/NDCG.
- 비교 매트릭스:
  - 임베더 사이즈 (0.6B vs 4B vs 8B)
  - dense vs hybrid
  - MRL 차원 (full vs 512 …)
  - child 청크 크기 / 오버랩
  - graph on vs off (멀티홉·비교 질문에서)
- **검증:** 평가 테이블 산출 → 아래 §5 "측정해서 정할 값"들을 **숫자로** 확정.

---

## 5. 측정해서 정할 값 (지금 못 박지 말 것)

| 항목 | 출발점 | 확정 방법 |
|---|---|---|
| 임베더 사이즈 | 0.6B 시작 | MRR/NDCG 비교 |
| child 청크 크기 / 오버랩 | 256~384 토큰 / 10~15% | 평가셋 실측 |
| 검색 파라미터 | child top-20 / rerank top-5 / parent 3~4 | 튜닝 |
| MRL 차원 | full | 용량 vs 품질 트레이드오프 |
| dense vs hybrid | dense 먼저 | 둘 다 측정 후 |
| graph 확장 | off로 베이스라인 | 효과 분리 측정 |

---

## 6. 아직 안 정한 설계 결정 (착수 전 필요)

1. **코퍼스 범위** — ✅ **전체 SEP 크롤 확정.** seed/홉 BFS 폐기 → `/contents.html` 전체 목록(스텁 제외) 순회. 저장 용량 ~1GB대로 무리 없음. 개발은 슬라이스, 전체는 배치.
2. **에디션/소스 고정** — ✅ **라이브 `/entries/` + 로컬 스냅샷 확정.** robots.txt가 `/archives/`를 Disallow → 아카이브 고정 폐기. 라이브를 crawl-delay 5초로 긁고 `snapshot_date`(2026-06-24) + entry별 fetched_at·최종수정일로 재현성 확보(개정 빈도 낮아 충분). 현 라이브 ≈ Summer 2026 Edition이라 `edition_label`로 기록.
3. **docstore 구현** — parent 본문을 sqlite / json / Qdrant 별도 컬렉션 중 어디에. *제안: sqlite.*
4. **hybrid sparse 방식** — Qdrant native BM25/SPLADE vs BGE-M3 sparse + RRF 융합 파라미터. *Phase 4로 defer 가능.*
5. **수식/notation 처리** — ✅ **strip + 명시 확정.** `[MATH]` placeholder + `has_stripped_math` 플래그로 제거 사실을 드러냄(조용한 누락 금지). 전체 크롤이라 논리·수리·물리철학 entry 다수 포함되므로 chunk.py에서 필수 처리.
6. **평가셋 구성** — 어느 entry, 몇 쿼리. *Phase 6에서 확정.*

---

## 7. 핵심 개념 메모

- **small-to-big**: 검색은 작은 child(정밀) ↔ LLM엔 큰 parent(맥락). 매칭 단위 ≠ 반환 단위. SEP는 섹션 구조가 깨끗해서 섹션이 곧 parent → coreference("그는…") 문제 자동 해결.
- **GraphRAG (Type A)**: 기존 그래프(Related Entries) 활용. 벡터(유사) + small-to-big(구조) + 그래프(관계) **세 겹**. 단일 사실 질문엔 그래프 끄고, 비교/멀티홉 질문에서만 켬.
  - (Type B = LLM으로 그래프 추출하는 MS GraphRAG식. SEP는 사람이 큐레이션한 그래프가 이미 있어서 불필요.)
```
