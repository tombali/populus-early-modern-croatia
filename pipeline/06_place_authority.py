"""Step 6 — Place-name authority / crosswalk.

Historical toponyms are spelled many ways across census years (e.g. Zalathnok
/ Zlathnok / Zalathnak; Petrowina / Pethrouyna / Petthrowyna). This step groups
the raw `places` rows into authority records so analysis can aggregate by a
single canonical place, and emits a reviewable crosswalk.

Grouping evidence, strongest first:
  1. manual override           (data/manual/place_overrides.csv) — always wins
  2. identical orthographic fold key within a county   -> high confidence
  3. shared non-empty modern_place within a county     -> high confidence
  4. fuzzy fold-key similarity within a county          -> flagged needs_review

Only merges within the SAME county are considered. Fuzzy merges and clusters
with conflicting modern identifications are flagged `needs_review = 1` for a
human to confirm or correct via the override file.

Stdlib only (difflib for similarity). Reruns are deterministic.
"""
import csv
import os
from collections import Counter, defaultdict
from difflib import SequenceMatcher

from authority_lib import UnionFind, fold, vowel_skeleton
from common import CLEAN_DIR, ROOT, ensure_dirs, geocode_query

PLACES_CSV = os.path.join(CLEAN_DIR, "places.csv")
ENTRIES_CSV = os.path.join(CLEAN_DIR, "tax_entries.csv")
OVERRIDES_CSV = os.path.join(ROOT, "data", "manual", "place_overrides.csv")
GEOCODE_CACHE = os.path.join(ROOT, "data", "manual", "geocode_cache.csv")
AUTHORITY_CSV = os.path.join(CLEAN_DIR, "place_authority.csv")
CROSSWALK_CSV = os.path.join(CLEAN_DIR, "place_crosswalk.csv")

FUZZY_THRESHOLD = 0.86   # min SequenceMatcher ratio to merge two fold keys
FUZZY_MIN_LEN = 4        # don't fuzzy-merge very short keys

