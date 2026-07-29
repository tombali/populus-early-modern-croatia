"""Step 10 — Place-mention table (multi-toponym cells).

A single `place_historical` cell can name several toponyms for one holder/count
(compilers' note 5, e.g. `Adamowcz, Thewkowcz`, `Okych-castrum / Ladanye`).
This step splits each cell into its component toponyms and writes a per-mention
table, so a toponym can be found whether it was recorded alone or in a group —
the toponym-level search the compilers' own site supports.

Output data/clean/place_mentions.csv: one row per (place_id, toponym), with the
raw fragment kept for reference. Stdlib only.
"""
import csv
import os
import re

from common import CLEAN_DIR, ensure_dirs

PLACES_CSV = os.path.join(CLEAN_DIR, "places.csv")
MENTIONS_CSV = os.path.join(CLEAN_DIR, "place_mentions.csv")

# Settlement-type / qualifier words that decorate a toponym without being one.
_TYPES = ("castrum", "castellum", "fortalitium", "arx", "oppidum", "villa",
          "praedium", "predium", "curia", "possessio", "abbatia", "capitulum",
          "cantoratus", "villicatus", "villlicatus", "judicatus", "provincia",
          "districtus")


def clean_toponym(fragment):
    """Reduce one comma/slash fragment to a bare toponym (best effort)."""
    f = fragment.strip()
    f = re.sub(r"-\s*(?:%s)\b" % "|".join(_TYPES), "", f, flags=re.I)
    f = re.sub(r"\b(?:%s)\b" % "|".join(_TYPES), "", f, flags=re.I)
    f = re.sub(r"\bcum\s+pertinent\w*", "", f, flags=re.I)
    f = re.sub(r"\bin\s+pertinent\w*", "", f, flags=re.I)
    f = re.sub(r"\bpertinent\w*", "", f, flags=re.I)
    f = re.sub(r"\b(superior|inferior|utraque|sub)\b", "", f, flags=re.I)
    f = re.sub(r"\bapud\b.*$", "", f, flags=re.I)   # "Zenth Ilona apud Zamobor"
    f = f.replace("(", " ").replace(")", " ")
    f = re.sub(r"\s+", " ", f).strip(" -,.*")
    return f


def split_mentions(historical_name):
    """Yield (toponym, raw_fragment) pairs for one place cell."""
    for frag in re.split(r"\s*[,/]\s*", historical_name):
        frag = frag.strip()
        if not frag:
            continue
        top = clean_toponym(frag)
        if top:
            yield top, frag


def main():
    ensure_dirs()
    with open(PLACES_CSV, encoding="utf-8") as fh:
        places = list(csv.DictReader(fh))

    rows = []
    mid = 0
    for p in places:
        seen = set()
        for top, frag in split_mentions(p["historical_name"]):
            key = top.lower()
            if key in seen:
                continue                       # dedupe within one cell
            seen.add(key)
            mid += 1
            rows.append([mid, p["place_id"], top, frag])

    with open(MENTIONS_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["mention_id", "place_id", "toponym", "source_fragment"])
        w.writerows(rows)

    multi = sum(1 for p in places
                if len(set(t for t, _ in split_mentions(p["historical_name"])))
                > 1)
    print(f"  place_mentions.csv: {len(rows)} mentions from {len(places)} "
          f"places ({multi} cells name >1 toponym)")


if __name__ == "__main__":
    main()
