"""Step 5 — Load the clean CSVs into a SQLite database.

Applies db/schema.sql then bulk-loads each dimension and the fact table (in FK
dependency order). Empty CSV strings are converted to NULL so numeric/FK
columns type correctly. Uses only the stdlib sqlite3 module.
"""
import csv
import os
import sqlite3

from common import CLEAN_DIR, DB_DIR, ROOT, ensure_dirs

DB_PATH = os.path.join(DB_DIR, "tax_lists.sqlite")
SCHEMA_PATH = os.path.join(ROOT, "db", "schema.sql")

# (table, csv file, column order) — load parents before children.
LOAD_ORDER = [
    ("counties", "counties.csv",
     ["county_id", "name_hr", "comitatus_latin"]),
    ("census_campaigns", "census_campaigns.csv",
     ["campaign_id", "year", "year_circa", "year_note", "tax_type"]),
    ("judicial_districts", "judicial_districts.csv",
     ["district_id", "judge_name", "county_id"]),
    ("settlement_types", "settlement_types.csv", ["code", "latin", "english"]),
    ("status_codes", "status_codes.csv",
     ["code", "english", "canonical", "needs_review"]),
    ("title_codes", "title_codes.csv",
     ["code", "english", "canonical", "needs_review"]),
    ("institution_codes", "institution_codes.csv",
     ["code", "english", "canonical", "needs_review"]),
    ("places", "places.csv",
     ["place_id", "historical_name", "county_id", "modern_place",
      "modern_uncertain"]),
    ("persons", "persons.csv",
     ["person_id", "first_name", "surname", "normalized_name"]),
    ("place_authority", "place_authority.csv",
     ["authority_id", "canonical_name", "modern_place", "county_id",
      "n_variants", "n_entries", "method", "needs_review", "lat", "lon"]),
    ("place_crosswalk", "place_crosswalk.csv",
     ["place_id", "historical_name", "county_id", "authority_id",
      "method", "needs_review"]),
    ("tax_entries", "tax_entries.csv", None),  # None -> use CSV header order
]


def load_table(cur, table, filename, columns):
    path = os.path.join(CLEAN_DIR, filename)
    with open(path, encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        cols = columns or reader.fieldnames
        placeholders = ",".join("?" for _ in cols)
        sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})"
        batch = [tuple((r[c] if r[c] != "" else None) for c in cols)
                 for r in reader]
    cur.executemany(sql, batch)
    return len(batch)


def main():
    ensure_dirs()
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    with open(SCHEMA_PATH, encoding="utf-8") as fh:
        con.executescript(fh.read())

    cur = con.cursor()
    for table, filename, columns in LOAD_ORDER:
        n = load_table(cur, table, filename, columns)
        print(f"  loaded {n:>6} -> {table}")
    con.commit()

    # Integrity check: no orphan foreign keys.
    violations = con.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        print(f"FK VIOLATIONS: {len(violations)} (showing 5) {violations[:5]}")
    else:
        print("FK check: OK (no orphans)")

    con.close()
    print(f"Database written -> {DB_PATH}")


if __name__ == "__main__":
    main()
