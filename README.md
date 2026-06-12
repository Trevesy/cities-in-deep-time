# Cities in Deep Time

An interactive web visualisation showing how 16 major world cities have moved across the surface of the Earth due to plate tectonics — from the present day back to the start of the Cambrian period (540 million years ago).

**[Live demo →](https://trevesy.github.io/cities-in-deep-time)**

---

## What it shows

- **Animated paleo-continental coastlines** reconstructed from the [GPlates MERDITH2021 tectonic model](https://gwsdoc.gplates.org)
- **City positions** tracked backwards through geological time — each city moves with the tectonic plate it sits on
- **Supercontinent labels** — Gondwana, Pangea and Laurasia fade in and out over their correct geological periods
- **Reference lines** — equator, tropics of Cancer and Capricorn, Greenwich meridian
- **Modern coastline overlay** as a dotted reference so you can see how far the land has moved
- Time slider from present day to 540 Ma (Cambrian), 1 Ma steps

### Cities included
London, Paris, Edinburgh, Moscow, Rome · New York, Mexico City, San Francisco, Honolulu · Sydney, Wellington, Delhi, Cape Town, Brasilia, Buenos Aires, Tokyo

---

## Running locally (full 1 Ma resolution)

The high-resolution version uses 541 coastline files (one per million years). These are too large to host on GitHub and must be generated locally.

**1. Install dependencies**
```bash
pip3 install requests
```

**2. Fetch city tectonic paths** *(only needed once)*
```bash
python3 fetch_city_paths.py
python3 fetch_edinburgh.py
```

**3. Download coastline data** *(takes ~2 hours — 541 API calls to GPlates)*
```bash
python3 fetch_coastlines.py --step 1
```
Use `--resume` to continue an interrupted download.

**4. Serve locally**
```bash
python3 -m http.server 8000
```
Then open **http://localhost:8000**

---

## Deploying the web version (5 Ma resolution)

The `web` branch contains a smaller version (109 coastline files at 5 Ma steps, ~186 MB) suitable for GitHub Pages. City positions still interpolate at 1 Ma for smooth animation.

To regenerate the web version from scratch:

```bash
# Create the 5 Ma subset from your local 1 Ma files
mkdir coastline_paths_5ma
for t in $(seq 0 5 540); do
  cp coastline_paths/$(printf "coastlines_%04d.json" $t) coastline_paths_5ma/
done
```

Then switch the `coastline_paths_5ma/` folder name and CDN script tags in `index.html`, commit to the `web` branch, and push.

---

## File structure

```
.
├── index.html                  Main visualisation
├── fetch_city_paths.py         Fetches tectonic paths for all cities from GPlates
├── fetch_edinburgh.py          Adds Edinburgh, removes Washington DC
├── fetch_coastlines.py         Downloads paleo-coastline polygons from GPlates
├── d3.min.js                   D3.js v7 (local copy for offline use)
├── topojson.min.js             TopoJSON client (local copy)
├── countries-110m.json         Modern world basemap (Natural Earth 110m)
├── city_paths/
│   ├── all_cities.json         All 16 city paths combined
│   └── *.json                  Individual city files
└── coastline_paths/            NOT in git — generate with fetch_coastlines.py
    └── coastlines_NNNN.json    One file per million years, 0–540 Ma
```

---

## Data sources

| Data | Source |
|------|--------|
| Tectonic reconstruction | [GPlates Web Service](https://gws.gplates.org) — MERDITH2021 model |
| Modern basemap | [Natural Earth](https://naturalearthdata.com) via [topojson/world-atlas](https://github.com/topojson/world-atlas) |
| Visualisation library | [D3.js v7](https://d3js.org) |

---

## Branches

| Branch | Description |
|--------|-------------|
| `master` | Full 1 Ma resolution — code only, coastline data generated locally |
| `web` | 5 Ma resolution with CDN libraries — deployed to GitHub Pages |