def load_places():
    with open(PLACES_CSV, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def entry_counts():
    counts = Counter()
    with open(ENTRIES_CSV, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["place_id"]:
                counts[r["place_id"]] += 1
    return counts


def load_overrides():
    """place_id -> group_key ; and group_key -> {canonical_name, modern_place}."""
    if not os.path.exists(OVERRIDES_CSV):
        return {}, {}
    pid_group, group_meta = {}, {}
    with open(OVERRIDES_CSV, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            gk = r["group_key"].strip()
            pid_group[r["place_id"].strip()] = gk
            if r.get("canonical_name") or r.get("modern_place"):
                group_meta[gk] = {"canonical_name": (r.get("canonical_name")
                                                     or "").strip(),
                                  "modern_place": (r.get("modern_place")
                                                   or "").strip()}
    return pid_group, group_meta


def load_geocode_cache():
    """query string -> (lat, lon) from the geocode cache, if it exists."""
    if not os.path.exists(GEOCODE_CACHE):
        return {}
    out = {}
    with open(GEOCODE_CACHE, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("lat") and r.get("lon"):
                out[r["query"]] = (r["lat"], r["lon"])
    return out


def main():
    ensure_dirs()
    places = load_places()
    counts = entry_counts()
    geocode = load_geocode_cache()
    for p in places:
        p["fold"] = fold(p["historical_name"])
        p["n_entries"] = counts.get(p["place_id"], 0)

    uf = UnionFind()
    for p in places:
        uf.find(p["place_id"])

    by_county = defaultdict(list)
    for p in places:
        by_county[p["county_id"]].append(p)

    # -- stage 2: identical fold key within county ---------------------------
    for cid, members in by_county.items():
        seen = {}
        for p in members:
            k = p["fold"]
            if k in seen:
                uf.union(p["place_id"], seen[k])
            else:
                seen[k] = p["place_id"]

    # -- stage 3: shared non-empty modern_place within county ----------------
    for cid, members in by_county.items():
        seen = {}
        for p in members:
            m = p["modern_place"].strip().lower().rstrip("?")
            if not m:
                continue
            if m in seen:
                uf.union(p["place_id"], seen[m])
            else:
                seen[m] = p["place_id"]

    # -- stage 4: fuzzy fold-key similarity within county (blocked) ----------
    # Guard: modern_place is a ground-truth identification, so two clusters
    # with conflicting non-empty modern names are DIFFERENT places and must
    # never be fuzzy-merged (this stops chains like Sisak<->Susedgrad). We
    # track each cluster's set of modern names by its union-find root.
    root_moderns = defaultdict(set)
    for p in places:
        m = p["modern_place"].strip().lower().rstrip("?")
        if m:
            root_moderns[uf.find(p["place_id"])].add(m)

    for cid, members in by_county.items():
        blocks = defaultdict(list)
        for p in members:
            if len(p["fold"]) >= FUZZY_MIN_LEN:
                blocks[p["fold"][0]].append(p)      # block by first letter
        for block in blocks.values():
            for i in range(len(block)):
                fi = block[i]["fold"]
                for j in range(i + 1, len(block)):
                    fj = block[j]["fold"]
                    ra = uf.find(block[i]["place_id"])
                    rb = uf.find(block[j]["place_id"])
                    if ra == rb:
                        continue
                    ma, mb = root_moderns[ra], root_moderns[rb]
                    if ma and mb and ma.isdisjoint(mb):
                        continue      # conflicting modern identifications
                    # require both surface form and consonant skeleton close,
                    # so different toponyms sharing a prefix are not merged
                    if SequenceMatcher(None, fi, fj).ratio() >= FUZZY_THRESHOLD \
                            and SequenceMatcher(None, vowel_skeleton(fi),
                                                vowel_skeleton(fj)).ratio() \
                            >= FUZZY_THRESHOLD:
                        uf.union(block[i]["place_id"], block[j]["place_id"])
                        merged = ma | mb
                        root_moderns[uf.find(block[i]["place_id"])] = merged

    # -- stage 1 (applied last so it wins): manual overrides -----------------
    pid_group, group_meta = load_overrides()
    forced = defaultdict(list)
    for pid, gk in pid_group.items():
        forced[gk].append(pid)
    override_pids = set(pid_group)

    # Final grouping: start from union-find, then reassign overridden places.
    group_of = {}
    for p in places:
        group_of[p["place_id"]] = "AUTO:" + uf.find(p["place_id"])
    for gk, pids in forced.items():
        for pid in pids:
            group_of[pid] = "OV:" + gk

    # -- assemble authorities ------------------------------------------------
    members_by_group = defaultdict(list)
    for p in places:
        members_by_group[group_of[p["place_id"]]].append(p)

    # deterministic authority ids: order groups by their smallest place_id
    ordered = sorted(members_by_group.items(),
                     key=lambda kv: min(int(m["place_id"]) for m in kv[1]))
    auth_id = {g: i + 1 for i, (g, _) in enumerate(ordered)}

    auth_rows, cross_rows = [], []
    for group, members in ordered:
        aid = auth_id[group]
        cid = members[0]["county_id"]
        is_manual = group.startswith("OV:")
        folds = {m["fold"] for m in members}
        moderns = Counter(m["modern_place"].strip() for m in members
                          if m["modern_place"].strip())
        # canonical historical name: most entries, then shortest, then alpha
        canon = sorted(members, key=lambda m: (-m["n_entries"],
                                               len(m["historical_name"]),
                                               m["historical_name"]))[0]
        gmeta = group_meta.get(group[3:], {}) if is_manual else {}
        canonical_name = gmeta.get("canonical_name") or canon["historical_name"]
        modern = gmeta.get("modern_place") or (
            moderns.most_common(1)[0][0] if moderns else "")

        conflict = len(moderns) > 1
        if is_manual:
            method = "manual"
        elif len(members) == 1:
            method = "singleton"
        elif len(folds) == 1:
            method = "orthographic-exact"
        elif moderns and not conflict:
            method = "modern"
        else:
            method = "orthographic-fuzzy"
        needs_review = 1 if (method == "orthographic-fuzzy" or conflict) else 0

        lat, lon = geocode.get(geocode_query(modern), ("", ""))

        auth_rows.append([aid, canonical_name, modern, cid, len(members),
                          sum(m["n_entries"] for m in members), method,
                          needs_review, lat, lon])
        for m in members:
            cross_rows.append([m["place_id"], m["historical_name"], cid, aid,
                               method, needs_review])

    auth_rows.sort(key=lambda r: r[0])
    cross_rows.sort(key=lambda r: int(r[0]))

    with open(AUTHORITY_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["authority_id", "canonical_name", "modern_place",
                    "county_id", "n_variants", "n_entries", "method",
                    "needs_review", "lat", "lon"])
        w.writerows(auth_rows)
    with open(CROSSWALK_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["place_id", "historical_name", "county_id",
                    "authority_id", "method", "needs_review"])
        w.writerows(cross_rows)

    merged = sum(1 for r in auth_rows if r[4] > 1)
    review = sum(1 for r in auth_rows if r[7] == 1)
    geocoded = sum(1 for r in auth_rows if r[8])
    print(f"  place_authority.csv: {len(auth_rows)} authorities "
          f"({merged} group >1 spelling; {review} need review; "
          f"{geocoded} geocoded)")
    print(f"  place_crosswalk.csv: {len(cross_rows)} places -> authorities")
    print(f"  collapsed {len(places)} raw places into {len(auth_rows)} "
          f"({len(places) - len(auth_rows)} variant rows merged)")


if __name__ == "__main__":
    main()
