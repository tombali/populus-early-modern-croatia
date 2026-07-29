"""Step 6 — Validate the built database against the source.

Reconciles row counts and taxable-selišta sums between the raw extract and the
SQLite fact table, checks FK integrity, and prints a short data-health report.
Exit code is non-zero if any hard check fails.
"""
import csv
import os
import sqlite3
import sys

from common import CLEAN_ROWS_CSV, DB_DIR, RAW_CSV

DB_PATH = os.path.join(DB_DIR, "tax_lists.sqlite")


def to_float(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return 0.0


def main():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()
    ok = True

    def check(label, condition, detail=""):
        nonlocal ok
        status = "PASS" if condition else "FAIL"
        if not condition:
            ok = False
        print(f"  [{status}] {label}{('  — ' + detail) if detail else ''}")

    # --- row reconciliation -------------------------------------------------
    with open(RAW_CSV, encoding="utf-8") as fh:
        raw_rows = list(csv.DictReader(fh))
    n_raw = len(raw_rows)
    n_fact = cur.execute("SELECT COUNT(*) FROM tax_entries").fetchone()[0]
    check("fact rows == raw rows", n_fact == n_raw, f"{n_fact} vs {n_raw}")

    n_distinct_src = cur.execute(
        "SELECT COUNT(DISTINCT source_row) FROM tax_entries").fetchone()[0]
    check("every source_row present exactly once",
          n_distinct_src == n_fact, f"{n_distinct_src} distinct")

    # --- taxable-selišta sum reconciliation ---------------------------------
    with open(CLEAN_ROWS_CSV, encoding="utf-8") as fh:
        clean_rows = list(csv.DictReader(fh))
    sum_clean = round(sum(to_float(r["taxable_selista"]) for r in clean_rows), 3)
    sum_db = cur.execute(
        "SELECT ROUND(SUM(taxable_selista), 3) FROM tax_entries").fetchone()[0]
    check("SUM(taxable_selista) DB == clean CSV",
          abs((sum_db or 0) - sum_clean) < 1e-6, f"{sum_db} vs {sum_clean}")

    # --- FK integrity -------------------------------------------------------
    fk = cur.execute("PRAGMA foreign_key_check").fetchall()
    check("no foreign-key violations", not fk, f"{len(fk)} violations")

    # --- place authority / crosswalk coverage -------------------------------
    n_places = cur.execute("SELECT COUNT(*) FROM places").fetchone()[0]
    n_cross = cur.execute("SELECT COUNT(*) FROM place_crosswalk").fetchone()[0]
    check("every place has a crosswalk row", n_places == n_cross,
          f"{n_cross}/{n_places}")
    unresolved = cur.execute(
        "SELECT COUNT(*) FROM tax_entries e WHERE e.place_id IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM place_crosswalk x "
        "WHERE x.place_id = e.place_id)").fetchone()[0]
    check("every placed entry resolves to an authority", unresolved == 0,
          f"{unresolved} unresolved")

    # --- data-health report (informational) ---------------------------------
    print("\nData-health report:")
    year_span = cur.execute(
        "SELECT MIN(year), MAX(year) FROM census_campaigns "
        "WHERE year IS NOT NULL").fetchone()
    print(f"  year span: {year_span[0]}–{year_span[1]}")
    print("  parse issues logged: %d" % _count_csv(
        os.path.join(os.path.dirname(RAW_CSV), "..", "interim",
                     "parse_issues.csv")))
    for tbl in ("institution_codes", "title_codes", "status_codes"):
        distinct = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        canon = cur.execute(
            f"SELECT COUNT(DISTINCT canonical) FROM {tbl}").fetchone()[0]
        rev = cur.execute(
            f"SELECT COUNT(*) FROM {tbl} WHERE needs_review = 1").fetchone()[0]
        print(f"  {tbl}: {distinct} codes -> {canon} canonical ({rev} review)")
    n_auth = cur.execute("SELECT COUNT(*) FROM place_authority").fetchone()[0]
    n_rev = cur.execute("SELECT COUNT(*) FROM place_authority "
                        "WHERE needs_review = 1").fetchone()[0]
    print(f"  place authorities: {n_auth} (from {n_places} raw places; "
          f"{n_rev} need review — see v_places_needing_review)")
    for tbl in ("counties", "census_campaigns", "judicial_districts",
                "places", "persons", "tax_entries"):
        n = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  {tbl}: {n}")
    no_place = cur.execute(
        "SELECT COUNT(*) FROM tax_entries WHERE place_id IS NULL").fetchone()[0]
    print(f"  entries with no place_id: {no_place}")
    no_modern = cur.execute(
        "SELECT COUNT(*) FROM places WHERE modern_place IS NULL "
        "OR modern_place = ''").fetchone()[0]
    print(f"  places lacking a modern identification: {no_modern} "
          f"(feeds the geocoding phase)")
    ungloss = cur.execute(
        "SELECT COUNT(*) FROM institution_codes WHERE english IS NULL "
        "OR english = ''").fetchone()[0]
    print(f"  institution codes still un-glossed: {ungloss}")

    # --- smoke query --------------------------------------------------------
    print("\nSmoke query — taxable selišta by county (all years):")
    for row in cur.execute(
            "SELECT co.name_hr, ROUND(SUM(e.taxable_selista)) "
            "FROM tax_entries e JOIN counties co ON co.county_id = e.county_id "
            "GROUP BY co.name_hr ORDER BY 2 DESC"):
        print(f"    {row[0]}: {int(row[1] or 0)}")

    con.close()
    print("\nRESULT:", "ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
    sys.exit(0 if ok else 1)


def _count_csv(path):
    if not os.path.exists(path):
        return 0
    with open(path, encoding="utf-8") as fh:
        return sum(1 for _ in fh) - 1


if __name__ == "__main__":
    main()
