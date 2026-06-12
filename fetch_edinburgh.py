#!/usr/bin/env python3
"""
fetch_edinburgh.py
------------------
Adds Edinburgh to city_paths/ and removes Washington DC.
Run from the same directory as your city_paths/ folder.

Requirements:
  pip3 install requests
"""

import json
import time
from pathlib import Path

import requests

MODEL      = "MERDITH2021"
BASE_URL   = "https://gws.gplates.org/reconstruct/reconstruct_points/"
OUTPUT_DIR = Path("city_paths")
TIME_STEP  = 10

CITY = {"name": "Edinburgh", "lat": 55.953, "lon": -3.189, "max_ma": 600, "group": "laurasia"}


def main():
    session = requests.Session()
    session.headers.update({"User-Agent": "city-plate-paths/1.0 (educational)"})

    print(f"Fetching path for Edinburgh (0–{CITY['max_ma']} Ma)...")

    path = [{"time_ma": 0, "lon": CITY["lon"], "lat": CITY["lat"]}]

    for t in range(TIME_STEP, CITY["max_ma"] + TIME_STEP, TIME_STEP):
        params = {
            "points": f"{CITY['lon']},{CITY['lat']}",
            "time":   t,
            "model":  MODEL,
            "fc":     "true",
        }
        try:
            r = session.get(BASE_URL, params=params, timeout=30)
            r.raise_for_status()
            feat = r.json().get("features", [None])[0]
            if feat and feat.get("geometry", {}).get("coordinates"):
                lon, lat = feat["geometry"]["coordinates"]
                if lon is not None and lat is not None:
                    path.append({"time_ma": t,
                                 "lon": round(float(lon), 4),
                                 "lat": round(float(lat), 4)})
                    print(f"  {t:4d} Ma  lat={float(lat):7.2f}  lon={float(lon):8.2f}")
                else:
                    print(f"  {t:4d} Ma  path ended"); break
            else:
                print(f"  {t:4d} Ma  no data returned"); break
        except Exception as e:
            print(f"  {t:4d} Ma  ERROR: {e}")
        time.sleep(0.35)

    city_data = {
        "name":         "Edinburgh",
        "group":        "laurasia",
        "modern_lat":   CITY["lat"],
        "modern_lon":   CITY["lon"],
        "model":        MODEL,
        "time_step_ma": TIME_STEP,
        "path_end_ma":  path[-1]["time_ma"],
        "step_count":   len(path),
        "path":         path,
    }

    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "edinburgh.json").write_text(json.dumps(city_data, indent=2))
    print(f"\nSaved city_paths/edinburgh.json  ({len(path)} steps, ends {path[-1]['time_ma']} Ma)")

    # Update all_cities.json — remove Washington DC, add Edinburgh
    all_path = OUTPUT_DIR / "all_cities.json"
    if all_path.exists():
        cities = json.loads(all_path.read_text())
        before = len(cities)
        cities = [c for c in cities if c["name"] != "Washington DC"]
        cities.append(city_data)
        all_path.write_text(json.dumps(cities, indent=2))
        print(f"Updated all_cities.json  ({before} → {len(cities)} cities)")
        print("  — removed Washington DC")
        print("  — added Edinburgh")
    else:
        print(f"WARNING: {all_path} not found — only edinburgh.json was saved.")


if __name__ == "__main__":
    main()
