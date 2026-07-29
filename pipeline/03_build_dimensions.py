"""Step 3 — Build dimension / lookup tables.

Reads data/interim/clean_rows.csv and derives the deduplicated dimension tables
with stable surrogate keys. Natural keys are deterministic (sorted) so reruns
produce identical IDs. Writes one CSV per table to data/clean/.
"""
import csv
import os
from collections import Counter, defaultdict

from common import CLEAN_DIR, CLEAN_ROWS_CSV, ensure_dirs
from glosses import (INSTITUTION_GLOSS, SETTLEMENT_TYPE_GLOSS, STATUS_GLOSS,
                     TITLE_GLOSS)


def write_csv(name, headers, rows):
    path = os.path.join(CLEAN_DIR, name)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(headers)
        w.writerows(rows)
    print(f"  {name}: {len(rows)} rows")


def main():
    ensure_dirs()
    with open(CLEAN_ROWS_CSV, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    # --- counties -----------------------------------------------------------
    county_keys = sorted({(r["county_name_hr"], r["comitatus_latin"])
                          for r in rows if r["county_name_hr"]})
    county_id = {k: i + 1 for i, k in enumerate(county_keys)}
    write_csv("counties.csv", ["county_id", "name_hr", "comitatus_latin"],
              [[county_id[k], k[0], k[1]] for k in county_keys])

    # --- census_campaigns ---------------------------------------------------
    camp_keys = sorted({(r["year"], r["year_circa"], r["year_note"],
                         r["tax_type"]) for r in rows})
    camp_id = {k: i + 1 for i, k in enumerate(camp_keys)}
    write_csv("census_campaigns.csv",
              ["campaign_id", "year", "year_circa", "year_note", "tax_type"],
              [[camp_id[k], k[0], k[1], k[2], k[3]] for k in camp_keys])

    # --- judicial_districts (judge within a county) -------------------------
    dist_keys = sorted({(r["judge_name"], r["county_name_hr"],
                         r["comitatus_latin"])
                        for r in rows if r["judge_name"]})
    dist_id = {k: i + 1 for i, k in enumerate(dist_keys)}
    write_csv("judicial_districts.csv",
              ["district_id", "judge_name", "county_id"],
              [[dist_id[k], k[0], county_id[(k[1], k[2])]] for k in dist_keys])

    # --- places (toponym within a county; modern name consolidated) ---------
    modern_by_place = defaultdict(Counter)
    uncertain_by_place = defaultdict(bool)
    place_keys = set()
    for r in rows:
        if not r["place_historical"]:
            continue
        k = (r["place_historical"], r["county_name_hr"], r["comitatus_latin"])
        place_keys.add(k)
        if r["modern_place"]:
            modern_by_place[k][r["modern_place"]] += 1
        if r["modern_uncertain"] == "1" or (r["modern_place"] == "" and
                                            r["modern_uncertain"] == "1"):
            uncertain_by_place[k] = True
    place_keys = sorted(place_keys)
    place_id = {k: i + 1 for i, k in enumerate(place_keys)}
    place_rows = []
    for k in place_keys:
        modern = (modern_by_place[k].most_common(1)[0][0]
                  if modern_by_place[k] else "")
        uncertain = "1" if uncertain_by_place[k] else ""
        place_rows.append([place_id[k], k[0], county_id[(k[1], k[2])],
                           modern, uncertain, "", ""])  # lat, lon deferred
    write_csv("places.csv",
              ["place_id", "historical_name", "county_id", "modern_place",
               "modern_uncertain", "lat", "lon"], place_rows)

    # --- persons ------------------------------------------------------------
    person_keys = sorted({(r["first_name"], r["surname"]) for r in rows
                          if r["first_name"] or r["surname"]})
    person_id = {k: i + 1 for i, k in enumerate(person_keys)}
    write_csv("persons.csv",
              ["person_id", "first_name", "surname", "normalized_name"],
              [[person_id[k], k[0], k[1], ""] for k in person_keys])

    # --- small controlled vocabularies --------------------------------------
    settlement_codes = sorted({r["settlement_type"] for r in rows
                               if r["settlement_type"]})
    write_csv("settlement_types.csv", ["code", "latin", "english"],
              [[c, *SETTLEMENT_TYPE_GLOSS.get(c, (c, ""))]
               for c in settlement_codes])

    status_codes = sorted({r["family_status"] for r in rows
                           if r["family_status"]})
    write_csv("status_codes.csv", ["code", "english"],
              [[c, STATUS_GLOSS.get(c, "")] for c in status_codes])

    title_codes = sorted({r["title"] for r in rows if r["title"]})
    write_csv("title_codes.csv", ["code", "english"],
              [[c, TITLE_GLOSS.get(c, "")] for c in title_codes])

    inst_codes = sorted({r["institution_office"] for r in rows
                         if r["institution_office"]})
    write_csv("institution_codes.csv", ["code", "english"],
              [[c, INSTITUTION_GLOSS.get(c, "")] for c in inst_codes])

    print("Dimensions built.")


if __name__ == "__main__":
    main()
