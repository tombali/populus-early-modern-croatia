"""Step 2 — Clean & split.

Read the verbatim raw CSV and produce data/interim/clean_rows.csv where every
overloaded source column has been split into atomic, typed fields, whitespace
is normalised, and uncertainty is captured in explicit flags. Anything that
cannot be parsed cleanly is coerced to a best effort AND logged to
data/interim/parse_issues.csv (nothing is silently dropped).
"""
import csv
import re

from common import (CLEAN_ROWS_CSV, PARSE_ISSUES_CSV, RAW_CSV, ensure_dirs,
                    norm_ws)

# --- county aliases: repair malformed source values (name -> name, latin) ---
# The source has one row reading only "Zagrebčka" (truncated, no Latin gloss),
# which is unambiguously Zagreb county. Add further typo fixes here as found.
COUNTY_ALIASES = {
    "zagrebčka": ("Zagrebačka županija", "Comitatus Zagrabiensis"),
}

# --- settlement-type suffix vocabulary (canonical <- raw variants) ----------
SETTLEMENT_TYPES = {
    "castrum": "castrum", "oppidum": "oppidum", "judicatus": "judicatus",
    "provincia": "provincia", "villicatus": "villicatus",
    "villlicatus": "villicatus", "castellum": "castellum",
    "fortalitium": "fortalitium", "arx": "arx", "cantoratus": "cantoratus",
    "capitulum": "capitulum", "predium": "praedium", "praedium": "praedium",
    "curia": "curia", "abbatia": "abbatia", "districtus": "districtus",
    "possessio": "possessio", "villa": "villa",
}

CLEAN_HEADERS = [
    "source_row", "year", "year_circa", "year_note",
    "tax_type", "rate_forint", "rate_denar", "rate_note",
    "county_name_hr", "comitatus_latin", "provincia", "judge_name",
    "place_historical", "settlement_type",
    "modern_place", "modern_uncertain",
    "first_name", "surname", "family_status",
    "institution_office", "other_holders", "title",
    "taxable_selista", "taxable_uncertain",
    "abandoned_selista", "abandoned_status",
    "inferred",
]

_issues = []


def log_issue(source_row, field, raw, note):
    _issues.append({"source_row": source_row, "field": field,
                    "raw_value": raw, "note": note})


def num_str(x):
    """Format a number without a trailing .0 for whole values."""
    if x is None:
        return ""
    if float(x) == int(x):
        return str(int(x))
    return repr(float(x))


# --- field parsers ----------------------------------------------------------
def parse_year(raw, source_row):
    """-> (year|'', circa bool, note). Extracts first 1400-1700 4-digit year."""
    s = norm_ws(raw)
    if not s:
        return "", "", ""
    circa = bool(re.match(r"(?i)^c[.,\s]", s)) or "circa" in s.lower()
    m = re.search(r"\b(1[4-6]\d\d|170\d)\b", s)
    year = m.group(1) if m else ""
    # Note = the original whenever it is more than the bare year.
    note = "" if s == year else s
    if not year:
        log_issue(source_row, "year", raw, "no 4-digit year found")
    return year, ("1" if circa else ""), note


def parse_tax(raw, source_row):
    """-> (tax_type, rate_forint, rate_denar, rate_note)."""
    s = norm_ws(raw)
    if not s:
        return "", "", "", ""
    parts = re.split(r"\s*[-–]\s*", s, maxsplit=1)
    ttype = parts[0].strip().lower()
    if ttype not in ("dica", "dimnica"):
        log_issue(source_row, "tax_type", raw, f"unexpected type '{ttype}'")
    rate = parts[1] if len(parts) > 1 else ""
    forint = denar = ""
    mf = re.search(r"(\d+(?:[.,]\d+)?)\s*forint", rate, re.I)
    if mf:
        forint = mf.group(1).replace(",", ".")
    md = re.search(r"(\d+(?:[.,]\d+)?)\s*denar", rate, re.I)
    if md:
        denar = md.group(1).replace(",", ".")
    # Anything left after removing the amount clauses becomes a note.
    residual = rate
    for pat in (r"\d+(?:[.,]\d+)?\s*forint\w*", r"\d+(?:[.,]\d+)?\s*denar\w*"):
        residual = re.sub(pat, "", residual, flags=re.I)
    residual = norm_ws(re.sub(r"^[\s,;]+|[\s,;]+$", "", residual))
    rate_note = residual if re.search(r"[A-Za-zČĆŽŠĐčćžšđ]", residual) else ""
    return ttype, forint, denar, rate_note


