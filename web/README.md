# Web visualizations

Interactive views of the tax-list data:

- **Map** (`index.html`) — year-by-year map of taxable *selišta* and county trends
- **Browse** (`explorer.html`) — filter and export all 11,792 entries from `v_entries_full`

Static HTML + sibling JS files. Census data is inlined at rebuild time; no external
tiles, fonts or network calls.

## Source files

| File | Role |
|------|------|
| `template.html` | Map shell → `build_web.py` → `index.html` |
| `map.js` | Map/table UI logic |
| `explorer_template.html` | Browse shell → `build_explorer.py` → `explorer.html` |
| `explorer.js` | Filter/table UI logic |
| `geo.json` | County borders + rivers (optional map context) |

## Rebuild

After pipeline or database changes:

```bash
python web/build_web.py         # map → index.html
python web/build_explorer.py    # browse → explorer.html
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
# then open http://127.0.0.1:8137/index.html or …/explorer.html
```

(Opening `index.html` directly also works in most browsers.)

## Deploy to the web

Deploy the whole `web/` folder (`index.html`, `explorer.html`, `*.js`, `geo.json`):

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
