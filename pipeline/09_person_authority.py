"""Step 9 — Person name authority.

Fills `persons.normalized_name` with a canonical spelling so orthographic
variants of the same name collapse for analysis, while the raw `first_name` /
`surname` stay verbatim. Same fold technique as places/codes, but exact-fold
only (no fuzzy): first names are standardised Latin, so fuzzy matching would
risk merging genuinely different people (e.g. Georgius vs Gregorius). Cross-fold
merges a human is sure about go in data/manual/person_overrides.csv.

Note: this normalises the *name*, not the *person* — two different people who
share a spelling share a normalized_name. True person disambiguation (widows
named only by a late husband's first name, unnamed heirs — compilers' notes
7-8) needs archival research and is out of scope.
"""
import csv
import os
from collections import Counter, defaultdict

from authority_lib import UnionFind, fold
from common import CLEAN_DIR, ROOT, ensure_dirs

PERSONS_CSV = os.path.join(CLEAN_DIR, "persons.csv")
ENTRIES_CSV = os.path.join(CLEAN_DIR, "tax_entries.csv")
OVERRIDES_CSV = os.path.join(ROOT, "data", "manual", "person_overrides.csv")


def full_name(first, surname):
    return (f"{first} {surname}").strip()


def load_overrides():
    if not os.path.exists(OVERRIDES_CSV):
        return {}, {}
    pid_group, group_canon = {}, {}
    with open(OVERRIDES_CSV, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            gk = r["group_key"].strip()
            pid_group[r["person_id"].strip()] = gk
            if r.get("canonical"):
                group_canon[gk] = r["canonical"].strip()
    return pid_group, group_canon


def main():
    ensure_dirs()
    with open(PERSONS_CSV, encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        persons = list(reader)
    base_cols = [c for c in reader.fieldnames if c != "normalized_name"]

    counts = Counter()
    with open(ENTRIES_CSV, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["person_id"]:
                counts[r["person_id"]] += 1

    uf = UnionFind()
    seen = {}
    for p in persons:
        uf.find(p["person_id"])
        k = fold(full_name(p["first_name"], p["surname"]))
        if k in seen:
            uf.union(p["person_id"], seen[k])
        else:
            seen[k] = p["person_id"]

    # manual overrides win: reassign listed persons to their named group
    pid_group, group_canon = load_overrides()
    group_of = {p["person_id"]: "AUTO:" + uf.find(p["person_id"])
                for p in persons}
    for pid, gk in pid_group.items():
        if pid in group_of:
            group_of[pid] = "OV:" + gk

    members = defaultdict(list)
    for p in persons:
        members[group_of[p["person_id"]]].append(p)

    normalized = {}
    for group, grp in members.items():
        canon = None
        if group.startswith("OV:"):
            canon = group_canon.get(group[3:])
        if not canon:
            best = sorted(grp, key=lambda p: (
                -counts.get(p["person_id"], 0),
                -len(full_name(p["first_name"], p["surname"])),
                full_name(p["first_name"], p["surname"])))[0]
            canon = full_name(best["first_name"], best["surname"])
        for p in grp:
            normalized[p["person_id"]] = canon

    out_cols = base_cols + ["normalized_name"]
    with open(PERSONS_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=out_cols)
        w.writeheader()
        for p in persons:
            p["normalized_name"] = normalized[p["person_id"]]
            w.writerow({c: p[c] for c in out_cols})

    n_groups = len(members)
    merged = sum(1 for g in members.values() if len(g) > 1)
    print(f"  persons: {len(persons)} -> {n_groups} normalized names "
          f"({merged} names group >1 spelling)")


if __name__ == "__main__":
    main()
