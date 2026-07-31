"""Step 8 — Geocode modern place names (optional, network step).

Resolves each distinct `modern_place` in place_authority to lat/lon via the
OpenStreetMap Nominatim service. Geocoding is **county-aware**: the same name
can name different villages in different historical counties (e.g. Zamlača near
Dvor in the south vs Zamlača near Vidovec by Varaždin), so each (county, name)
pair is resolved separately and the candidate **nearest that county's seat**
(within a distance cap) is chosen. Matches must also fall inside the counties
the tax lists cover. Several query variants are tried to recover
compound/abbreviated forms.

Results are cached in data/manual/geocode_cache.csv (keyed by county+name; also
hand-editable — set source=manual to pin a correction). NOT part of run_all;
`06_place_authority.py` reads the cache. Polite: 1 req/s, descriptive
User-Agent. Safe to re-run and interrupt (progress is flushed per query).
"""
import csv
import json
import math
import os
import re
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
CACHE_COLS = ["county", "query", "lat", "lon", "display_name", "source"]

# A match is accepted only if its modern županija is one the tax lists cover.
ALLOWED_COUNTIES = {
    "grad zagreb", "zagreb",
    "zagrebačka županija", "krapinsko-zagorska županija",
    "sisačko-moslavačka županija", "karlovačka županija",
    "varaždinska županija", "koprivničko-križevačka županija",
    "bjelovarsko-bilogorska županija", "virovitičko-podravska županija",
    # medieval Križevec (county 1) reached SE into the Pakrac/Slavonia zone,
    # so its modern successors count too.
    "požeško-slavonska županija", "brodsko-posavska županija",
}

# Historical county seat (modern coords) and how far a match may plausibly sit
# from it. Zagreb was a large county (generous cap); Varaždin was compact.
HIST_SEAT = {"1": (46.0246, 16.5460), "2": (46.3057, 16.3366),
             "3": (45.8319, 17.3836), "4": (45.8144, 15.9780)}
CAP_KM = {"1": 130, "2": 60, "3": 95, "4": 110}


def haversine_km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 6371 * 2 * math.asin(math.sqrt(h))


def load_cache():
    """(county, query) -> row; prefer a real result/miss over a transient error."""
    if not os.path.exists(CACHE_CSV):
        return {}
    out = {}
    with open(CACHE_CSV, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            k = (r.get("county", ""), r["query"])
            if k not in out or out[k].get("source") == "error":
                out[k] = r
    return out


_GENERIC = {"crkva", "sveti", "sveta", "sv", "općina", "grad", "selo",
            "gornji", "donji", "gornja", "donja", "veliki", "mali"}


def query_variants(name):
    """Alternative phrasings to try, most-specific first. Expands the SV. saint
    abbreviation BEFORE splitting so its dot isn't taken as a compound break."""
    bases = [name]
    if re.search(r"(?i)\bsv[.\s]", name):
        bases = [re.sub(r"(?i)\bsv[.\s]+", "Sveti ", name),
                 re.sub(r"(?i)\bsv[.\s]+", "Sveta ", name)]
    out = []
    for base in bases:
        out.append(base)
        for sep in (". ", " I ", " - "):
            if sep in base:
                for part in (base.split(sep)[0], base.split(sep)[-1]):
                    part = part.strip()
                    if len(part) >= 4 and part.lower() not in _GENERIC:
                        out.append(part)
        stripped = re.sub(r"\s*\([^)]*\)", "", base).strip()
        if stripped and stripped != base:
            out.append(stripped)
    seen, uniq = set(), []
    for v in out:
        v = v.strip()
        if v and v.lower() not in seen:
            seen.add(v.lower())
            uniq.append(v)
    return uniq


def _search(q, cid):
    """Among Nominatim candidates in the covered counties and within the county
    cap, return the one NEAREST the historical seat; else None."""
    params = urllib.parse.urlencode({
        "q": f"{q}, Croatia", "format": "json", "limit": 10,
        "countrycodes": "hr", "addressdetails": 1, "accept-language": "hr",
    })
    req = urllib.request.Request(f"{NOMINATIM}?{params}",
                                 headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    seat, cap = HIST_SEAT[cid], CAP_KM[cid]
    best = None
    for hit in data:
        addr = hit.get("address", {})
        county = (addr.get("county") or "").strip().lower()
        city = (addr.get("city") or "").strip().lower()
        if not (county in ALLOWED_COUNTIES
                or (not county and city in ALLOWED_COUNTIES)):
            continue
        d = haversine_km(seat, (float(hit["lat"]), float(hit["lon"])))
        if d <= cap and (best is None or d < best[0]):
            best = (d, hit["lat"], hit["lon"], hit.get("display_name", ""))
    return best[1:] if best else None


def geocode_one(name, cid):
    variants = query_variants(name)
    for i, q in enumerate(variants):
        hit = _search(q, cid)
        if hit:
            lat, lon, disp = hit
            return lat, lon, (f"[via {q!r}] {disp}" if q != name else disp)
        if i + 1 < len(variants):
            time.sleep(DELAY_S)
    return None, None, None


def main():
    ensure_dirs()
    with open(AUTHORITY_CSV, encoding="utf-8") as fh:
        pairs = sorted({(r["county_id"], geocode_query(r["modern_place"]))
                        for r in csv.DictReader(fh)} - {(c, "") for c in "1234"})
    pairs = [p for p in pairs if p[1]]

    cache = load_cache()
    todo = [p for p in pairs
            if p not in cache or cache[p].get("source") == "error"]
    print(f"{len(pairs)} (county,name) pairs; {len(cache)} cached; "
          f"{len(todo)} to fetch (~{len(todo) * DELAY_S / 60:.1f} min)")

    new_file = not os.path.exists(CACHE_CSV)
    with open(CACHE_CSV, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CACHE_COLS)
        if new_file:
            w.writeheader()
        hits = misses = 0
        for i, (cid, name) in enumerate(todo, 1):
            source = "nominatim"
            try:
                lat, lon, disp = geocode_one(name, cid)
            except Exception as e:
                print(f"  ! [{cid}] {name}: {type(e).__name__} {e}",
                      file=sys.stderr)
                lat = lon = disp = None
                source = "error"
            w.writerow({"county": cid, "query": name, "lat": lat or "",
                        "lon": lon or "", "display_name": disp or "",
                        "source": source})
            fh.flush()
            hits += 1 if lat else 0
            misses += 0 if lat else 1
            if i % 25 == 0 or i == len(todo):
                print(f"  {i}/{len(todo)}  hits={hits} misses={misses}")
            time.sleep(DELAY_S)

    print(f"done: {hits} matched, {misses} unmatched -> {CACHE_CSV}")


if __name__ == "__main__":
    main()
