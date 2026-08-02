"""Shared helpers for the tax-list ETL pipeline.

Stdlib-only, plus xlrd in the extract step. This began as a workaround: an
Application Control policy on the target machine was blocking pandas' compiled
DLL on import (numpy's loaded fine). That block no longer reproduces (pandas
imports cleanly as of 2026-07), but the stdlib-only design is kept on purpose --
it stays dependency-light and reproducible. Prefer csv/sqlite3/re/difflib/math/
unicodedata over adding third-party packages.
"""
import os
import re
import unicodedata

# Repo-root-relative paths so scripts can run from anywhere.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLS_PATH = os.path.join(ROOT, "excel", "tax-lists-kampuš-adamček.xls")
RAW_DIR = os.path.join(ROOT, "data", "raw")
INTERIM_DIR = os.path.join(ROOT, "data", "interim")
CLEAN_DIR = os.path.join(ROOT, "data", "clean")
DB_DIR = os.path.join(ROOT, "db")

RAW_CSV = os.path.join(RAW_DIR, "tax_lists_raw.csv")
CLEAN_ROWS_CSV = os.path.join(INTERIM_DIR, "clean_rows.csv")
PARSE_ISSUES_CSV = os.path.join(INTERIM_DIR, "parse_issues.csv")

# Column order of the raw dump (source col 14 is empty and dropped).
RAW_HEADERS = [
    "source_row",          # 1-based Excel data-row index (row 1 = first data row)
    "year_raw",            # col 0
    "tax_raw",             # col 1
    "county_raw",          # col 2
    "district_raw",        # col 3
    "place_raw",           # col 4
    "modern_place_raw",    # col 5
    "first_name_raw",      # col 6
    "surname_raw",         # col 7
    "family_status_raw",   # col 8
    "institution_raw",     # col 9
    "other_holders_raw",   # col 10
    "taxable_raw",         # col 11
    "abandoned_raw",       # col 12
    "title_raw",           # col 13
]


def ensure_dirs():
    for d in (RAW_DIR, INTERIM_DIR, CLEAN_DIR, DB_DIR):
        os.makedirs(d, exist_ok=True)


def render_cell(value):
    """Render an xlrd cell value as a clean string.

    Excel stores every number as a float, so integral floats become plain
    ints (1495.0 -> "1495") while fractional values keep their decimals
    (0.5 -> "0.5"). Text passes through unchanged.
    """
    if isinstance(value, float):
        if value == int(value):
            return str(int(value))
        return repr(value)
    return str(value)


def norm_ws(s):
    """Collapse internal whitespace and strip ends. NFC-normalise unicode."""
    if s is None:
        return ""
    s = unicodedata.normalize("NFC", str(s))
    s = s.replace("\xa0", " ")  # non-breaking space
    return re.sub(r"\s+", " ", s).strip()


def blank(s):
    return norm_ws(s) == ""


def geocode_query(modern):
    """Normalise a `modern_place` value into a geocoder query string.

    Takes the first toponym of a compound value and drops the '?' uncertainty
    marker. Returns "" when there is nothing to geocode.
    """
    m = norm_ws(modern)
    if not m or m == "?":
        return ""
    m = m.split(",")[0].strip()          # first toponym of a compound value
    m = re.sub(r"\s*\([^)]*\)", "", m)    # drop qualifiers like "(INF.)"
    return m.rstrip("?").strip()


def geocode_key(modern):
    """Case-insensitive cache key for a modern place. The geocode cache mixes
    ALL-CAPS source names with proper-cased manual pins, so match on casefold
    to keep both spellings interchangeable."""
    return geocode_query(modern).casefold()


# Croatian lowercase particles that stay lowercase mid-name.
_PLACE_LOWER = {"na", "pod", "kod", "nad", "pri", "za", "uz", "iz", "do",
                "od", "u", "i", "sa", "ob"}


def title_place(name):
    """Re-case an ALL-CAPS modern place name to Croatian naming conventions
    (e.g. "GORNJA STUBICA" -> "Gornja Stubica", "NOVIGRAD NA DOBRI" ->
    "Novigrad na Dobri"). Mixed-case values are already curated and returned
    unchanged so hand-cased names/diacritics are never clobbered."""
    m = norm_ws(name)
    # drop stray leading/trailing commas (keep internal ones of compounds)
    m = re.sub(r"^[\s,]+|[\s,]+$", "", m)
    letters = [c for c in m if c.isalpha()]
    if not letters or not all(c.isupper() for c in letters):
        return m                          # only normalise pure ALL-CAPS values

    def cap(tok):
        return "-".join(p[:1].upper() + p[1:] if p else p
                        for p in tok.split("-"))

    out, first = [], True
    for tok in m.lower().split(" "):
        if not tok:
            continue
        # a leading particle still capitalises (start of a name/segment)
        if not first and tok.rstrip(",") in _PLACE_LOWER:
            out.append(tok)
        else:
            out.append(cap(tok))
        first = tok.endswith(",")         # segment restart after a comma
    return " ".join(out)
