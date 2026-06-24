#!/usr/bin/env python3
"""031 — entry HTML → 구조화 텍스트.

data/raw/entries/<slug>.html → data/structure/structure.jsonl (entry당 1줄).
- 본문은 #preamble(intro) + #main-text(번호 섹션)만. 꼬리(bibliography/academic-tools/
  related-entries)는 별도 div라 자동 제외됨.
- 수식(LaTeX \\(..\\), \\[..\\])은 [MATH]로 치환 + has_stripped_math 플래그.
- blockquote(원전 인용)는 직전 문단에 흡수(독립 단위 X).
- 섹션 경계 보존: 각 문단은 소속 섹션(id/level/title)에 매핑.

사용 (repo 루트에서):
  python 03_chunk/031_structure/extract_structure.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
META = {
    r["slug"]: r
    for r in json.loads((ROOT / "data" / "metadata" / "entries_meta.json").read_text(encoding="utf-8"))
}
RAW = ROOT / "data" / "raw" / "entries"
OUT = ROOT / "data" / "structure"

CONTENT = ["h2", "h3", "h4", "p", "blockquote", "ul", "ol", "dl", "table"]
HEADERS = {"h2", "h3", "h4"}
BLOCKS = ("p", "blockquote", "ul", "ol", "dl", "table")
MATH_DISPLAY = re.compile(r"\\\[.*?\\\]", re.S)
MATH_INLINE = re.compile(r"\\\(.*?\\\)", re.S)


def strip_math(text: str) -> tuple[str, bool]:
    had = bool(MATH_INLINE.search(text) or MATH_DISPLAY.search(text))
    text = MATH_DISPLAY.sub("[MATH]", text)
    text = MATH_INLINE.sub("[MATH]", text)
    return text, had


def clean(el) -> tuple[str, bool]:
    text, had = strip_math(el.get_text(" ", strip=True))
    return re.sub(r"\s+", " ", text).strip(), had


def header_id(el) -> str | None:
    """섹션 앵커. 보통 <h2><a name="X">..</a></h2> (구식 a name) 형태라 fallback 필요."""
    if el.get("id"):
        return el.get("id")
    a = el.find("a")
    return (a.get("id") or a.get("name")) if a else None


def paras_of(container) -> tuple[list[str], bool]:
    """container 내 <p>들을 문단 리스트로(수식 strip). preamble용."""
    out, math = [], False
    for p in container.find_all("p"):
        txt, had = clean(p)
        math = math or had
        if txt:
            out.append(txt)
    return out, math


def extract(slug: str, html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    m = META.get(slug, {})
    sections: list[dict] = []
    math_any = False

    pre = soup.find(id="preamble")
    if pre:
        paras, had = paras_of(pre)
        math_any = math_any or had
        if paras:
            sections.append({"id": "preamble", "level": 1, "title": "Preamble", "paragraphs": paras})

    mt = soup.find(id="main-text") or soup.find(id="article-content")
    current: dict | None = None
    if mt:
        for el in mt.find_all(CONTENT):
            if el.name in HEADERS:
                if current:
                    sections.append(current)
                title, had = clean(el)
                math_any = math_any or had
                current = {"id": header_id(el), "level": int(el.name[1]), "title": title, "paragraphs": []}
                continue
            if el.find_parent(BLOCKS):  # 다른 블록에 중첩된 건 부모가 흡수 → 스킵
                continue
            txt, had = clean(el)
            math_any = math_any or had
            if not txt:
                continue
            if current is None:  # 첫 헤더 이전 본문 (드묾)
                current = {"id": None, "level": 2, "title": "", "paragraphs": []}
            if el.name == "blockquote" and current["paragraphs"]:
                current["paragraphs"][-1] += " " + txt  # 인용 → 직전 문단 흡수
            else:
                current["paragraphs"].append(txt)
        if current:
            sections.append(current)

    return {
        "slug": slug,
        "url": m.get("url"),
        "title": m.get("title"),
        "author": m.get("author"),
        "first_published": m.get("first_published"),
        "last_modified": m.get("last_modified"),
        "has_stripped_math": math_any,
        "sections": sections,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    files = sorted(RAW.glob("*.html"))
    recs = []
    empty = []
    for f in files:
        rec = extract(f.stem, f.read_text(encoding="utf-8"))
        recs.append(rec)
        if not rec["sections"]:
            empty.append(f.stem)

    with open(OUT / "structure.jsonl", "w", encoding="utf-8") as out:
        for r in recs:
            out.write(json.dumps(r, ensure_ascii=False) + "\n")

    n_sec = sum(len(r["sections"]) for r in recs)
    n_par = sum(len(s["paragraphs"]) for r in recs for s in r["sections"])
    math_n = sum(1 for r in recs if r["has_stripped_math"])
    print(f"entries           : {len(recs)}  -> data/structure/structure.jsonl")
    print(f"sections total    : {n_sec}  (avg {n_sec/len(recs):.1f}/entry)")
    print(f"paragraphs total  : {n_par}  (avg {n_par/len(recs):.1f}/entry)")
    print(f"entries w/ math    : {math_n}")
    print(f"entries w/ 0 sections: {len(empty)}  {empty[:10]}")


if __name__ == "__main__":
    main()
