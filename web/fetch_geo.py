"""Fetch + simplify map context geometry, cached to web/geo.json.

County borders come from OSM Nominatim (polygon_geojson); rivers (Sava, Drava,
Mura, Kupa) from the Overpass API. Geometry is simplified (Douglas-Peucker) so
it inlines small, keeping web/map.html self-contained. Network step, run
rarely; skips work if web/geo.json already exists (use --force to refetch).

Stdlib only. Polite: 1 req/s, descriptive User-Agent.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "geo.json")
UA = {"User-Agent": "populus-early-modern-croatia/1.0 (historical GIS)"}
BBOX = (45.0, 15.0, 47.0, 18.35)          # S, W, N, E
EPS = 0.006                                # simplify tolerance (~0.6 km)

COUNTIES = [
    "Grad Zagreb", "Zagrebačka županija", "Krapinsko-zagorska županija",
    "Sisačko-moslavačka županija", "Karlovačka županija",
    "Varaždinska županija", "Koprivničko-križevačka županija",
    "Bjelovarsko-bilogorska županija", "Virovitičko-podravska županija",
    # Drawn for context; js/map.js does not let these expand the initial frame.
    "Međimurska županija", "Požeško-slavonska županija",
]


def get(url, data=None, timeout=90):
    req = urllib.request.Request(url, data=data, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def overpass(ql, timeout=180):
    """Run an Overpass query, retrying on gateway timeout / rate limit."""
    data = urllib.parse.urlencode({"data": ql}).encode()
    url = "https://overpass-api.de/api/interpreter"
    for attempt in range(4):
        try:
            return get(url, data=data, timeout=timeout)
        except urllib.error.HTTPError as e:
            if e.code in (429, 504) and attempt < 3:
                wait = 8 * (attempt + 1)
                print(f"  overpass {e.code}, retrying in {wait}s…",
                      file=sys.stderr)
                time.sleep(wait)
                continue
            raise


def _perp(p, a, b):
    (x, y), (x1, y1), (x2, y2) = p, a, b
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return ((x - x1) ** 2 + (y - y1) ** 2) ** .5
    t = ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)
    t = max(0, min(1, t))
    return ((x - (x1 + t * dx)) ** 2 + (y - (y1 + t * dy)) ** 2) ** .5


def dp(pts, eps=EPS):
    if len(pts) < 3:
        return pts
    dmax, idx = 0, 0
    for i in range(1, len(pts) - 1):
        d = _perp(pts[i], pts[0], pts[-1])
        if d > dmax:
            dmax, idx = d, i
    if dmax > eps:
        return dp(pts[:idx + 1], eps)[:-1] + dp(pts[idx:], eps)
    return [pts[0], pts[-1]]


def rings_from_geojson(geom):
    """Outer rings only, as lists of [lon,lat], simplified."""
    polys = (geom["coordinates"] if geom["type"] == "MultiPolygon"
             else [geom["coordinates"]])
    out = []
    for poly in polys:
        ring = [[round(x, 5), round(y, 5)] for x, y in poly[0]]
        s = dp(ring)
        if len(s) >= 4:
            out.append(s)
    return out


def fetch_counties():
    counties = []
    for name in COUNTIES:
        q = urllib.parse.urlencode({"q": f"{name}, Croatia", "format": "json",
                                    "limit": 1, "polygon_geojson": 1,
                                    "countrycodes": "hr"})
        try:
            d = get(f"https://nominatim.openstreetmap.org/search?{q}")
            geom = d[0]["geojson"]
            rings = rings_from_geojson(geom)
            counties.append({"name": name, "rings": rings})
            print(f"  county {name}: {sum(len(r) for r in rings)} pts")
        except Exception as e:
            print(f"  ! {name}: {type(e).__name__} {e}", file=sys.stderr)
        time.sleep(1.1)
    return counties


def _river_kind(name):
    """Classify an OSM river name, or None to skip."""
    n = (name or "").strip().lower()
    if not n or n.startswith("stara drava"):
        return None
    if n.startswith("sava"):
        return "Sava"
    # Drava / Dráva (and bilingual "Drava / Dráva") on different ways
    if (n.startswith("drava") or n.startswith("dráva")
            or " drava" in n or " dráva" in n):
        return "Drava"
    # Mura / Mur (de)
    if n.startswith("mura") or n == "mur" or n.startswith("mur "):
        return "Mura"
    # Kupa (hr) / Kolpa (sl)
    if n.startswith("kupa") or n.startswith("kolpa"):
        return "Kupa"
    return None


# Overpass name regex → canonical label. Each result is re-checked by _river_kind.
RIVER_QUERIES = (
    ("Sava", "^Sava"),
    ("Drava", "Drava|Dráva"),
    ("Mura", "^Mura|^Mur$|^Mur "),
    ("Kupa", "Kupa|Kolpa"),
)


def fetch_rivers():
    s, w, n, e = BBOX
    rivers = {label: [] for label, _ in RIVER_QUERIES}
    for label, pattern in RIVER_QUERIES:
        ql = (f'[out:json][timeout:120];'
              f'way["waterway"="river"]["name"~"{pattern}",i]'
              f'({s},{w},{n},{e});out geom;')
        d = overpass(ql)
        for elem in d.get("elements", []):
            nm = elem.get("tags", {}).get("name", "")
            kind = _river_kind(nm)
            g = elem.get("geometry")
            if kind and g:
                line = [[round(p["lon"], 5), round(p["lat"], 5)] for p in g]
                if len(line) >= 2:
                    rivers[kind].append(dp(line))
        print(f"  river {label}: {len(rivers[label])} segments")
        time.sleep(1.5)
    order = ["Drava", "Mura", "Sava", "Kupa"]
    return [{"name": k, "lines": rivers[k]} for k in order if rivers.get(k)]


def main():
    if os.path.exists(OUT) and "--force" not in sys.argv:
        print(f"{OUT} exists; use --force to refetch"); return
    geo = {"counties": fetch_counties(), "rivers": fetch_rivers()}
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(geo, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {OUT} ({os.path.getsize(OUT)//1024} KB)")


if __name__ == "__main__":
    main()