def parse_county(raw, source_row):
    """-> (name_hr, comitatus_latin, provincia/subdivision)."""
    s = norm_ws(raw)
    if not s:
        return "", "", ""
    if s.lower() in COUNTY_ALIASES:
        name_hr, comitatus = COUNTY_ALIASES[s.lower()]
        return name_hr, comitatus, ""
    m = re.search(r"\(([^)]*)\)", s)
    comitatus = norm_ws(m.group(1)) if m else ""
    name_hr = norm_ws(s[:m.start()]) if m else s
    # Everything after the closing paren is the subdivision, minus separators.
    tail = norm_ws(s[m.end():]) if m else ""
    provincia = norm_ws(re.sub(r"^[\s/–-]+", "", tail))
    return name_hr, comitatus, provincia


def parse_place(raw, source_row):
    """-> (historical_name, settlement_type). Strips a known -<type> suffix."""
    s = norm_ws(raw)
    if not s:
        return "", ""
    m = re.search(r"[-–]\s*([A-Za-z]+)\s*$", s)
    if m and m.group(1).lower() in SETTLEMENT_TYPES:
        stype = SETTLEMENT_TYPES[m.group(1).lower()]
        name = norm_ws(s[:m.start()])
        return name, stype
    return s, ""


def parse_modern(raw, source_row):
    """-> (modern_place, uncertain bool). '?' marks uncertain identification."""
    s = norm_ws(raw)
    uncertain = "?" in s
    name = norm_ws(s.replace("?", ""))
    return name, ("1" if uncertain else "")


def parse_taxable(raw, source_row):
    """-> (value|'', uncertain bool)."""
    s = norm_ws(raw)
    if not s:
        return "", ""
    uncertain = "(?)" in s or "?" in s
    m = re.search(r"-?\d+(?:[.,]\d+)?", s)
    if not m:
        log_issue(source_row, "taxable_selista", raw, "no number")
        return "", ("1" if uncertain else "")
    val = float(m.group(0).replace(",", "."))
    return num_str(val), ("1" if uncertain else "")


def parse_abandoned(raw, source_row):
    """-> (value|'', status text). Numbers and status words may co-occur."""
    s = norm_ws(raw)
    if not s:
        return "", ""
    m = re.search(r"\d+(?:[.,]\d+)?", s)
    val = num_str(float(m.group(0).replace(",", "."))) if m else ""
    # Status = the string with the number removed.
    status = norm_ws(re.sub(r"\d+(?:[.,]\d+)?", "", s)) if m else s
    status = norm_ws(re.sub(r"^[\s-]+|[\s-]+$", "", status))
    return val, status


def main():
    ensure_dirs()
    with open(RAW_CSV, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    with open(CLEAN_ROWS_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CLEAN_HEADERS)
        w.writeheader()
        for row in rows:
            sr = row["source_row"]
            year, circa, ynote = parse_year(row["year_raw"], sr)
            ttype, forint, denar, rnote = parse_tax(row["tax_raw"], sr)
            cname, clatin, prov = parse_county(row["county_raw"], sr)
            place, stype = parse_place(row["place_raw"], sr)
            modern, muncert = parse_modern(row["modern_place_raw"], sr)
            taxable, tuncert = parse_taxable(row["taxable_raw"], sr)
            aband, astatus = parse_abandoned(row["abandoned_raw"], sr)
            # Authors mark editorially-inferred values with '*' (see their
            # methodology notes 6 & 11). Keep the '*' verbatim in the field and
            # additionally surface a row-level flag for easy filtering.
            inferred = "1" if any("*" in (v or "") for k, v in row.items()
                                  if k != "source_row") else ""
            w.writerow({
                "source_row": sr,
                "year": year, "year_circa": circa, "year_note": ynote,
                "tax_type": ttype, "rate_forint": forint,
                "rate_denar": denar, "rate_note": rnote,
                "county_name_hr": cname, "comitatus_latin": clatin,
                "provincia": prov, "judge_name": norm_ws(row["district_raw"]),
                "place_historical": place, "settlement_type": stype,
                "modern_place": modern, "modern_uncertain": muncert,
                "first_name": norm_ws(row["first_name_raw"]),
                "surname": norm_ws(row["surname_raw"]),
                "family_status": norm_ws(row["family_status_raw"]),
                "institution_office": norm_ws(row["institution_raw"]),
                "other_holders": norm_ws(row["other_holders_raw"]),
                "title": norm_ws(row["title_raw"]),
                "taxable_selista": taxable, "taxable_uncertain": tuncert,
                "abandoned_selista": aband, "abandoned_status": astatus,
                "inferred": inferred,
            })

    with open(PARSE_ISSUES_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["source_row", "field",
                                           "raw_value", "note"])
        w.writeheader()
        w.writerows(_issues)

    print(f"Cleaned {len(rows)} rows -> {CLEAN_ROWS_CSV}")
    print(f"Logged {len(_issues)} parse issues -> {PARSE_ISSUES_CSV}")


if __name__ == "__main__":
    main()
