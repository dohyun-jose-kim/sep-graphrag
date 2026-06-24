#!/usr/bin/env python3
"""022 — SEP entry fetcher (checkpoint 크롤).

data/contents/entries.json 의 entry들을 robots 준수(crawl-delay 5s + jitter)로 받아
data/raw/entries/<slug>.html 로 저장한다. 이미 저장된 slug는 스킵(resume).
메타데이터 추출은 extract_meta.py(오프라인, 재실행 가능)에서 한다.

사용 (repo 루트에서):
  python 02_scrape/022_entry_fetcher/fetch_entries.py --limit 5   # 슬라이스 검증
  python 02_scrape/022_entry_fetcher/fetch_entries.py             # 전체(~1,861, ~3h)
"""
from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
ENTRIES = json.loads((ROOT / "data" / "contents" / "entries.json").read_text(encoding="utf-8"))
RAW = ROOT / "data" / "raw" / "entries"
LOG = ROOT / "data" / "raw" / "fetch.log"

DELAY = CFG["crawl_delay_seconds"]
UA = CFG["user_agent"]
RETRY_STATUS = {429, 500, 502, 503, 504}


def log(msg: str) -> None:
    print(msg, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def fetch_one(client: httpx.Client, slug: str, url: str, retries: int = 4) -> str | None:
    for attempt in range(1, retries + 1):
        try:
            r = client.get(url, headers={"User-Agent": UA}, timeout=60, follow_redirects=True)
            if r.status_code == 200:
                return r.text
            if r.status_code in RETRY_STATUS:
                wait = DELAY * attempt * 2
                log(f"  {slug}: HTTP {r.status_code}, retry {attempt}/{retries} after {wait}s")
                time.sleep(wait)
                continue
            log(f"  {slug}: HTTP {r.status_code} (skip)")
            return None
        except (httpx.TimeoutException, httpx.TransportError) as e:
            wait = DELAY * attempt * 2
            log(f"  {slug}: {type(e).__name__}, retry {attempt}/{retries} after {wait}s")
            time.sleep(wait)
    log(f"  {slug}: failed after {retries} retries")
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="앞에서 N개만 (검증용)")
    args = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)

    targets = ENTRIES if args.limit is None else ENTRIES[: args.limit]
    todo = [e for e in targets if not (RAW / f"{e['slug']}.html").exists()]
    log(f"=== fetch start: {len(todo)}/{len(targets)} to fetch (rest cached), delay={DELAY}s+jitter ===")

    ok = fail = 0
    with httpx.Client() as client:
        for i, e in enumerate(todo, 1):
            html = fetch_one(client, e["slug"], e["url"])
            if html:
                (RAW / f"{e['slug']}.html").write_text(html, encoding="utf-8")
                ok += 1
            else:
                fail += 1
            if i % 25 == 0 or i == len(todo):
                log(f"  progress {i}/{len(todo)}  ok={ok} fail={fail}")
            time.sleep(DELAY + random.uniform(0, 1.0))

    cached = sum(1 for e in targets if (RAW / f"{e['slug']}.html").exists())
    log(f"=== fetch done: ok={ok} fail={fail}, cached {cached}/{len(targets)} ===")


if __name__ == "__main__":
    main()
