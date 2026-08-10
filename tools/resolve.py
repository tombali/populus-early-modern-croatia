"""resolve.py — one-shot place resolution: verify -> geocode -> apply -> rebuild.

The manual loop for locating an unlocated ("red") place used to be a dozen
hand steps: look up its place_id, hand-write a Nominatim script, edit
place_overrides.csv, edit geocode_cache.csv, then run 06 -> 05 -> validate ->
build_web and eyeball the red count. This collapses all of that into one call
and — crucially — VERIFIES after the rebuild that each place actually attached
its coordinate, because the geocode-cache key match is silent when it fails.

Stdlib only (csv, sqlite3, subprocess, json). Reuses the pipeline's own
geocode_key/title_place so the cache-key match is identical to step 06.

Usage
-----
  # Resolve reds (one JSON object per resolution, or a list of them):
  python tools/resolve.py apply --json path/to/resolutions.json
  python tools/resolve.py apply --json -              # read JSON from stdin
  python tools/resolve.py apply --json res.json --dry-run     # no writes
  python tools/resolve.py apply --json res.json --no-build    # write, skip rebuild

  # List remaining reds (optionally by county), tax-sorted, with holders:
  python tools/resolve.py reds
  python tools/resolve.py reds --county 2

Resolution object
-----------------
  {
    "place_ids": [2164, 2167, 2165],   # one or more raw place ids to merge
    "group_key": "mirkovec_c2",        # shared key -> one authority
    "modern_place": "Mirkovec",        # NO commas; "(...)" and "?" allowed
    "lat": 46.031, "lon": 16.287,      # omit to reuse an existing cache pin
    "canonical_name": "Nassenyna",     # optional; defaults to a member's name
    "needs_review": 1,                 # default 1 (yellow); 0 = green
    "note": "Heller Varasdiensis ..."  # optional provenance -> display_name
  }
"""
import argparse
import csv
import json
import os
import sqlite3
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
from common import geocode_key, title_place  # noqa: E402  (pipeline helper reuse)

OVERRIDES = os.path.join(ROOT, "data", "manual", "place_overrides.csv")
GEOCACHE = os.path.join(ROOT, "data", "manual", "geocode_cache.csv")
DB = os.path.join(ROOT, "db", "tax_lists.sqlite")
PY = sys.executable

OVERRIDE_COLS = ["place_id", "group_key", "canonical_name", "modern_place",
                 "needs_review"]
GEOCACHE_COLS = ["county", "query", "lat", "lon", "display_name", "source"]


# ---- small csv helpers (append-mode, trailing-newline safe) ----------------

