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

## 상태
전체 크롤 완료 후 1,861 노드 + 전체 엣지로 최종 산출. (부분 실행은 검증용.)
