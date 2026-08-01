"""Build the static data explorer (web/explorer.html).

Exports entry rows joined to place_authority (canonical/modern names + geocode)
from db/tax_lists.sqlite, with person/status fields from v_entries_full.
Stdlib only.
"""
import json
import os
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "db", "tax_lists.sqlite")
TEMPLATE = os.path.join(ROOT, "web", "explorer_template.html")
OUT = os.path.join(ROOT, "web", "explorer.html")

COLS = [
    "entry_id", "year", "tax_type", "county", "judge_name",
    "place", "place_canonical", "modern_place",
    "first_name", "surname",
    "family_status_canonical", "title_canonical", "institution_canonical",
    "taxable_selista", "abandoned_selista", "inferred",
]

QUERY = """
    SELECT a.entry_id, a.year, a.tax_type, a.county, f.judge_name,
           a.place_historical, a.place_canonical, a.place_modern,
           f.first_name, f.surname,
           f.family_status_canonical, f.title_canonical, f.institution_canonical,
           a.taxable_selista, a.abandoned_selista, f.inferred
    FROM v_entries_authority a
    JOIN v_entries_full f ON f.entry_id = a.entry_id
    ORDER BY a.year, a.county, a.place_historical, a.entry_id
"""


def build():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    rows = cur.execute(QUERY).fetchall()
    ix = COLS.index
    years = sorted({r[ix("year")] for r in rows if r[ix("year")] is not None})
    counties = sorted({r[ix("county")] for r in rows if r[ix("county")]})
    tax_types = sorted({r[ix("tax_type")] for r in rows if r[ix("tax_type")]})
    geocoded = cur.execute(
        "SELECT COUNT(*) FROM v_entries_authority WHERE lat IS NOT NULL"
    ).fetchone()[0]
    con.close()

    data = {
        "cols": COLS,
        "rows": rows,
        "years": years,
        "counties": counties,
        "taxTypes": tax_types,
    }

    with open(TEMPLATE, encoding="utf-8") as fh:
        html = fh.read()
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    html = html.replace("/*__DATA__*/null", payload)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)

    print(f"  entries: {len(rows)} ({geocoded} with coordinates)")
    print(f"  wrote {OUT} ({os.path.getsize(OUT) // 1024} KB)")


if __name__ == "__main__":
    build()