def _read(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _append_rows(path, cols, rows):
    """Append rows to a CSV, guaranteeing a newline before the first one."""
    if os.path.exists(path) and os.path.getsize(path):
        with open(path, "rb") as fh:
            fh.seek(-1, os.SEEK_END)
            needs_nl = fh.read(1) != b"\n"
    else:
        needs_nl = False
    with open(path, "a", encoding="utf-8", newline="") as fh:
        if needs_nl:
            fh.write("\n")
        w = csv.writer(fh)
        for r in rows:
            w.writerow([r[c] for c in cols])


# ---- DB lookups ------------------------------------------------------------

def _db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def _place_index(con):
    """place_id -> (county_id, historical_name)."""
    return {str(r["place_id"]): (str(r["county_id"]), r["historical_name"])
            for r in con.execute(
                "SELECT place_id, county_id, historical_name FROM places")}


def _red_count(con):
    return con.execute(
        "SELECT COUNT(*) FROM place_authority "
        "WHERE COALESCE(hide_from_map,0)=0 AND lat IS NULL").fetchone()[0]


def _authority_of(con, place_id):
    """Post-rebuild: (authority_id, canonical_name, lat) the place landed in."""
    r = con.execute(
        "SELECT pa.authority_id, pa.canonical_name, pa.lat "
        "FROM place_crosswalk pc JOIN place_authority pa "
        "  ON pa.authority_id = pc.authority_id "
        "WHERE pc.place_id = ?", (place_id,)).fetchone()
    return (r["authority_id"], r["canonical_name"], r["lat"]) if r else None


# ---- validation ------------------------------------------------------------

def _validate(res, i, pidx):
    """Return (errors, county). Pure checks against the current DB."""
    errs = []
    pids = [str(p) for p in res.get("place_ids", [])]
    if not pids:
        errs.append(f"[{i}] no place_ids")
    if not res.get("group_key"):
        errs.append(f"[{i}] no group_key")
    modern = (res.get("modern_place") or "").strip()
    if not modern:
        errs.append(f"[{i}] no modern_place")
    if "," in (res.get("canonical_name") or ""):
        errs.append(f"[{i}] canonical_name must not contain a comma")
    if "," in modern:
        errs.append(f"[{i}] modern_place must not contain a comma "
                    f"(geocode_key drops everything after it): {modern!r}")
    counties = set()
    for pid in pids:
        if pid not in pidx:
            errs.append(f"[{i}] place_id {pid} not found in DB")
        else:
            counties.add(pidx[pid][0])
    if len(counties) > 1:
        errs.append(f"[{i}] place_ids span multiple counties {sorted(counties)}"
                    f" — geocode attaches per-county; split into separate "
                    f"resolutions")
    county = res.get("county")
    if county is not None and counties and str(county) not in counties:
        errs.append(f"[{i}] declared county {county} != place county "
                    f"{sorted(counties)}")
    county = str(county) if county is not None else (
        next(iter(counties)) if counties else None)
    have_coord = res.get("lat") not in (None, "") and \
        res.get("lon") not in (None, "")
    return errs, county, modern, have_coord


# ---- apply -----------------------------------------------------------------

def cmd_apply(args):
    raw = sys.stdin.read() if args.json == "-" else open(
        args.json, encoding="utf-8").read()
    data = json.loads(raw)
    if isinstance(data, dict):
        data = [data]

    con = _db()
    pidx = _place_index(con)
    cache = _read(GEOCACHE)
    # existing (county, key) -> has a coord already?
    cache_keys = {(r["county"], geocode_key(r["query"]))
                  for r in cache if r.get("lat") and r.get("lon")}
    existing_overrides = {(r["place_id"], r["group_key"]) for r in _read(OVERRIDES)}

    # keys any resolution in THIS batch supplies coords for, so a later
    # coord-less row merging into the same (county, modern) is recognised.
    batch_keys = set()
    for res in data:
        county = res.get("county")
        pids = [str(p) for p in res.get("place_ids", [])]
        if county is None and pids and pids[0] in pidx:
            county = pidx[pids[0]][0]
        if county is not None and res.get("lat") not in (None, "") \
                and res.get("lon") not in (None, ""):
            batch_keys.add((str(county), geocode_key(res.get("modern_place") or "")))

    all_errs, plan = [], []
    for i, res in enumerate(data):
        errs, county, modern, have_coord = _validate(res, i, pidx)
        key = (county, geocode_key(modern)) if county else None
        # cache_hit = pin ALREADY in the on-disk cache (drives whether we write
        # a new pin). A sibling batch row supplying the coord relaxes the
        # "needs a coordinate" check but must NOT suppress the actual write.
        cache_hit = key in cache_keys if key else False
        satisfied = cache_hit or (key in batch_keys if key else False)
        if not have_coord and not satisfied and not errs:
            errs.append(f"[{i}] {modern!r} has no lat/lon and no existing "
                        f"geocode_cache pin for county {county} — supply "
                        f"coordinates")
        all_errs += errs
        plan.append(dict(res=res, county=county, modern=modern,
                         have_coord=have_coord, cache_hit=cache_hit, key=key))

    if all_errs:
        print("VALIDATION FAILED — nothing written:")
        for e in all_errs:
            print("  " + e)
        con.close()
        return 1

    reds_before = _red_count(con)
    con.close()

    ov_rows, gc_rows, notices = [], [], []
    seen_cache = set()
    for p in plan:
        res, county, modern = p["res"], p["county"], p["modern"]
        gk = res["group_key"].strip()
        nr = str(res.get("needs_review", 1)).strip() or "1"
        canon_default = pidx[str(res["place_ids"][0])][1]
        canon = (res.get("canonical_name") or canon_default).strip()
        for pid in (str(x) for x in res["place_ids"]):
            if (pid, gk) in existing_overrides:
                notices.append(f"  · place {pid} already mapped to '{gk}' "
                               f"(skipped duplicate override row)")
                continue
            ov_rows.append({"place_id": pid, "group_key": gk,
                            "canonical_name": canon, "modern_place": modern,
                            "needs_review": nr})
        # geocode cache row only when we have fresh coords AND none exists yet
        if p["have_coord"] and not p["cache_hit"] and p["key"] not in seen_cache:
            seen_cache.add(p["key"])
            gc_rows.append({
                "county": county, "query": modern,
                "lat": str(res["lat"]), "lon": str(res["lon"]),
                "display_name": (res.get("note") or modern), "source": "manual"})
        elif p["cache_hit"]:
            notices.append(f"  · reused existing geocode pin for '{modern}' "
                           f"(county {county})")

    print(f"Resolutions: {len(plan)}   override rows: +{len(ov_rows)}   "
          f"geocode pins: +{len(gc_rows)}")
    for n in notices:
        print(n)
    if args.dry_run:
        print("\n--dry-run: no files written, no rebuild.")
        for r in ov_rows:
            print(f"  OVERRIDE  {r['place_id']},{r['group_key']},"
                  f"{r['canonical_name']},{r['modern_place']},{r['needs_review']}")
        for r in gc_rows:
            print(f"  GEOCODE   {r['county']},{r['query']},{r['lat']},{r['lon']}")
        return 0

    if ov_rows:
        _append_rows(OVERRIDES, OVERRIDE_COLS, ov_rows)
    if gc_rows:
        _append_rows(GEOCACHE, GEOCACHE_COLS, gc_rows)

    if args.no_build:
        print("\n--no-build: CSVs written; rerun pipeline manually to apply.")
        return 0

    if not _rebuild():
        print("\nREBUILD FAILED — see output above. CSVs were written; "
              "fix and rerun the pipeline.")
        return 2

    # ---- verify the attach actually happened -------------------------------
    con = _db()
    reds_after = _red_count(con)
    print(f"\nReds: {reds_before} -> {reds_after}  "
          f"(resolved {reds_before - reds_after})")
    problems = 0
    for p in plan:
        for pid in (str(x) for x in p["res"]["place_ids"]):
            got = _authority_of(con, pid)
            if not got or got[2] is None:
                problems += 1
                print(f"  ✗ place {pid} ({p['modern']}) did NOT attach a "
                      f"coordinate — check county/geocode_key match")
    con.close()
    if problems:
        print(f"\n⚠ {problems} place(s) rebuilt WITHOUT coordinates — "
              f"the resolution silently failed. Investigate before trusting.")
        return 3
    print("✓ all resolved places verified with coordinates attached.")
    return 0


def _rebuild():
    steps = [("pipeline/06_place_authority.py", "authority"),
             ("pipeline/05_load_sqlite.py", "load"),
             ("pipeline/validate.py", "validate"),
             ("web/build_web.py", "web")]
    for script, label in steps:
        p = subprocess.run([PY, script], cwd=ROOT, capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        lines = [ln for ln in (p.stdout or "").strip().splitlines() if ln.strip()]
        # for validate, surface the RESULT line specifically; else the last line
        tail = next((ln for ln in reversed(lines) if "RESULT" in ln),
                    lines[-1] if lines else "")
        print(f"  [{label}] {tail}")
        if p.returncode != 0:
            print(p.stdout)
            print(p.stderr)
            return False
    return True


# ---- reds ------------------------------------------------------------------

def cmd_reds(args):
    con = _db()
    tax = {r["a"]: (r["t"] or 0) for r in con.execute(
        "SELECT authority_id a, ROUND(SUM(taxable_selista),1) t "
        "FROM v_entries_authority WHERE authority_id IS NOT NULL "
        "GROUP BY authority_id")}
    sp, pids = {}, {}
    for r in con.execute(
            "SELECT authority_id a, historical_name h, place_id p "
            "FROM place_crosswalk"):
        sp.setdefault(r["a"], set()).add(r["h"])
        pids.setdefault(r["a"], set()).add(r["p"])
    q = ("SELECT authority_id a, canonical_name n, county_id c "
         "FROM place_authority WHERE COALESCE(hide_from_map,0)=0 AND lat IS NULL")
    if args.county:
        q += f" AND county_id = {int(args.county)}"
    reds = [dict(r) for r in con.execute(q)]
    reds.sort(key=lambda r: -tax.get(r["a"], 0))

    def holders(ps):
        ph = ",".join("?" * len(ps))
        out = set()
        for r in con.execute(
            f"SELECT DISTINCT p.surname, p.first_name, te.institution_office "
            f"FROM tax_entries te LEFT JOIN persons p ON te.person_id=p.person_id "
            f"WHERE te.place_id IN ({ph})", list(ps)):
            v = " ".join(x for x in (r["first_name"], r["surname"],
                                     r["institution_office"]) if x)
            if v:
                out.add(v[:30])
        return "; ".join(sorted(out)[:4])

    print(f"{len(reds)} reds" + (f" in county {args.county}" if args.county
                                 else "") + ":")
    for r in reds:
        a = r["a"]
        print(f"  [pid {min(pids.get(a, [0]))}] c{r['c']} tax={tax.get(a,0):<6} "
              f"{r['n'][:28]:<28} | {'|'.join(sorted(sp.get(a, {r['n']})))[:55]}")
        if args.holders:
            print(f"        holders: {holders(pids.get(a, []))}")
    con.close()
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("apply", help="apply resolutions from JSON, then rebuild")
    a.add_argument("--json", required=True, help="path to JSON file, or '-' for stdin")
    a.add_argument("--dry-run", action="store_true", help="validate + preview, no writes")
    a.add_argument("--no-build", action="store_true", help="write CSVs but skip rebuild")
    a.set_defaults(func=cmd_apply)
    r = sub.add_parser("reds", help="list remaining reds (tax-sorted)")
    r.add_argument("--county", type=int, help="filter to a county id (1-4)")
    r.add_argument("--holders", action="store_true", help="also show holder names")
    r.set_defaults(func=cmd_reds)
    args = ap.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
