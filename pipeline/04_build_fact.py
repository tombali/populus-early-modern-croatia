"""Step 4 — Build the fact table.

Joins data/interim/clean_rows.csv against the dimension CSVs (by the same
natural keys used to build them) and emits data/clean/tax_entries.csv, one row
per source entry, with surrogate foreign keys resolved.
"""
import csv
import os

from common import CLEAN_DIR, CLEAN_ROWS_CSV, ensure_dirs


def load_lookup(name, key_cols, id_col):
    """Return {natural_key_tuple: id} from a dimension CSV."""
    path = os.path.join(CLEAN_DIR, name)
    out = {}
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out[tuple(r[c] for c in key_cols)] = r[id_col]
    return out


FACT_HEADERS = [
    "entry_id", "source_row", "campaign_id", "county_id", "district_id",
    "place_id", "person_id", "settlement_type", "provincia",
    "rate_forint", "rate_denar", "rate_note",
    "family_status", "title", "institution_office", "other_holders",
    "taxable_selista", "taxable_uncertain",
    "abandoned_selista", "abandoned_status",
]


def main():
    ensure_dirs()
    counties = load_lookup("counties.csv",
                           ["name_hr", "comitatus_latin"], "county_id")
    campaigns = load_lookup("census_campaigns.csv",
                            ["year", "year_circa", "year_note", "tax_type"],
                            "campaign_id")
    districts = load_lookup("judicial_districts.csv",
                            ["judge_name", "county_id"], "district_id")
    places = load_lookup("places.csv",
                         ["historical_name", "county_id"], "place_id")
    persons = load_lookup("persons.csv",
                          ["first_name", "surname"], "person_id")

    with open(CLEAN_ROWS_CSV, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    out_path = os.path.join(CLEAN_DIR, "tax_entries.csv")
    orphans = 0
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FACT_HEADERS)
        w.writeheader()
        for i, r in enumerate(rows, start=1):
            cid = counties.get((r["county_name_hr"], r["comitatus_latin"]), "")
            campaign = campaigns[(r["year"], r["year_circa"],
                                  r["year_note"], r["tax_type"])]
            did = districts.get((r["judge_name"], cid), "") if cid else ""
            pid = places.get((r["place_historical"], cid), "") if cid else ""
            person = persons.get((r["first_name"], r["surname"]), "") \
                if (r["first_name"] or r["surname"]) else ""
            if r["judge_name"] and not did:
                orphans += 1
            w.writerow({
                "entry_id": i,
                "source_row": r["source_row"],
                "campaign_id": campaign,
                "county_id": cid,
                "district_id": did,
                "place_id": pid,
                "person_id": person,
                "settlement_type": r["settlement_type"],
                "provincia": r["provincia"],
                "rate_forint": r["rate_forint"],
                "rate_denar": r["rate_denar"],
                "rate_note": r["rate_note"],
                "family_status": r["family_status"],
                "title": r["title"],
                "institution_office": r["institution_office"],
                "other_holders": r["other_holders"],
                "taxable_selista": r["taxable_selista"],
                "taxable_uncertain": r["taxable_uncertain"],
                "abandoned_selista": r["abandoned_selista"],
                "abandoned_status": r["abandoned_status"],
            })

    print(f"Fact table: {len(rows)} entries -> {out_path}")
    if orphans:
        print(f"WARNING: {orphans} rows had a judge_name with no district FK")


if __name__ == "__main__":
    main()
