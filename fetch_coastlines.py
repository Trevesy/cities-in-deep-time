#!/usr/bin/env python3
"""
fetch_coastlines.py
-------------------
Pre-compute reconstructed continental coastline polygons at each time step
using the GPlates Web Service.  Results saved to coastline_paths/.

Requirements:
  pip3 install requests

Usage:
  python3 fetch_coastlines.py              # 10 Ma steps, 0-540 Ma  (~55 files)
  python3 fetch_coastlines.py --step 1     # 1 Ma steps — smoother animation (~540 files, ~9 min)
  python3 fetch_coastlines.py --resume     # skip files already saved
"""

import argparse
import json
import time
from pathlib import Path

import requests

MODEL      = "MERDITH2021"
BASE_URL   = "https://gws.gplates.org/reconstruct/coastlines/"
OUTPUT_DIR = Path("coastline_paths")
DELAY      = 0.5
TIMEOUT    = 30
MAX_RETRY  = 3
MAX_MA     = 540   # Cambrian start ≈ 538.8 Ma


def fetch(t_ma, session):
    params = {"time": t_ma, "model": MODEL}
    for attempt in range(MAX_RETRY):
        try:
            r = session.get(BASE_URL, params=params, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as exc:
            wait = 2 ** attempt
            print(f"\n    [attempt {attempt+1}/{MAX_RETRY}] {exc} — retry in {wait}s", end="", flush=True)
            time.sleep(wait)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step",   type=int, default=5,    help="Time step in Ma (default 5)")
    ap.add_argument("--resume", action="store_true",    help="Skip files already saved")
    args = ap.parse_args()

    step  = args.step
    steps = list(range(0, MAX_MA + step, step))

    print("=" * 55)
    print(f"  GPlates coastline pre-computation")
    print(f"  Model     : {MODEL}")
    print(f"  Time step : {step} Ma")
    print(f"  Range     : 0 – {MAX_MA} Ma  ({len(steps)} requests)")
    print(f"  Output    : {OUTPUT_DIR}/")
    print("=" * 55)

    OUTPUT_DIR.mkdir(exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "city-plate-paths/1.0 (educational)"})

    ok = skipped = failed = 0

    for t in steps:
        fname = OUTPUT_DIR / f"coastlines_{t:04d}.json"
        if args.resume and fname.exists():
            print(f"  {t:5d} Ma  — cached, skipping")
            skipped += 1
            continue

        print(f"  {t:5d} Ma ...", end=" ", flush=True)
        data = fetch(t, session)

        if data is not None:
            fname.write_text(json.dumps(data, separators=(",", ":")))
            n  = len(data.get("features", []))
            kb = fname.stat().st_size // 1024
            print(f"{n} features  {kb} KB")
            ok += 1
        else:
            print("FAILED")
            failed += 1

        time.sleep(DELAY)

    print(f"\nDone — {ok} saved, {skipped} skipped, {failed} failed.")
    if failed:
        print("Re-run with --resume to retry failed steps.")


if __name__ == "__main__":
    main()
