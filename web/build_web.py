"""Build the self-contained web visualization (web/index.html).

Queries db/tax_lists.sqlite, computes per-place map positions + confidence
tiers, per-year tax burden, and county trends, then inlines the data as JSON
into web/template.html. Output is a single dependency-free HTML file: no
external scripts, tiles, fonts or network calls, so it works as a static file
and as a CSP-restricted artifact. Stdlib only.
"""
import csv  # noqa: F401  (kept for parity; not required)
import json
import math
import os
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "db", "tax_lists.sqlite")
TEMPLATE = os.path.join(ROOT, "web", "template.html")
OUT = os.path.join(ROOT, "web", "index.html")

SKIP_YEARS = (1578, 1675)          # single-row transcription typos

# county_id -> short label, modern capital [lat, lon], and categorical colors
# (reference palette slots 1-4; color follows the entity, not its rank).
COUNTIES = {
    4: {"name": "Zagreb",     "cap": [45.8144, 15.9780],
        "light": "#2a78d6", "dark": "#3987e5"},
    1: {"name": "Križevci",   "cap": [46.0246, 16.5460],
        "light": "#eb6834", "dark": "#d95926"},
    2: {"name": "Varaždin",   "cap": [46.3057, 16.3366],
        "light": "#1baf7a", "dark": "#199e70"},
    3: {"name": "Virovitica", "cap": [45.8319, 17.3836],
        "light": "#eda100", "dark": "#c98500"},
}

GOLDEN = math.pi * (3 - math.sqrt(5))   # phyllotaxis angle for fallback spread


def build():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # --- authorities: position + confidence tier -------------------------
    auth = list(cur.execute("""
        SELECT pa.authority_id AS id, pa.canonical_name AS name,
               COALESCE(pa.modern_place, '') AS modern, pa.county_id AS county,
               pa.lat AS lat, pa.lon AS lon, pa.needs_review AS review,
               MAX(COALESCE(pl.modern_uncertain, 0)) AS uncertain
        FROM place_authority pa
        LEFT JOIN place_crosswalk x ON x.authority_id = pa.authority_id
        LEFT JOIN places pl         ON pl.place_id    = x.place_id
        GROUP BY pa.authority_id"""))

    # deterministic fallback spread: rank the red authorities within a county
    fallback_rank, fallback_n = {}, {}
    for r in auth:
        if r["lat"] is None:
            fallback_n[r["county"]] = fallback_n.get(r["county"], 0) + 1
    seen = {}
    places = []
    for r in auth:
        cty = r["county"]
        if r["lat"] is not None:
            lat, lon = r["lat"], r["lon"]
            tier = 1 if (r["review"] or r["uncertain"]) else 0   # yellow / green
        else:
            i = seen.get(cty, 0)
            seen[cty] = i + 1
            n = max(fallback_n.get(cty, 1), 1)
            # phyllotaxis disc around the county capital (~0.02..0.42 deg)
            rad = 0.42 * math.sqrt((i + 0.5) / n)
            ang = i * GOLDEN
            clat, clon = COUNTIES[cty]["cap"]
            lat = clat + rad * math.sin(ang)
            lon = clon + rad * math.cos(ang) / math.cos(math.radians(clat))
            tier = 2                                             # red / no geo
        places.append([r["id"], r["name"], r["modern"], cty,
                       round(lat, 5), round(lon, 5), tier])

    # --- per-year burden per authority -----------------------------------
    burden = {}
    for r in cur.execute("""
        SELECT year, authority_id AS id,
               ROUND(SUM(taxable_selista), 1)   AS taxable,
               ROUND(SUM(abandoned_selista), 1) AS abandoned
        FROM v_entries_authority
        WHERE year IS NOT NULL AND authority_id IS NOT NULL
        GROUP BY year, authority_id"""):
        if r["year"] in SKIP_YEARS:
            continue
        burden.setdefault(str(r["year"]), []).append(
            [r["id"], r["taxable"] or 0, r["abandoned"] or 0])

    # --- county trends over time -----------------------------------------
    trends = {}
    for r in cur.execute("""
        SELECT year, county_id AS cty,
               ROUND(SUM(taxable_selista))   AS taxable,
               ROUND(SUM(abandoned_selista)) AS abandoned,
               COUNT(*)                      AS n
        FROM tax_entries e
        JOIN census_campaigns c ON c.campaign_id = e.campaign_id
        WHERE c.year IS NOT NULL AND e.county_id IS NOT NULL
        GROUP BY c.year, e.county_id"""):
        if r["year"] in SKIP_YEARS:
            continue
        trends.setdefault(str(r["cty"]), []).append(
            [r["year"], r["taxable"] or 0, r["abandoned"] or 0, r["n"]])

    years = sorted({int(y) for y in burden})
    con.close()

    # optional map context geometry (county borders + rivers), if fetched
    geo = {"counties": [], "rivers": []}
    geo_path = os.path.join(ROOT, "web", "geo.json")
    if os.path.exists(geo_path):
        with open(geo_path, encoding="utf-8") as fh:
            geo = json.load(fh)

    tier_counts = [sum(1 for p in places if p[6] == t) for t in (0, 1, 2)]
    data = {
        "counties": {str(k): v for k, v in COUNTIES.items()},
        "places": places,
        "years": years,
        "burden": burden,
        "trends": trends,
        "tierCounts": tier_counts,
        "geo": geo,
    }

    with open(TEMPLATE, encoding="utf-8") as fh:
        html = fh.read()
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    html = html.replace("/*__DATA__*/null", payload)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)

    print(f"  places: {len(places)} "
          f"(green {tier_counts[0]}, yellow {tier_counts[1]}, "
          f"red {tier_counts[2]})")
    print(f"  years: {len(years)} ({years[0]}-{years[-1]})")
    print(f"  wrote {OUT} ({os.path.getsize(OUT) // 1024} KB)")


if __name__ == "__main__":
    build()
