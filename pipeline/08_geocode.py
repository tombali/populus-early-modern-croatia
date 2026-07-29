"""Step 8 — Geocode modern place names (optional, network step).

Resolves each distinct `modern_place` in place_authority to lat/lon via the
OpenStreetMap Nominatim service. Matches are accepted only if they fall inside
the counties the tax lists cover (ALLOWED_COUNTIES), and several query variants
are tried per name to recover compound/abbreviated forms. Results are cached in
data/manual/geocode_cache.csv so each name is queried once; the cache is also
hand-editable (set source=manual to pin a correction). This step is NOT part of
run_all — run it on demand; `06_place_authority.py` then reads the cache to fill
coordinates into place_authority on the normal pipeline run.

Polite usage: one request/second, descriptive User-Agent. Safe to re-run and to
interrupt (progress is flushed per query).
"""
import csv
import json
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
CACHE_COLS = ["query", "lat", "lon", "display_name", "source"]

# The tax lists cover the historical Zagreb / Križevci / Varaždin / Virovitica
# counties. A match is accepted only if its modern županija is one of these,
# which rejects same-name places elsewhere in Croatia (e.g. a "Dolac" in
# Požeško-slavonska or a "Polje" in Dalmatia).
ALLOWED_COUNTIES = {
    "grad zagreb", "zagreb",
    "zagrebačka županija", "krapinsko-zagorska županija",
    "sisačko-moslavačka županija", "karlovačka županija",
    "varaždinska županija", "koprivničko-križevačka županija",
    "bjelovarsko-bilogorska županija", "virovitičko-podravska županija",
}


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


# Fragments too generic to be a useful standalone toponym query.
_GENERIC = {"crkva", "sveti", "sveta", "sv", "općina", "grad", "selo",
            "gornji", "donji", "gornja", "donja", "veliki", "mali"}


def query_variants(name):
    """Alternative phrasings to try for one toponym, most-specific first.

    Recovers compound cells (`LEKENIK. LUKAVEC`, `SUDOVEC I VINAREC`), saint
    abbreviations (`SV. ĐURĐ` -> `Sveti/Sveta Đurđ`) and parenthetical
    qualifiers. The saint abbreviation is expanded BEFORE splitting so its
    trailing dot is not mistaken for a compound separator (which previously
    turned `CRKVA SV. NIKOLE ...` into a spurious `CRKVA SV`).
    """
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


def _search(q):
    """Return (lat, lon, display_name) for the first candidate whose županija is
    in ALLOWED_COUNTIES, else None."""
    params = urllib.parse.urlencode({
        "q": f"{q}, Croatia", "format": "json", "limit": 5,
        "countrycodes": "hr", "addressdetails": 1, "accept-language": "hr",
    })
    req = urllib.request.Request(f"{NOMINATIM}?{params}",
                                 headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    for hit in data:
        addr = hit.get("address", {})
        county = (addr.get("county") or "").strip().lower()
        # Zagreb city has no county; its županija sits in the `city` field.
        city = (addr.get("city") or "").strip().lower()
        if county in ALLOWED_COUNTIES or (not county
                                          and city in ALLOWED_COUNTIES):
            return hit["lat"], hit["lon"], hit.get("display_name", "")
    return None


def geocode_one(name):
    """Try each query variant until one resolves inside the covered counties.

    The display_name is prefixed with the winning variant when it differs from
    the input, so recoveries stay auditable in the cache.
    """
    variants = query_variants(name)
    for i, q in enumerate(variants):
        hit = _search(q)
        if hit:
            lat, lon, disp = hit
            return lat, lon, (f"[via {q!r}] {disp}" if q != name else disp)
        if i + 1 < len(variants):
            time.sleep(DELAY_S)          # stay polite between variant tries
    return None, None, None


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
