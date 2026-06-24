# 평가 설계 (Phase 6)

리트리벌 품질을 숫자로 재서 PLAN §5의 "측정해서 정할 값"들을 확정한다.
평가셋: [`07_eval/eval_set.json`](../07_eval/eval_set.json) (질문 + gold entry slug만, 저작권 무관, 커밋됨).

## 무엇을 측정하나
24개 쿼리, 3타입 — 각 retrieval 층을 겨냥:

| 타입 | 수 | 겨냥 | 성공 기준 |
|---|---|---|---|
| factoid | 11 | dense child 정밀도 | gold 중 1개라도 top-k |
| synthesis | 6 | small-to-big(parent 맥락) | gold 중 1개라도 top-k |
| comparison | 7 | graph 확장(멀티홉) | `required`의 **모든** entry가 top-k |

gold는 **entry 레벨**(slug). 잡힌 청크의 `slug`가 gold에 속하는지로 채점 → 견고하고 라벨링 쉬움.

## 지표
- **hit@k** — top-k 안에 gold entry 청크 ≥1 (factoid/synthesis 주 지표)
- **MRR** — 첫 gold-entry 청크의 역순위
- **coverage@k** — comparison에서 `required` entry 충족 비율 (예: camus·sartre 둘 다 잡혔나)
- 보조: nDCG@k

## 이 평가셋으로 가르는 결정 (PLAN §5)
1. **임베더 사이즈** — 0.6B(전체) vs 4B/8B(평가셋 subset만 임베딩해 비교) → 승자만 전체 재임베딩
2. **dense vs hybrid** — sparse 추가가 factoid hit@k 올리나
3. **child 청크 크기/overlap** — 재청킹 후 재측정
4. **MRL 차원** — 1024 vs 512 품질차
5. **graph on/off** — comparison coverage@k가 graph로 오르나 / factoid엔 노이즈인가 (켜고 끄고 분리 측정)

## 절차
1. 베이스라인: dense child top-k → hit@k/MRR (graph off)
2. + 리랭커 → 재측정
3. + small-to-big(parent 확장)은 생성 품질용이라 검색 지표엔 직접 안 잡힘 — 별도로 컨텍스트 적절성 체크
4. + graph 확장 → comparison coverage 변화 측정
5. 표로 비교 → 결정

## 한계 (PoC)
- 24쿼리는 지표용 출발점(통계적 엄밀 X). 경향 파악용.
- entry-level gold(섹션-level 아님) — small-to-big parent가 섹션은 알아서 확장.
- gold는 저자 판단 — 편향 가능. 필요시 확장/교차검토.
