"""Step 8 — Geocode modern place names (optional, network step).

Resolves each distinct `modern_place` in place_authority to lat/lon via the
OpenStreetMap Nominatim service, restricted to Croatia. Results are cached in
data/manual/geocode_cache.csv so this only queries each name once; the cache is
also hand-editable (set source=manual to pin a correction). This step is NOT
part of run_all — run it on demand; `06_place_authority.py` then reads the cache
to fill coordinates into place_authority on the normal pipeline run.

Polite usage: one request/second, descriptive User-Agent, Croatia-only. Safe to
re-run and to interrupt (progress is flushed per query).
"""
import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request

from common import CLEAN_DIR, ROOT, ensure_dirs, geocode_query

CACHE_CSV = os.path.join(ROOT, "data", "manual", "geocode_cache.csv")
AUTHORITY_CSV = os.path.join(CLEAN_DIR, "place_authority.csv")
NOMINATIM = "https://nominatim.openstreetmap.org/search"
USER_AGENT = ("populus-early-modern-croatia/1.0 "
              "(historical tax-list GIS; https://github.com/)")
DELAY_S = 1.1                       # honour Nominatim's 1 req/s policy
CACHE_COLS = ["query", "lat", "lon", "display_name", "source"]


def load_cache():
    """query -> row, preferring a successful/genuine-miss row over an error so
    transient network failures are retried on the next run."""
    if not os.path.exists(CACHE_CSV):
        return {}
    out = {}
    with open(CACHE_CSV, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            prev = out.get(r["query"])
            if prev is None or prev.get("source") == "error":
                out[r["query"]] = r
    return out


def geocode_one(name):
    """Return (lat, lon, display_name) or (None, None, None) on no match."""
    params = urllib.parse.urlencode({
        "q": f"{name}, Croatia", "format": "json", "limit": 1,
        "countrycodes": "hr", "accept-language": "hr",
    })
    req = urllib.request.Request(f"{NOMINATIM}?{params}",
                                 headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if not data:
        return None, None, None
    top = data[0]
    return top["lat"], top["lon"], top.get("display_name", "")


def main():
    ensure_dirs()
    with open(AUTHORITY_CSV, encoding="utf-8") as fh:
        queries = sorted({geocode_query(r["modern_place"])
                          for r in csv.DictReader(fh)} - {""})

    cache = load_cache()
    # fetch names never seen, or ones whose only record was a transient error
    todo = [q for q in queries
            if q not in cache or cache[q].get("source") == "error"]
    print(f"{len(queries)} distinct names; {len(cache)} cached; "
          f"{len(todo)} to fetch (~{len(todo) * DELAY_S / 60:.1f} min)")

    new_file = not os.path.exists(CACHE_CSV)
    with open(CACHE_CSV, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CACHE_COLS)
        if new_file:
            w.writeheader()
        hits = misses = 0
        for i, name in enumerate(todo, 1):
            source = "nominatim"
            try:
                lat, lon, disp = geocode_one(name)
            except Exception as e:                       # network/parse hiccup
                print(f"  ! {name}: {type(e).__name__} {e}", file=sys.stderr)
                lat = lon = disp = None
                source = "error"                         # retried next run
            w.writerow({"query": name, "lat": lat or "", "lon": lon or "",
                        "display_name": disp or "", "source": source})
            fh.flush()
            if lat:
                hits += 1
            else:
                misses += 1
            if i % 25 == 0 or i == len(todo):
                print(f"  {i}/{len(todo)}  hits={hits} misses={misses}")
            time.sleep(DELAY_S)

    print(f"done: {hits} matched, {misses} unmatched -> {CACHE_CSV}")


if __name__ == "__main__":
    main()
