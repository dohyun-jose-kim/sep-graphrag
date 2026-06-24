#!/usr/bin/env python3
"""022 — 저장된 entry HTML에서 메타데이터 추출 (오프라인, 재실행 가능).

data/raw/entries/*.html  →  data/metadata/entries_meta.json
contents의 title/author/url 과 페이지 메타(dates, copyright, related, sections)를 병합한다.
`related_entries` 가 023 그래프의 엣지가 된다.

사용 (repo 루트에서):
  python 02_scrape/022_entry_fetcher/extract_meta.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
CONTENTS = {
    e["slug"]: e
    for e in json.loads((ROOT / "data" / "contents" / "entries.json").read_text(encoding="utf-8"))
}
RAW = ROOT / "data" / "raw" / "entries"
OUT = ROOT / "data" / "metadata"

PUB_RE = re.compile(r"First published\s+(.+?)(?:;\s*substantive revision\s+(.+))?\s*$")


def parse_pubinfo(text: str) -> tuple[str | None, str | None]:
    m = PUB_RE.search(text.strip())
    if not m:
        return None, None
    first = m.group(1).strip().rstrip(".") if m.group(1) else None
    revised = m.group(2).strip().rstrip(".") if m.group(2) else None
    return first, revised


def related_slugs(soup: BeautifulSoup) -> list[str]:
    rel = soup.find(id="related-entries")
    if not rel:
        return []
    out, seen = [], set()
    for a in rel.find_all("a"):
        href = a.get("href")
        if not href:
            continue
        path = href.split("#")[0].split("?")[0]
        parts = [p for p in path.split("/") if p and p != ".."]
        if parts and parts[-1] not in seen:
            seen.add(parts[-1])
            out.append(parts[-1])
    return out


def sections(soup: BeautifulSoup) -> list[dict]:
    body = soup.find(id="main-text") or soup.find(id="article-content") or soup
    out = []
    for h in body.find_all(["h2", "h3"]):
        hid = h.get("id")
        if not hid and h.find("a"):
            hid = h.find("a").get("id") or h.find("a").get("name")
        out.append({"id": hid, "level": int(h.name[1]), "title": h.get_text(" ", strip=True)})
    return out


def extract_one(slug: str, html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    pub = soup.find(id="pubinfo")
    first, revised = parse_pubinfo(pub.get_text(" ", strip=True)) if pub else (None, None)
    cp = soup.find(id="article-copyright")
    base = CONTENTS.get(slug, {})
    return {
        "slug": slug,
        "title": base.get("title"),
        "author": base.get("author"),
        "url": base.get("url") or CFG["entry_url_template"].format(slug=slug),
        "first_published": first,
        "last_modified": revised,
        "copyright": cp.get_text(" ", strip=True) if cp else None,
        "related_entries": related_slugs(soup),
        "sections": sections(soup),
        "snapshot_date": CFG["snapshot_date"],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    records = [
        extract_one(f.stem, f.read_text(encoding="utf-8")) for f in sorted(RAW.glob("*.html"))
    ]
    (OUT / "entries_meta.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    known = set(CONTENTS)
    total_edges = sum(len(r["related_entries"]) for r in records)
    unknown = {t for r in records for t in r["related_entries"] if t not in known}
    print(f"entries parsed         : {len(records)}  -> data/metadata/entries_meta.json")
    print(f"total related edges    : {total_edges}")
    print(f"entries w/o related    : {sum(1 for r in records if not r['related_entries'])}")
    print(f"entries w/o revision   : {sum(1 for r in records if not r['last_modified'])}")
    print(f"entries w/o first-pub  : {sum(1 for r in records if not r['first_published'])}")
    print(f"related targets not in contents: {len(unknown)}  {sorted(unknown)[:10]}")


if __name__ == "__main__":
    main()
