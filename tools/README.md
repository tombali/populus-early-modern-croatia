# tools/ — red-hunting plumbing

Two stdlib-only helpers that collapse the repetitive "locate an unlocated place"
loop into single calls. Both reuse the pipeline's own `fold` / `geocode_key`
(via `sys.path` into `pipeline/`) so their matching is identical to step 06.

## resolve.py — verify → geocode → apply → rebuild, in one call

Replaces the manual loop of editing `place_overrides.csv` + `geocode_cache.csv`
by hand and then running `06 → 05 → validate → build_web` and eyeballing the red
count. **It verifies after the rebuild that each place actually attached its
coordinate** — the geocode-cache key match fails silently otherwise.

```bash
# List remaining reds (tax-sorted), with the place_id to feed back in:
python tools/resolve.py reds                     # all counties
python tools/resolve.py reds --county 2 --holders

# Apply resolutions from JSON (one object or a list), then rebuild + verify:
python tools/resolve.py apply --json res.json
python tools/resolve.py apply --json res.json --dry-run    # validate + preview only
python tools/resolve.py apply --json res.json --no-build   # write CSVs, skip rebuild
```

Resolution object (see the module docstring for all fields):

```json
{"place_ids": [2164, 2167, 2165], "group_key": "mirkovec_c2",
 "modern_place": "Mirkovec", "lat": 46.031, "lon": 16.287,
 "needs_review": 1, "note": "Heller Comitatus Varasdiensis: mit Mirkovec erwähnt"}
```

- `modern_place` and `canonical_name` must **not** contain commas
  (`geocode_key` drops everything after the first comma).
- Omit `lat`/`lon` to reuse an existing `geocode_cache` pin for that
  `(county, modern_place)`.
- Multiple `place_ids` sharing a `group_key` merge into one authority.
- Validation blocks the **whole batch** on any bad row (missing place_id,
  cross-county merge, comma, no coordinate + no existing pin).

## corpus_index.py — persistent, word-boundary corpus search

Indexes `sources/corpus/*.txt` once into `sources/corpus/index.sqlite`
(git-ignored) and matches on **folded whole words**, so the space-stripped
substring noise (`nasena` matching "da**nas se na**lazi") is gone. A full-county
sweep runs in well under a second instead of re-reading ~15 MB per script.

```bash
python tools/corpus_index.py build            # (re)build after corpus changes
python tools/corpus_index.py search "Nassenyna"                 # one term
python tools/corpus_index.py search "Petrowcz" --mode contains  # widen
python tools/corpus_index.py sweep --county 2 --hits-only       # all reds vs corpus
python tools/corpus_index.py sweep --county 1 --holders         # + holder-surname search
```

`--mode word` (default) is highest precision; `prefix` / `contains` widen it.
Rebuild the index whenever a corpus file is added or re-OCR'd.
