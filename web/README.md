# Web visualizations

Two interactive views of the tax-list data: a **year-by-year map** of taxable
*selišta* and a **decline chart** of the county tax base over 1495–1596.

The page is static HTML + a sibling `map.js` (no build step for JS edits).
Census data is inlined into `index.html` at rebuild time; there are no external
tiles, fonts or network calls.

## Source files

| File | Role |
|------|------|
| `template.html` | HTML shell; `build_web.py` copies it to `index.html` and injects data |
| `map.js` | Map/table UI logic (edit this for behaviour changes) |
| `index.html` | Generated output — HTML + inlined `DATA` + `<script src="map.js">` |
| `geo.json` | County borders + rivers (optional map context) |

## Rebuild

Regenerate `index.html` from the committed database after pipeline/data changes:

```bash
python web/build_web.py        # reads db/tax_lists.sqlite, writes web/index.html
```

Only the Python standard library is required (`sqlite3`, `json`). `build_web.py`
computes each place's map position and confidence tier, the per-year burden, and
the county trends, then inlines them into `template.html` — along with the map
context geometry from `geo.json` if present. Edit `map.js` directly for UI
changes; no rebuild needed unless data changed.

**Map context geometry** (county borders + the Sava/Drava rivers) is cached in
`geo.json` and committed, so a normal rebuild needs no network. To refresh it
from OSM Nominatim (borders) and Overpass (rivers):

```bash
python web/fetch_geo.py --force
```

## View locally

Because browsers block `file://` for some features, serve the folder:

```bash
python -m http.server 8137 --directory web
# then open http://127.0.0.1:8137/index.html
```

(Opening `index.html` directly also works in most browsers.)

## Deploy to the web

Deploy the whole `web/` folder (at minimum `index.html`, `map.js`, and `geo.json`):

- **GitHub Pages**: the workflow in `.github/workflows/pages.yml` rebuilds and
  publishes `web/` on every push to `main`. Enable Pages → "GitHub Actions" in
  the repo settings once.
- **Netlify / any static host / S3**: upload the `web/` directory.

## Reading the map

- **Marker area** ∝ taxable *selišta* that census year.
- **Marker shape = historical county** — ● Zagreb · ■ Križevci · ▲ Varaždin ·
  ◆ Virovitica.
- **Marker colour = how confident the location is** — 🟢 exact geocode ·
  🟡 geocoded but the modern identification is uncertain/fuzzy · 🔴 no
  coordinates, so the place is scattered around its **county town**.
- Today's **county borders** and the **Sava/Drava rivers** are drawn for
  geographic context (from OpenStreetMap, embedded — no live map tiles).
- Use the **year slider** (or ▶) to step through the 23 census campaigns; the
  **Table** button shows the underlying numbers; the theme button toggles
  light/dark.
