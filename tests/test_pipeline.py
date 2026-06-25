"""파이프라인 순수 로직 단위테스트.

번호 폴더(01_setup 등)는 Python 패키지가 아니라 importlib로 모듈을 로드한다.
서비스/대용량 데이터 없이 동작하는 함수만 대상(모듈은 import-safe하게 가드됨).
"""
import importlib.util
import subprocess
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


struct = _load("struct", "03_chunk/031_structure/extract_structure.py")
chunker = _load("chunker", "03_chunk/032_chunker/build_chunks.py")  # 토크나이저 로드(캐시)
qa = _load("qa", "06_qa/061_qa/qa.py")
contents = _load("contents", "02_scrape/021_contents_parser/parse_contents.py")


# --- 031 수식 strip ---
def test_strip_math_replaces_and_flags():
    out, had = struct.strip_math(r"sets \(A\) and \(B\) differ")
    assert "[MATH]" in out and "\\(" not in out and had is True
    assert struct.strip_math("plain prose") == ("plain prose", False)


# --- 031 섹션 앵커(<a name> fallback — 과거 버그) ---
def test_header_id_resolves_anchor():
    assert struct.header_id(BeautifulSoup('<h2><a name="ParCamAbs">1. T</a></h2>', "lxml").h2) == "ParCamAbs"
    assert struct.header_id(BeautifulSoup('<h2 id="Direct">x</h2>', "lxml").h2) == "Direct"
    assert struct.header_id(BeautifulSoup("<h3>no anchor</h3>", "lxml").h3) is None


# --- 021 저자 추출 ---
def test_extract_author():
    li = BeautifulSoup('<li><a href="entries/x/"><strong>T</strong></a> (Jane Doe and J. Roe)</li>', "lxml").li
    assert contents.extract_author(li.find("a")) == "Jane Doe and J. Roe"


# --- 032 청킹: 짧은 문단 머지 / 긴 문단 split / 섹션 경계 ---
def test_split_sentences():
    assert len(chunker.split_sentences("A first. A second! A third?")) == 3


def test_chunk_section_merges_short():
    assert len(chunker.chunk_section(["Short one.", "Short two.", "Short three."], target=200, overlap=0)) == 1


def test_chunk_section_splits_long():
    long_para = " ".join(f"Sentence number {i} here." for i in range(60))
    assert len(chunker.chunk_section([long_para], target=50, overlap=0)) > 1


# --- 061 QA 프롬프트/맥락화 ---
def test_build_prompt_includes_query_and_source():
    parents = [{"slug": "camus", "section_path": "3.1", "url": "https://x/#A", "text": "body"}]
    p = qa.build_prompt("What is the absurd?", parents)
    assert "What is the absurd?" in p and "https://x/#A" in p


def test_condense_query_no_history_passthrough():
    assert qa.condense_query([], "standalone query") == "standalone query"


# --- .gitignore 가드(과거 인라인주석 버그 회귀 방지) ---
def test_gitignore_guards_sep_derivatives():
    def ignored(path):
        return subprocess.run(["git", "check-ignore", path], cwd=ROOT).returncode == 0
    assert ignored("data/chunks/children.jsonl")
    assert ignored("data/raw/entries/camus.html")
    assert ignored("data/embeddings/0.6B/x.npy")
    assert ignored("vectordb/qdrant_storage")
    assert not ignored("05_retrieve/051_retrieve/retrieve.py")  # 코드는 추적
