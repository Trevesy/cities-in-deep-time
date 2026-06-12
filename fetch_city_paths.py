#!/usr/bin/env python3
"""
fetch_city_paths.py
-------------------
Pre-compute plate tectonic reconstruction paths for 16 major world cities
using the GPlates Web Service (https://gws.gplates.org).

All 16 cities are batched into a single API call per time step, keeping
total requests to ~100 regardless of city count.

Results are saved as:
  city_paths/all_cities.json   — combined output for all cities
  city_paths/<city_name>.json  — individual cache file per city

Requirements:
  pip install requests

Usage:
  python fetch_city_paths.py
  python fetch_city_paths.py --step 5      # 5 Ma resolution (slower)
  python fetch_city_paths.py --step 10     # 10 Ma resolution (default)
  python fetch_city_paths.py --dry-run     # print config, make no API calls

Notes:
  - San Francisco and Honolulu are on oceanic Pacific plate crust —
    their paths will terminate naturally when GPlates can no longer
    reconstruct that crust (roughly 85-150 Ma respectively).
  - Honolulu (Oahu) emerged above sea level only ~3-4 Ma ago; the crust
    it sits on is ~85 Ma old. Both limits are worth noting in your app.
  - The reconstruction model is MERDITH2021, which covers 0-1000 Ma and
    is the most comprehensive currently available via this service.
  - Verify endpoint behaviour against https://gws.gplates.org/doc/ if
    the API has changed since this script was written.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import requests

# ── City definitions ──────────────────────────────────────────────────────────
# max_ma: upper reconstruction limit in million years.
# For oceanic-crust cities (SF, Honolulu) this is set conservatively;
# the API will stop returning valid coordinates before this if the
# crust didn't yet exist — the script handles that gracefully.

CITIES = [
    # Laurasia-derived continental crust
    {"name": "London",        "lat":  51.507, "lon":  -0.128, "max_ma": 600,  "group": "laurasia"},
    {"name": "Paris",         "lat":  48.864, "lon":   2.349, "max_ma": 600,  "group": "laurasia"},
    {"name": "New York",      "lat":  40.713, "lon": -74.006, "max_ma": 600,  "group": "laurasia"},
    {"name": "Washington DC", "lat":  38.907, "lon": -77.037, "max_ma": 600,  "group": "laurasia"},
    {"name": "Moscow",        "lat":  55.755, "lon":  37.617, "max_ma": 1000, "group": "laurasia"},
    {"name": "Mexico City",   "lat":  19.433, "lon": -99.133, "max_ma": 600,  "group": "laurasia"},
    # Gondwana-derived continental crust
    {"name": "Sydney",        "lat": -33.869, "lon": 151.209, "max_ma": 1000, "group": "gondwana"},
    {"name": "Wellington",    "lat": -41.286, "lon": 174.776, "max_ma": 600,  "group": "gondwana"},
    {"name": "Brasilia",      "lat": -15.780, "lon": -47.929, "max_ma": 1000, "group": "gondwana"},
    {"name": "Buenos Aires",  "lat": -34.603, "lon": -58.381, "max_ma": 1000, "group": "gondwana"},
    {"name": "Cape Town",     "lat": -33.924, "lon":  18.424, "max_ma": 1000, "group": "gondwana"},
    {"name": "Delhi",         "lat":  28.614, "lon":  77.209, "max_ma": 1000, "group": "gondwana"},
    # Special cases / plate boundaries / oceanic crust
    {"name": "Rome",          "lat":  41.902, "lon":  12.496, "max_ma": 600,  "group": "special"},
    {"name": "Tokyo",         "lat":  35.676, "lon": 139.650, "max_ma": 600,  "group": "special"},
    {"name": "San Francisco", "lat":  37.774, "lon":-122.419, "max_ma": 180,  "group": "special"},
    {"name": "Honolulu",      "lat":  21.307, "lon":-157.858, "max_ma": 100,  "group": "special"},
]

# ── Config ────────────────────────────────────────────────────────────────────
MODEL      = "MERDITH2021"
BASE_URL   = "https://gws.gplates.org/reconstruct/reconstruct_points/"
OUTPUT_DIR = Path("city_paths")
DELAY      = 0.4   # seconds between time-step batches (be polite to the API)
TIMEOUT    = 30    # seconds per HTTP request
MAX_RETRY  = 3     # retries per failed request


# ── API helpers ───────────────────────────────────────────────────────────────

def batch_reconstruct(cities_subset, time_ma, session):
    """
    Reconstruct all cities in cities_subset at time_ma in a single API call.

    GPlates expects points as a flat lon,lat,lon,lat,... string.
    Returns a list of {"lon": float, "lat": float} | None, one per input city,
    in the same order. None means the point could not be reconstructed.
    """
    # Build lon,lat string (GPlates convention: longitude first)
    points_str = ",".join(f"{c['lon']},{c['lat']}" for c in cities_subset)

    params = {
        "points": points_str,
        "time":   time_ma,
        "model":  MODEL,
        "fc":     "true",   # return as GeoJSON FeatureCollection
    }

    for attempt in range(MAX_RETRY):
        try:
            resp = session.get(BASE_URL, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as exc:
            wait = 2 ** attempt
            print(
                f"    [attempt {attempt + 1}/{MAX_RETRY}] error at {time_ma} Ma: "
                f"{exc}. Retrying in {wait}s...",
                flush=True,
            )
            time.sleep(wait)
            continue

        features = data.get("features", [])

        # Defensive: if the API returned fewer features than expected, pad with None
        while len(features) < len(cities_subset):
            features.append(None)

        results = []
        for feat in features:
            if feat is None:
                results.append(None)
                continue
            geom = feat.get("geometry") or {}
            coords = geom.get("coordinates")
            if coords and coords[0] is not None and coords[1] is not None:
                results.append({
                    "lon": round(float(coords[0]), 4),
                    "lat": round(float(coords[1]), 4),
                })
            else:
                results.append(None)

        return results

    # All retries exhausted
    print(f"    All retries failed at {time_ma} Ma — returning None for all cities", flush=True)
    return [None] * len(cities_subset)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fetch GPlates plate-tectonic paths for 16 cities.")
    parser.add_argument("--step",    type=int,  default=10,    help="Time step in Ma (default: 10)")
    parser.add_argument("--dry-run", action="store_true",      help="Print config and exit without API calls")
    args = parser.parse_args()

    time_step  = args.step
    global_max = max(c["max_ma"] for c in CITIES)
    time_steps = list(range(time_step, global_max + time_step, time_step))

    print("=" * 60)
    print(f"  GPlates city path pre-computation")
    print(f"  Cities    : {len(CITIES)}")
    print(f"  Model     : {MODEL}")
    print(f"  Time step : {time_step} Ma")
    print(f"  Range     : 0 – {global_max} Ma  ({len(time_steps)} steps)")
    print(f"  API calls : ~{len(time_steps)} batched  (~{len(CITIES) * len(time_steps)} if unbatched)")
    print(f"  Output    : {OUTPUT_DIR}/")
    print("=" * 60)

    if args.dry_run:
        print("\nDry run — exiting without making API calls.")
        return

    OUTPUT_DIR.mkdir(exist_ok=True)

    # Initialise path storage.
    # t=0 is always the modern position — no API call needed.
    paths   = {c["name"]: [{"time_ma": 0, "lon": c["lon"], "lat": c["lat"]}] for c in CITIES}
    active  = {c["name"]: True for c in CITIES}

    session = requests.Session()
    session.headers.update({"User-Agent": "city-plate-paths/1.0 (educational)"})

    for t in time_steps:
        # Only query cities still active and within their personal max_ma
        to_query = [c for c in CITIES if active[c["name"]] and t <= c["max_ma"]]
        if not to_query:
            break

        n = len(to_query)
        print(f"  {t:5d} Ma  — querying {n:2d} cities...", end=" ", flush=True)

        results = batch_reconstruct(to_query, t, session)

        hits = 0
        for city, result in zip(to_query, results):
            if result:
                paths[city["name"]].append({"time_ma": t, **result})
                hits += 1
            else:
                # Point can no longer be reconstructed — mark as done
                active[city["name"]] = False
                print(f"\n    ✗ {city['name']} path ends at {t} Ma", end="", flush=True)

        print(f"  {hits}/{n} reconstructed", flush=True)
        time.sleep(DELAY)

    # ── Save individual city files ─────────────────────────────────────────
    print("\nSaving individual city files...")
    for city in CITIES:
        name = city["name"]
        city_data = {
            "name":       name,
            "group":      city["group"],
            "modern_lat": city["lat"],
            "modern_lon": city["lon"],
            "model":      MODEL,
            "time_step_ma": time_step,
            "path_end_ma":  paths[name][-1]["time_ma"],
            "step_count":   len(paths[name]),
            "path":         paths[name],
        }
        slug = name.lower().replace(" ", "_")
        out  = OUTPUT_DIR / f"{slug}.json"
        out.write_text(json.dumps(city_data, indent=2))

    # ── Save combined file ─────────────────────────────────────────────────
    combined = [
        {
            "name":         city["name"],
            "group":        city["group"],
            "modern_lat":   city["lat"],
            "modern_lon":   city["lon"],
            "model":        MODEL,
            "time_step_ma": time_step,
            "path_end_ma":  paths[city["name"]][-1]["time_ma"],
            "step_count":   len(paths[city["name"]]),
            "path":         paths[city["name"]],
        }
        for city in CITIES
    ]

    combined_path = OUTPUT_DIR / "all_cities.json"
    combined_path.write_text(json.dumps(combined, indent=2))

    # ── Summary ────────────────────────────────────────────────────────────
    print(f"\nSaved → {combined_path}\n")
    print(f"  {'City':<18}  {'Steps':>6}  {'Path ends':>10}  Group")
    print(f"  {'-'*18}  {'-'*6}  {'-'*10}  {'-'*10}")
    for c in combined:
        print(
            f"  {c['name']:<18}  {c['step_count']:>6}  "
            f"{c['path_end_ma']:>7} Ma  {c['group']}"
        )
    print()


if __name__ == "__main__":
    main()
