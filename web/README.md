# Web visualizations

Two interactive views of the tax-list data, in one self-contained page
(`index.html`): a **year-by-year map** of taxable *selišta* and a **decline
chart** of the county tax base over 1495–1596.

`index.html` is fully self-contained — the data is inlined, and there are no
external scripts, tiles, fonts or network calls — so it runs from `file://`,
any static host, or a CSP-restricted embed.

## Rebuild

Regenerate `index.html` from the committed database after the pipeline changes:

```bash
python web/build_web.py        # reads db/tax_lists.sqlite, writes web/index.html
```

Only the Python standard library is required (`sqlite3`, `json`). `build_web.py`
computes each place's map position and confidence tier, the per-year burden, and
the county trends, then inlines them into `template.html` — along with the map
context geometry from `geo.json` if present.

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

`index.html` is a single static file — host it anywhere:

- **GitHub Pages**: the workflow in `.github/workflows/pages.yml` rebuilds and
  publishes `web/` on every push to `main`. Enable Pages → "GitHub Actions" in
  the repo settings once.
- **Netlify / any static host / S3**: drop in `web/index.html` (rename to
  `index.html` at the site root if needed).

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
