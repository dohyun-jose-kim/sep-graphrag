#!/usr/bin/env python3
"""032 — small-to-big 청킹 + parent docstore.

031의 structure.jsonl → 검색용 child 청크 + 생성용 parent(섹션) docstore.
- parent = 섹션(서브섹션 그대로; preamble 포함). parent_id -> text 를 sqlite에.
- child = 문단 길이보정: 짧은 문단 머지 / 긴 문단 문장경계 split / 섹션 내 overlap.
  길이는 Qwen3 토크나이저 기준. child는 섹션 경계를 넘지 않는다.

출력(gitignored):
  data/chunks/children.jsonl       - child 청크 + 메타
  data/docstore/parents.sqlite     - parent_id -> 섹션 본문

사용 (repo 루트에서):
  python 03_chunk/032_chunker/build_chunks.py            # 기본 target 320 / overlap 48
  python 03_chunk/032_chunker/build_chunks.py --target 256 --overlap 40
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path

from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parents[2]
STRUCT = ROOT / "data" / "structure" / "structure.jsonl"
CHUNKS = ROOT / "data" / "chunks"
DOCSTORE = ROOT / "data" / "docstore"

TOK = AutoTokenizer.from_pretrained("Qwen/Qwen3-Embedding-0.6B")
SENT = re.compile(r"(?<=[.!?])\s+")


def ntok(text: str) -> int:
    return len(TOK.encode(text, add_special_tokens=False))


def split_sentences(text: str) -> list[str]:
    return [s for s in SENT.split(text) if s.strip()]


def split_long(para: str, target: int) -> list[str]:
    """target 초과 문단을 문장경계로 분할(문장 단위는 깨지 않음)."""
    out, cur, cur_n = [], [], 0
    for s in split_sentences(para):
        n = ntok(s)
        if cur and cur_n + n > target:
            out.append(" ".join(cur))
            cur, cur_n = [], 0
        cur.append(s)
        cur_n += n
    if cur:
        out.append(" ".join(cur))
    return out


def tail_overlap(text: str, overlap: int) -> str:
    """text의 끝 문장들을 ~overlap 토큰만큼 가져온다(다음 청크 머리에 붙일 용)."""
    if overlap <= 0:
        return ""
    sents, acc, n = split_sentences(text), [], 0
    for s in reversed(sents):
        acc.insert(0, s)
        n += ntok(s)
        if n >= overlap:
            break
    return " ".join(acc)


def chunk_section(paras: list[str], target: int, overlap: int) -> list[str]:
    """섹션 문단들을 target 크기 child로 패킹(짧은 건 머지, 긴 건 split, overlap 적용)."""
    units: list[str] = []
    for p in paras:
        units.extend([p] if ntok(p) <= target else split_long(p, target))

    chunks: list[str] = []
    cur, cur_n = "", 0
    for u in units:
        un = ntok(u)
        if cur and cur_n + un > target:
            chunks.append(cur)
            cur = tail_overlap(cur, overlap)
            cur_n = ntok(cur) if cur else 0
        cur = (cur + " " + u).strip() if cur else u
        cur_n += un
    if cur:
        chunks.append(cur)
    return chunks


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=320, help="child 목표 토큰")
    ap.add_argument("--overlap", type=int, default=48, help="섹션 내 overlap 토큰")
    args = ap.parse_args()

    CHUNKS.mkdir(parents=True, exist_ok=True)
    DOCSTORE.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DOCSTORE / "parents.sqlite")
    db.execute("DROP TABLE IF EXISTS parents")
    db.execute("CREATE TABLE parents (parent_id TEXT PRIMARY KEY, slug TEXT, "
               "title TEXT, section_path TEXT, url TEXT, text TEXT)")

    n_child = n_parent = 0
    lens: list[int] = []
    fout = open(CHUNKS / "children.jsonl", "w", encoding="utf-8")

    for line in open(STRUCT, encoding="utf-8"):
        e = json.loads(line)
        slug, base_url = e["slug"], e["url"]
        h2_title = ""
        anchors: dict[int, str] = {}  # level -> 가장 가까운 조상 앵커
        for i, sec in enumerate(e["sections"]):
            sid = sec["id"] or f"sec{i}"
            lvl = sec["level"]
            own = sec["id"] if sec["id"] and sec["id"] != "preamble" else None
            if own:  # 자체 앵커 보유
                anchors = {L: a for L, a in anchors.items() if L < lvl}
                anchors[lvl] = own
                anchor = own
            elif sec["id"] == "preamble":  # 도입부 → entry 최상단
                anchor = None
            else:  # 앵커 없는 섹션(주로 h4) → 가장 가까운 조상 섹션 앵커로 딥링크
                ups = [anchors[L] for L in sorted(anchors) if L <= lvl]
                anchor = ups[-1] if ups else None
            url = f"{base_url}#{anchor}" if anchor else base_url
            if sec["level"] <= 2:
                h2_title = sec["title"]
                section_path = sec["title"]
            else:
                section_path = f"{h2_title} > {sec['title']}" if h2_title else sec["title"]
            parent_id = f"{slug}#{sid}"

            parent_text = (sec["title"] + "\n\n" + "\n\n".join(sec["paragraphs"])).strip()
            db.execute("INSERT OR REPLACE INTO parents VALUES (?,?,?,?,?,?)",
                       (parent_id, slug, sec["title"], section_path, url, parent_text))
            n_parent += 1

            for ci, text in enumerate(chunk_section(sec["paragraphs"], args.target, args.overlap)):
                tlen = ntok(text)
                lens.append(tlen)
                fout.write(json.dumps({
                    "id": f"{parent_id}::{ci}", "text": text, "tokens": tlen,
                    "slug": slug, "entry": e["title"], "author": e["author"],
                    "section_id": sec["id"], "section_path": section_path, "level": sec["level"],
                    "url": url, "parent_id": parent_id,
                    "first_published": e["first_published"], "last_modified": e["last_modified"],
                    "has_stripped_math": "[MATH]" in text,
                }, ensure_ascii=False) + "\n")
                n_child += 1

    fout.close()
    db.commit()
    db.close()

    lens.sort()
    def pct(p):
        return lens[int(len(lens) * p)] if lens else 0

    print(f"parents: {n_parent}  -> data/docstore/parents.sqlite")
    print(f"children: {n_child}  -> data/chunks/children.jsonl")
    print(f"child tokens  min {lens[0]} / p25 {pct(.25)} / median {pct(.5)} / p75 {pct(.75)} / "
          f"p95 {pct(.95)} / max {lens[-1]}")
    print(f"avg children/parent: {n_child/n_parent:.2f}")


if __name__ == "__main__":
    main()
