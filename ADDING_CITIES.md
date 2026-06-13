# Adding a Custom Location

This guide explains how to add any city or place to the *Cities in Deep Time* visualisation. It covers the full manual process and includes ready-to-use Claude Code prompts that automate everything.

---

## What's involved

Adding a location requires two things:

1. **Fetching its tectonic path** — a Python script calls the GPlates Web Service to find where your location was at each time step going back through geological time
2. **Updating the visualisation** — adding a colour and group assignment to `index.html`

---

## Step 1: Find your city's coordinates

You need decimal latitude and longitude. Google Maps is the easiest source: right-click anywhere on the map and the coordinates appear at the top of the context menu.

Examples:
| City | Latitude | Longitude |
|------|----------|-----------|
| Cairo | 30.033 | 31.233 |
| Mumbai | 19.076 | 72.878 |
| Vancouver | 49.283 | -123.120 |

---

## Step 2: Fetch the tectonic path

Create a file called `fetch_CITYNAME.py` in the project root. The template below is a complete working script — replace the five values at the top.

```python
#!/usr/bin/env python3
"""
fetch_CITYNAME.py
-----------------
Fetches the tectonic path for a custom location and adds it to all_cities.json.
Run from the project root (same folder as city_paths/).

Requirements:
  pip3 install requests
"""

import json
import time
from pathlib import Path
import requests

# ── Configure these five values ──────────────────────────────────────────────
CITY_NAME  = "Cairo"       # Display name — must be unique
CITY_LAT   =  30.033       # Decimal degrees N (negative = S)
CITY_LON   =  31.233       # Decimal degrees E (negative = W)
CITY_GROUP = "gondwana"    # "laurasia", "gondwana", or "boundaries"
MAX_MA     =  600          # How far back to track (600 is a safe maximum)
# ─────────────────────────────────────────────────────────────────────────────

MODEL      = "MERDITH2021"
BASE_URL   = "https://gws.gplates.org/reconstruct/reconstruct_points/"
OUTPUT_DIR = Path("city_paths")
TIME_STEP  = 10            # Must stay at 10 — matches the other city data


def main():
    session = requests.Session()
    session.headers.update({"User-Agent": "city-plate-paths/1.0 (educational)"})

    slug = CITY_NAME.lower().replace(" ", "_")
    print(f"Fetching path for {CITY_NAME} (0–{MAX_MA} Ma at {TIME_STEP} Ma steps)...")

    # Time 0 = modern position
    path = [{"time_ma": 0, "lon": CITY_LON, "lat": CITY_LAT}]

    for t in range(TIME_STEP, MAX_MA + TIME_STEP, TIME_STEP):
        params = {
            "points": f"{CITY_LON},{CITY_LAT}",
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
                    path.append({
                        "time_ma": t,
                        "lon": round(float(lon), 4),
                        "lat": round(float(lat), 4),
                    })
                    print(f"  {t:4d} Ma  lat={float(lat):7.2f}  lon={float(lon):8.2f}")
                else:
                    print(f"  {t:4d} Ma  path ended (off-model)")
                    break
            else:
                print(f"  {t:4d} Ma  no data returned")
                break
        except Exception as e:
            print(f"  {t:4d} Ma  ERROR: {e}")
        time.sleep(0.35)

    city_data = {
        "name":         CITY_NAME,
        "group":        CITY_GROUP,
        "modern_lat":   CITY_LAT,
        "modern_lon":   CITY_LON,
        "model":        MODEL,
        "time_step_ma": TIME_STEP,
        "path_end_ma":  path[-1]["time_ma"],
        "step_count":   len(path),
        "path":         path,
    }

    OUTPUT_DIR.mkdir(exist_ok=True)

    # Save individual file
    out_file = OUTPUT_DIR / f"{slug}.json"
    out_file.write_text(json.dumps(city_data, indent=2))
    print(f"\nSaved {out_file}  ({len(path)} steps, ends at {path[-1]['time_ma']} Ma)")

    # Update all_cities.json — remove any existing entry for this city, add new one
    all_path = OUTPUT_DIR / "all_cities.json"
    if all_path.exists():
        cities = json.loads(all_path.read_text())
        before = len(cities)
        cities = [c for c in cities if c["name"] != CITY_NAME]
        cities.append(city_data)
        all_path.write_text(json.dumps(cities, indent=2))
        print(f"Updated all_cities.json  ({before} → {len(cities)} cities)")
    else:
        print(f"WARNING: {all_path} not found — only {slug}.json was saved.")


if __name__ == "__main__":
    main()
```

Run it from the project folder:

```bash
python3 fetch_CITYNAME.py
```

This takes about a minute. When it finishes `city_paths/all_cities.json` will contain your new city.

### Which group to use?

| Group | Use for |
|-------|---------|
| `"laurasia"` | Europe, North America, most of northern/central Asia, Greenland |
| `"gondwana"` | Africa, South America, India, Australia, New Zealand, Antarctica |
| `"boundaries"` | Japan, Italy, western USA, Pacific islands — near plate boundaries |

---

## Step 3: Update index.html

Two small changes are needed.

### 3a — Add a colour

Find the `COLORS` object near the top of the `<script>` block and add one line:

```javascript
const COLORS = {
    "London":        "#FF6B6B",
    "Paris":         "#FF8C42",
    // ... existing entries ...
    "Cairo":         "#F4A261",   // ← add your city here
};
```

Pick any hex colour not already used. Suggested palette for new entries:

