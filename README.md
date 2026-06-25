# SEP GraphRAG

Stanford Encyclopedia of Philosophy(SEP) 전체(~1,861 entry)를 대상으로 한 **로컬** 벡터 검색 + QA 챗봇 + GraphRAG 실험.
벡터 검색(dense + 리랭크) · small-to-big · Related-Entries 그래프(GraphRAG)를 한 파이프라인에 얹고, 평가셋으로 효과를 **측정**한다.

## 누구를 위한 것 / 무엇에 쓰나

- **철학을 공부하는 사람** — SEP 1,861개 항목에 자연어로 질문하면, 답변마다 **원문 섹션 딥링크**(`…/entries/camus/#CriExi`)로 바로 확인. 비교 질문("Camus vs Sartre")엔 그래프가 관련 항목까지 끌어온다.
- **RAG/GraphRAG를 배우는 개발자** — 스크래핑 → 청킹(small-to-big) → 임베딩 → Qdrant → 리랭크 → 그래프 확장 → QA → 평가 → UI 까지 **레퍼런스 구현**. 각 단계가 번호 폴더(`NN_단계/`)로 분리되고 단계별 README + 평가 수치가 붙어 있다.
- **포트폴리오** — 로컬에서 도는 end-to-end GraphRAG(+ Neo4j 그래프 탐색, Streamlit 챗봇). 데이터는 라이선스상 미포함, 코드로 재현.

> 명시적으로 **개인·로컬 사용 전제**다 (공개 배포 X — 아래 라이선스).

## ⚠️ 데이터 미포함 (라이선스)

SEP 본문은 저작권이 살아있고 **전자적 재배포가 금지**돼 있어, 이 리포에는 **코드만** 들어있고
긁은 본문·청크·벡터 인덱스는 일절 포함하지 않는다(`.gitignore` 처리). robots.txt 준수(`/archives/` 금지 → 라이브
`/entries/`만, crawl-delay 5s). 재현하려면 `02_scrape/`로 직접 스크래핑한다. QA 답변은 **요약 + 짧은 인용 + 딥링크**(본문 덤프 X).

## 사전 요구사항

- **OS/HW**: macOS Apple Silicon 권장(임베딩 MPS 가속). CPU도 동작(느림).
- **Docker**: Qdrant(+ Neo4j) 컨테이너.
- **Ollama** + 생성 모델: `ollama pull qwen3:14b gemma3:4b`.
- **Python 3.11 + [uv](https://github.com/astral-sh/uv)**.

## 처음부터 실행 (재현)

```bash
# 0) 셋업
uv venv && uv pip install -r 01_setup/requirements.txt
docker compose up -d qdrant            # 그래프 탐색까지면: ... up -d qdrant neo4j

# 1) 스크랩 + 그래프  (robots 준수 crawl-delay 5s, 전체 ~2.8h)
python 02_scrape/021_contents_parser/parse_contents.py     # entry 목록
python 02_scrape/022_entry_fetcher/fetch_entries.py        # 본문 크롤(resume 가능)
python 02_scrape/022_entry_fetcher/extract_meta.py         # 메타+related
python 02_scrape/023_graph_builder/build_graph.py          # 그래프/커뮤니티

# 2) 청킹 → 3) 임베딩 → 인덱싱
python 03_chunk/031_structure/extract_structure.py
python 03_chunk/032_chunker/build_chunks.py
python 04_embed/041_embed/embed_chunks.py                  # ~2.7h (MPS fp16)
python 04_embed/042_qdrant/index_qdrant.py

# 4) 검색 / 5) QA / 6) 평가 / 7) 챗봇
python 05_retrieve/051_retrieve/retrieve.py "What is the absurd for Camus?" [--graph]
python 06_qa/061_qa/qa.py "..."
python 07_eval/eval.py
streamlit run 08_chatbot/app.py                            # → http://localhost:8501
```
각 단계 상세는 해당 폴더의 README, 작업 정책은 [`CLAUDE.md`](./CLAUDE.md).

## 스택

- **벡터DB**: Qdrant (로컬 docker, named vector `dense`, hybrid 확장 여지)
- **임베딩**: Qwen3-Embedding-0.6B (MPS fp16). *4B/8B·hybrid·MRL은 rerank로 0.6B 충분해 보류*
- **리랭커**: Qwen3-Reranker-0.6B (causal-LM yes/no)
- **청킹**: 문단 인식 + small-to-big (parent=서브섹션, child=문단), 수식 strip
- **생성 LLM**: Ollama qwen3:14b · gemma3:4b (thinking off 기본)
- **그래프**: Related Entries 방향 그래프 → networkx/pyvis/Neo4j + GraphRAG(Type A)

## 파이프라인 (전 단계 동작 ✅)

```
02_scrape → 03_chunk → 04_embed → 05_retrieve → 06_qa → 07_eval → 08_chatbot
```

| 단계 | 산출물(로컬) |
|---|---|
| 02_scrape | entry 1,861 + 메타 + Related Entries 그래프(1,861노드·20,660엣지·10커뮤니티) |
| 03_chunk | child 152,611 / parent 31,371 (small-to-big, url#anchor 딥링크 97.4%) |
| 04_embed | Qwen3-Embedding-0.6B 임베딩(MPS fp16) → Qdrant |
| 05_retrieve | dense → Qwen3-Reranker → small-to-big → dedup → graph 슬롯예약(comparison) |
| 06_qa | Ollama qwen3:14b/gemma3:4b → 요약+인용+딥링크 |
| 07_eval | 24쿼리 평가 → **dense+rerank hit@10 0.875** (dense 0.667), graph로 comparison cov 0.571→0.643 |
| 08_chatbot | Streamlit UI (모델선택 · graph 토글 · thinking 토글 · SEP 출처 딥링크) |

평가 결과·결정은 [`Docs/eval-design.md`](./Docs/eval-design.md), 전체 설계는 [`Docs/PLAN.md`](./Docs/PLAN.md).

## 그래프 (GraphRAG 재료)

Related Entries는 방향 그래프 그 자체다. `build_graph.py`로 edgelist/커뮤니티/pyvis, `to_neo4j.py`로 Neo4j 적재.

```bash
docker compose up -d neo4j        # http://localhost:7474  (neo4j / sepgraph123)
python 02_scrape/023_graph_builder/to_neo4j.py
python 02_scrape/023_graph_builder/visualize.py     # community_map.png, hub_subgraph.png
python 02_scrape/023_graph_builder/viz_neo4j.py      # schema.svg, camus_2hop.svg
```
스냅샷·Cypher 예시는 [`02_scrape/023_graph_builder/README.md`](./02_scrape/023_graph_builder/README.md).
