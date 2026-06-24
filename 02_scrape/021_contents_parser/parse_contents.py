#!/usr/bin/env python3
"""021 — SEP contents 파서.

라이브 https://plato.stanford.edu/contents.html 를 받아 **실제 entry 목록**(스텁 제외)을 산출한다.

contents.html 구조:
  - 실제 entry : <li><a href="entries/<slug>/"><strong>title</strong></a> (author) ...</li>
  - "see" 스텁 : <li> alias — see <a href="entries/<target>/">...</a></li>   (<strong> 없음)
판별: <a>가 <strong>을 감싸면 실제 entry. "see" 링크는 cross-reference라 제외.

출력(둘 다 gitignored):
  data/contents/entries.json  - [{slug, title, author, url}]  ← 022 크롤 대상
  data/contents/aliases.json  - [{alias, target_slug}]        ← 제외된 cross-ref
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
RAW = ROOT / "data" / "raw" / "contents.html"
OUT = ROOT / "data" / "contents"


def load_contents_html() -> str:
    """캐시가 있으면 재사용, 없으면 한 번만 fetch (robots 허용 경로)."""
    if RAW.exists():
        return RAW.read_text(encoding="utf-8")
    RAW.parent.mkdir(parents=True, exist_ok=True)
    r = httpx.get(
        CFG["contents_url"],
        headers={"User-Agent": CFG["user_agent"]},
        timeout=30,
        follow_redirects=True,
    )
    r.raise_for_status()
    RAW.write_text(r.text, encoding="utf-8")
    return r.text


def extract_author(a) -> str | None:
    """strong-link 뒤, 중첩 <ul>(하위 항목) 전까지의 텍스트에서 (저자)를 뽑는다."""
    parts = []
    for sib in a.next_siblings:
        if getattr(sib, "name", None) == "ul":
            break
        parts.append(sib.get_text() if hasattr(sib, "get_text") else str(sib))
    m = re.search(r"\(([^)]*)\)", "".join(parts))
    return m.group(1).strip() if m else None


def main() -> None:
    soup = BeautifulSoup(load_contents_html(), "lxml")
    links = soup.select('a[href^="entries/"]')

    entries: list[dict] = []
    aliases: list[dict] = []
    seen: set[str] = set()
    for a in links:
        slug = a["href"].split("/")[1]
        if a.find("strong"):  # 실제 entry
            if slug in seen:
                continue
            seen.add(slug)
            entries.append(
                {
                    "slug": slug,
                    "title": a.find("strong").get_text(strip=True),
                    "author": extract_author(a),
                    "url": CFG["entry_url_template"].format(slug=slug),
                }
            )
        else:  # "see" cross-reference 스텁 → 제외
            li = a.find_parent("li")
            aliases.append(
                {
                    "alias": li.get_text(" ", strip=True) if li else a.get_text(strip=True),
                    "target_slug": slug,
                }
            )

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "entries.json").write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "aliases.json").write_text(
        json.dumps(aliases, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    no_author = sum(1 for e in entries if not e["author"])
    print(f"edition_label        : {CFG['edition_label']}  (snapshot {CFG['snapshot_date']})")
    print(f"total entry-links    : {len(links)}")
    print(f"real entries         : {len(entries)}   -> {OUT.relative_to(ROOT)}/entries.json")
    print(f"excluded 'see' stubs : {len(aliases)}   -> {OUT.relative_to(ROOT)}/aliases.json")
    print(f"entries missing author: {no_author}")


if __name__ == "__main__":
    main()
