PY := .venv/bin/python
.DEFAULT_GOAL := help
.PHONY: help setup up down healthcheck contents fetch meta graph neo4j chunk embed index eval chat retrieve lint test

help:  ## 타깃 목록
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/\t/' | sort

setup:  ## venv + 의존성 설치
	uv venv && VIRTUAL_ENV=$(PWD)/.venv uv pip install -r 01_setup/requirements.txt

up:  ## Qdrant + Neo4j 컨테이너 기동
	docker compose up -d qdrant neo4j

down:  ## 컨테이너 정지
	docker compose down

healthcheck:  ## 서비스/데이터 상태 점검
	$(PY) 01_setup/healthcheck.py

contents:  ## Phase1: contents 파싱 (entry 목록)
	$(PY) 02_scrape/021_contents_parser/parse_contents.py

fetch:  ## Phase1: 전체 entry 크롤 (~2.8h, robots 준수)
	$(PY) 02_scrape/022_entry_fetcher/fetch_entries.py

meta:  ## Phase1: 메타데이터 추출
	$(PY) 02_scrape/022_entry_fetcher/extract_meta.py

graph:  ## Phase1: Related Entries 그래프 빌드
	$(PY) 02_scrape/023_graph_builder/build_graph.py

neo4j:  ## Phase1: 그래프 Neo4j 적재
	$(PY) 02_scrape/023_graph_builder/to_neo4j.py

chunk:  ## Phase2: 구조추출 + small-to-big 청킹
	$(PY) 03_chunk/031_structure/extract_structure.py && $(PY) 03_chunk/032_chunker/build_chunks.py

embed:  ## Phase3: 임베딩 (~2.7h, MPS)
	$(PY) 04_embed/041_embed/embed_chunks.py

index:  ## Phase3: Qdrant 인덱싱
	$(PY) 04_embed/042_qdrant/index_qdrant.py

retrieve:  ## Phase4: 검색 (Q="질문" [--graph는 직접])
	$(PY) 05_retrieve/051_retrieve/retrieve.py "$(Q)"

eval:  ## Phase6: 평가 (hit@k/MRR/coverage)
	$(PY) 07_eval/eval.py

chat:  ## Phase7: 챗봇 (http://localhost:8501)
	.venv/bin/streamlit run 08_chatbot/app.py --server.fileWatcherType none

lint:  ## ruff 검사
	.venv/bin/ruff check .

test:  ## pytest
	.venv/bin/pytest -q