| Colour | Hex |
|--------|-----|
| Warm amber | `#F4A261` |
| Sage green | `#95D5B2` |
| Slate blue | `#6096BA` |
| Dusty rose | `#E8A0BF` |
| Terracotta | `#CB6040` |
| Mint | `#80B9AD` |

### 3b — Add to a group

Find the `GROUPS` array and add the city name to the appropriate group:

```javascript
const GROUPS = [
    { label: "Laurasia",
      names: ["London","Paris","New York","Edinburgh","Moscow","Mexico City"] },
    { label: "Gondwana",
      names: ["Sydney","Wellington","Brasilia","Buenos Aires","Cape Town","Delhi",
              "Cairo"] },   // ← add here
    { label: "Plate Boundaries / Oceanic",
      names: ["Rome","Tokyo","San Francisco","Honolulu"] },
];
```

That's it. Reload the page and your city appears in the legend with its own checkbox, colour, and track.

---

## Step 4: Commit and deploy

```bash
# Commit the new city data and updated HTML
git add city_paths/ index.html
git commit -m "Add Cairo"

# Push master (code backup)
git push origin master

# Merge into web branch and push to update the live site
git checkout web
git merge master
git push origin web
git checkout master
```

GitHub Pages will rebuild within about a minute.

---

## Using Claude Code to do this automatically

If you have [Claude Code](https://claude.ai/code) installed, you can paste either of the prompts below into a session opened in your project folder and it will handle everything.

---

### Prompt A — Complete automation (fetch + update HTML)

Paste this into Claude Code, replacing the values in the first four lines:

```
I want to add a new city to my Cities in Deep Time visualisation.

City name:  Cairo
Latitude:   30.033
Longitude:  31.233
Group:      gondwana   (options: laurasia / gondwana / boundaries)
Colour:     #F4A261

The project is a D3.js plate-tectonics visualisation. Here is what you need to do:

1. Create a Python script called fetch_cairo.py based on this template pattern:
   - It calls https://gws.gplates.org/reconstruct/reconstruct_points/ for each
     time step from 10 to 600 Ma (10 Ma increments, 0.35s delay between requests)
   - Parameters: points="{lon},{lat}", time={t}, model=MERDITH2021, fc=true
   - It appends {time_ma, lon, lat} entries to a path array starting with time 0
   - It stops when the API returns null coordinates (city has drifted off-model)
   - It saves city_paths/cairo.json and updates city_paths/all_cities.json
     (removing any existing Cairo entry first to avoid duplicates)
   - The city_data object needs: name, group, modern_lat, modern_lon, model,
     time_step_ma, path_end_ma, step_count, path

2. Run the script: python3 fetch_cairo.py

3. In index.html, add "Cairo": "#F4A261" to the COLORS object.

4. In index.html, add "Cairo" to the "gondwana" entry in the GROUPS array.

5. Confirm the city appears in city_paths/all_cities.json without duplicates.

The project is served locally with python3 -m http.server 8000.
```

---

### Prompt B — HTML only (you've already run the fetch script)

Use this if you've already run the Python fetch script and just want Claude to update the visualisation:

```
I've added a new city to city_paths/all_cities.json called "Cairo".
Now I need you to update index.html to include it in the visualisation.

1. Add "Cairo": "#F4A261" to the COLORS object in index.html.
   (This is a JavaScript object literal near the top of the <script> block.)

2. Add "Cairo" to the names array of the "Gondwana" group in the GROUPS array.

3. Check city_paths/all_cities.json to confirm Cairo is present and has a valid
   path array with time_ma, lon, lat entries.

That's all — do not change anything else.
```

---

### Prompt C — Add multiple cities at once

```
I want to add three new cities to my Cities in Deep Time visualisation.

Cities:
  - Cairo      lat=30.033  lon=31.233   group=gondwana    colour=#F4A261
  - Vancouver  lat=49.283  lon=-123.120 group=laurasia     colour=#6096BA
  - Mumbai     lat=19.076  lon=72.878   group=gondwana     colour=#CB6040

For each city:
1. Create a fetch script (fetch_cairo.py, fetch_vancouver.py, fetch_mumbai.py)
   using the GPlates API pattern: GET https://gws.gplates.org/reconstruct/reconstruct_points/
   with params points="{lon},{lat}", time={t}, model=MERDITH2021, fc=true.
   Step from 10 to 600 Ma in 10 Ma increments with 0.35s delay.
   Stop when coordinates return null. Save to city_paths/ and update all_cities.json.

2. Run all three scripts sequentially.

3. In index.html add all three to COLORS and to their respective GROUPS entries.

4. Verify no duplicates in all_cities.json.
```

---

## Troubleshooting

**City appears in the wrong location at present day**
Check that you haven't swapped latitude and longitude. Latitude is N/S (−90 to 90), longitude is E/W (−180 to 180).

**Path ends early (e.g. stops at 400 Ma)**
This is normal — some locations drift off the edge of the tectonic model at older times. The visualisation automatically hides the marker beyond `path_end_ma`.

**Duplicate city entries in all_cities.json**
Run this to clean up:
```bash
python3 - <<'EOF'
import json
path = "city_paths/all_cities.json"
cities = json.load(open(path))
seen, deduped = set(), []
for c in cities:
    if c["name"] not in seen:
        seen.add(c["name"]); deduped.append(c)
open(path,"w").write(json.dumps(deduped, indent=2))
print([c["name"] for c in deduped])
EOF
```

**City doesn't appear in the legend**
Make sure the name in `all_cities.json` exactly matches the name in `COLORS` and `GROUPS` — including capitalisation and spaces.
