"""Step 7 — Code-list authority (variant reconciliation for controlled vocab).

Keeps every raw `code` verbatim (100% faithful to the source) but adds a
`canonical` column so equivalent spellings collapse for analysis/visualisation.
Applies to institution_codes, title_codes and status_codes; settlement_types is
already canonical.

Grouping evidence, strongest first:
  1. manual override        (data/manual/code_overrides.csv) — always wins
  2. identical fold key      -> high confidence (drops *, (?), case, w/v, y/i…)
  3. fuzzy fold similarity   -> flagged needs_review (catches typos)

The canonical value for a group is a real attested member: the cleanest (no
`*` / `(?)` marker), then most-used, then longest, then alphabetical. Merge
suggestions that are NOT applied automatically (e.g. a truncated form that is a
token-prefix of a fuller one) are written to
data/interim/code_merge_suggestions.csv for a human to confirm via overrides.

Stdlib only; reuses authority_lib. Deterministic.
"""
import csv
import os
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher

from authority_lib import UnionFind, fold, vowel_skeleton
from common import CLEAN_DIR, INTERIM_DIR, ROOT, ensure_dirs

ENTRIES_CSV = os.path.join(CLEAN_DIR, "tax_entries.csv")
OVERRIDES_CSV = os.path.join(ROOT, "data", "manual", "code_overrides.csv")
SUGGESTIONS_CSV = os.path.join(INTERIM_DIR, "code_merge_suggestions.csv")

FUZZY_THRESHOLD = 0.90   # stricter than places: these strings are longer

# (csv file, extra columns to keep, tax_entries field used for usage weight)
CONFIGS = [
    ("institution_codes.csv", ["english"], "institution_office"),
    ("title_codes.csv", ["english"], "title"),
    ("status_codes.csv", ["english"], "family_status"),
]


def is_marked(code):
    """True if the spelling carries an editor marker / punctuation artefact."""
    return bool(re.search(r"[*]|\(\?\)", code)) or code.strip().endswith(")") \
        and code.count("(") < code.count(")")


def usage_counts(field):
    counts = Counter()
    with open(ENTRIES_CSV, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            v = r.get(field, "")
            if v:
                counts[v] += 1
    return counts


def load_overrides(table):
    """code -> group_key and group_key -> canonical, for one table."""
    if not os.path.exists(OVERRIDES_CSV):
        return {}, {}
    code_group, group_canon = {}, {}
    with open(OVERRIDES_CSV, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["table"].strip() != table:
                continue
            gk = r["group_key"].strip()
            code_group[r["code"]] = gk
            if r.get("canonical"):
                group_canon[gk] = r["canonical"].strip()
    return code_group, group_canon


def suggest_token_prefix(reps):
    """Yield (short, long) canonical pairs where one fold is a token-prefix of
    another — likely truncations a human may want to merge."""
    items = [(fold(r), r) for r in reps]
    for i, (fi, ri) in enumerate(items):
        ti = fi.split()
        for j, (fj, rj) in enumerate(items):
            if i == j or fi == fj:
                continue
            tj = fj.split()
            if len(ti) < len(tj) and tj[:len(ti)] == ti:
                yield ri, rj


def process(table, extra_cols, usage_field, suggestions):
    path = os.path.join(CLEAN_DIR, table)
    with open(path, encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        # idempotent: ignore columns this step may have added on a prior run
        base_cols = [c for c in reader.fieldnames
                     if c not in ("canonical", "needs_review")]
    counts = usage_counts(usage_field)

    uf = UnionFind()
    for r in rows:
        uf.find(r["code"])

    # stage 2: identical fold key
    seen = {}
    for r in rows:
        k = fold(r["code"])
        if k in seen:
            uf.union(r["code"], seen[k])
        else:
            seen[k] = r["code"]

    # stage 3: fuzzy fold similarity (typos) — flagged review afterwards
    codes = [r["code"] for r in rows]
    fk = {code: fold(code) for code in codes}
    blocks = defaultdict(list)
    for code in codes:
        if len(fk[code]) >= 4:
            blocks[fk[code][:1]].append(code)
    for block in blocks.values():
        for i in range(len(block)):
            for j in range(i + 1, len(block)):
                a, b = block[i], block[j]
                if uf.find(a) == uf.find(b):
                    continue
                if SequenceMatcher(None, fk[a], fk[b]).ratio() >= FUZZY_THRESHOLD \
                        and SequenceMatcher(None, vowel_skeleton(fk[a]),
                                            vowel_skeleton(fk[b])).ratio() \
                        >= FUZZY_THRESHOLD:
                    uf.union(a, b)

    # stage 1 (wins): manual overrides
    code_group, group_canon = load_overrides(table.replace(".csv", ""))
    group_of = {code: "AUTO:" + uf.find(code) for code in codes}
    for code, gk in code_group.items():
        if code in group_of:
            group_of[code] = "OV:" + gk

    members = defaultdict(list)
    for r in rows:
        members[group_of[r["code"]]].append(r)

    # choose canonical + write augmented rows
    canon_of = {}
    review_of = {}
    for group, grp_rows in members.items():
        is_manual = group.startswith("OV:")
        root_folds = {fk[r["code"]] for r in grp_rows}
        review = 0 if (is_manual or len(root_folds) <= 1) else 1
        if is_manual and group[3:] in group_canon:
            canonical = group_canon[group[3:]]
        else:
            best = sorted(grp_rows, key=lambda r: (
                is_marked(r["code"]),                 # unmarked first
                -counts.get(r["code"], 0),            # most used
                -len(r["code"]), r["code"]))          # longest, then alpha
            canonical = best[0]["code"]
        for r in grp_rows:
            canon_of[r["code"]] = canonical
            review_of[r["code"]] = review

    out_cols = base_cols + ["canonical", "needs_review"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=out_cols)
        w.writeheader()
        for r in rows:
            r["canonical"] = canon_of[r["code"]]
            r["needs_review"] = review_of[r["code"]]
            w.writerow(r)

    # collect token-prefix suggestions among the canonical forms
    canon_reps = sorted(set(canon_of.values()))
    for short, long in suggest_token_prefix(canon_reps):
        suggestions.append([table.replace(".csv", ""), short, long])

    n_groups = len(members)
    n_merged = sum(1 for g in members.values() if len(g) > 1)
    n_review = len({group_of[c] for c in codes if review_of[c]})
    print(f"  {table}: {len(rows)} codes -> {n_groups} canonical "
          f"({n_merged} merged; {n_review} groups need review)")


def main():
    ensure_dirs()
    suggestions = []
    for table, extra, field in CONFIGS:
        process(table, extra, field, suggestions)
    with open(SUGGESTIONS_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["table", "shorter_form", "fuller_form"])
        w.writerows(suggestions)
    print(f"  merge suggestions (not auto-applied): {len(suggestions)} "
          f"-> {SUGGESTIONS_CSV}")


if __name__ == "__main__":
    main()
