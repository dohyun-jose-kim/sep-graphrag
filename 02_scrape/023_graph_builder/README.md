# 023 — Graph builder  (이슈 #3)

`data/metadata/entries_meta.json`의 `related_entries`로 **방향 그래프**를 만든다. GraphRAG(Type A)의 재료.

- **노드** = 전체 contents entry(1,861). **엣지** = entry → related entry (out-link).
- 메타가 부분만 있어도(크롤 진행 중) 있는 만큼으로 그린다 → 재실행 가능.

## 실행 (repo 루트에서)
```bash
python 02_scrape/022_entry_fetcher/extract_meta.py   # 메타 최신화
python 02_scrape/023_graph_builder/build_graph.py
```

## 출력 (data/graph/, gitignored)
| 파일 | 내용 |
|---|---|
| `edges.csv` | `source,target` edgelist |
| `graph.json` | networkx node-link (title/author/community/pagerank 속성) |
| `graph.html` | pyvis 인터랙티브 (커뮤니티별 색, degree별 크기) |
| `hubs.json` | PageRank·in-degree 상위 + 커뮤니티 요약 |

## 분석
- 중심성: PageRank, in-degree(가장 많이 참조되는 허브 entry)
- 커뮤니티: Louvain(무방향 투영) → 주제 클러스터
- 방향성 보존(DiGraph), 커뮤니티/시각화는 undirected로 접어서 계산

## 결과 (전체)
**1,861 노드 / 20,660 엣지 / 10 커뮤니티** (largest 352).
- 허브(PageRank/in-degree): kant, aristotle, plato, aquinas, descartes, hume, leibniz, consequentialism …
- 커뮤니티 = 주제 클러스터 (top 멤버):
  | # | size | 테마 |
  |---|---|---|
  | 0 | 352 | 정치·윤리 (consequentialism, liberalism, virtue, rawls) |
  | 4 | 296 | 고대·중세 (aristotle, plato, aquinas, ockham) |
  | 3 | 221 | 심리철학 (consciousness, physicalism, functionalism) |
  | 5 | 208 | 논리·수학 (russell, frege, set-theory, modal logic) |
  | 1 | 197 | 독일관념론·현상학 (kant, hegel, husserl, marx) |
  | 9 | 165 | 과학철학·확률 (bayesian, confirmation, induction) |
  | 6 | 156 | 근대 (hume, leibniz, descartes, locke, spinoza) |
  | 8 | 93 | 자유의지·물리 (freewill, qm, causation) |
  | 7 | 92 | 인식론 (knowledge, justification, skepticism) |
  | 2 | 81 | 중국철학 (daoism, mencius, confucius, mohism) |

전체 요약은 `data/graph/hubs.json`, 인터랙티브는 `data/graph/graph.html`.

## 그래프 추출 · 시각화 · Neo4j
| 스크립트 | 산출 |
|---|---|
| `visualize.py` | `community_map.png`(10클러스터 메타그래프), `hub_subgraph.png`(top35 허브), `full_graph.png`(전체 1,861 노드) |
| `to_neo4j.py` | Neo4j 적재: `(:Entry{slug,title,author,community,pagerank})-[:RELATED_TO]->(:Entry)` |
| `viz_neo4j.py` | `schema.svg`(스키마), `camus_2hop.svg`(Neo4j 쿼리 기반 2-hop, 155노드) |

**Neo4j 탐색** (`docker compose up -d neo4j` → http://localhost:7474, neo4j/sepgraph123):
```cypher
MATCH (c:Entry {slug:'camus'})-[:RELATED_TO*1..2]-(n) RETURN c,n   // 2-hop 네트워크
MATCH (e:Entry) RETURN e ORDER BY e.pagerank DESC LIMIT 20         // 허브
MATCH (e:Entry) RETURN e.community, count(*) ORDER BY 2 DESC       // 커뮤니티 크기
```
- 외부 임포트용 edgelist는 `edges.csv`(Gephi/Neo4j LOAD CSV).
