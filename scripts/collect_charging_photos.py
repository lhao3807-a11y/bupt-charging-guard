"""Collect auditable, openly licensed EV charging photo candidates from Openverse.

Candidates are not scene ground truth. Review the actual pixels before promoting any
image into a dataset, and never infer charging completion or dwell time from a still.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "algo" / "dataset_charging_raw"
API = "https://api.openverse.org/v1/images/"
USER_AGENT = "BUPT-Charging-Guard/1.0 (academic image dataset review)"
QUERIES = (
    "electric car charging station",
    "EV plugged charging station",
    "electric car charging parking",
    "charging station parking car",
    "EV charger parked car",
    "electric vehicle charge point car",
    "Tesla supercharger vehicles",
    "car plugged into charging station",
    "plugged in electric car",
    "charging electric car",
    "car at EV charger",
    "public EV charging station",
    "electric vehicle charger with car",
    "EV charging bay car",
    "electric car charging garage",
)
LICENSES = {"by", "by-sa", "cc0", "pdm"}


def eligible_candidate(item: dict) -> bool:
    """Require reusable license, traceable credit, original page and usable size."""
    return (
        item.get("license") in LICENSES
        and bool(item.get("creator"))
        and bool(item.get("foreign_landing_url"))
        and bool(item.get("url"))
        and min(item.get("width") or 0, item.get("height") or 0) >= 500
    )


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.load(response)
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def collect(pages_per_query: int) -> list[dict]:
    seen: dict[str, dict] = {}
    for query in QUERIES:
        for page in range(1, pages_per_query + 1):
            params = urllib.parse.urlencode(
                {
                    "q": query,
                    "page": page,
                    "page_size": 20,
                    "license": ",".join(sorted(LICENSES)),
                    "extension": "jpg",
                }
            )
            payload = get_json(f"{API}?{params}")
            for item in payload.get("results", []):
                if eligible_candidate(item):
                    source = item["foreign_landing_url"].split("?")[0]
                    seen.setdefault(
                        source,
                        {
                            "title": item.get("title") or "",
                            "creator": item["creator"],
                            "source_page": source,
                            "source_url": item["url"],
                            "license": item["license"],
                            "license_version": item.get("license_version") or "",
                            "width": item["width"],
                            "height": item["height"],
                            "query": query,
                        },
                    )
            time.sleep(0.25)
        print(f"{query}: {len(seen)} unique licensed candidates", flush=True)
    return list(seen.values())


def download(index: int, item: dict, image_dir: Path) -> dict:
    image_dir.mkdir(parents=True, exist_ok=True)
    source_key = hashlib.sha256(item["source_page"].encode()).hexdigest()[:12]
    name = f"candidate_{source_key}.jpg"
    path = image_dir / name
    if path.exists():
        data = path.read_bytes()
    else:
        req = urllib.request.Request(item["source_url"], headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=35) as response:
            data = response.read(8_000_001)
        if not 15_000 <= len(data) <= 8_000_000 or not data.startswith(b"\xff\xd8"):
            raise ValueError("invalid, undersized or oversized JPEG")
        path.write_bytes(data)
    return {**item, "file": name, "sha256": hashlib.sha256(data).hexdigest()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages-per-query", type=int, default=5)
    parser.add_argument("--max-download", type=int, default=250)
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    if args.pages_per_query < 1 or args.max_download < 0:
        parser.error("page count must be positive and max download nonnegative")
    RAW.mkdir(parents=True, exist_ok=True)
    candidates = collect(args.pages_per_query)
    (RAW / "candidates.json").write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Candidate manifest: {len(candidates)}")
    if args.probe:
        return 0
    retained = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {
            pool.submit(download, index, item, RAW / "images"): index
            for index, item in enumerate(candidates[: args.max_download], 1)
        }
        for future in as_completed(futures):
            try:
                retained.append(future.result())
            except (OSError, ValueError) as exc:
                print(f"download {futures[future]} failed: {exc}", flush=True)
    retained.sort(key=lambda item: item["file"])
    (RAW / "downloaded.json").write_text(
        json.dumps(retained, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Downloaded {len(retained)} of {min(len(candidates), args.max_download)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
