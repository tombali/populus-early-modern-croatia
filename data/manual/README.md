# Manual curation inputs

These files let a human correct the automatic pipeline. They are read by the
pipeline if present and always take priority over the automatic logic. Edit
them, then re-run `python pipeline/run_all.py`.

## `place_overrides.csv`

Overrides the automatic place-name authority grouping
(`pipeline/06_place_authority.py`). Columns:

| column | required | meaning |
|---|---|---|
| `place_id` | yes | a raw place id from `data/clean/places.csv` |
| `group_key` | yes | free label; all rows sharing a `group_key` are forced into the **same** authority |
| `canonical_name` | no | force the canonical name for that group |
| `modern_place` | no | force the modern identification for that group |

**A place listed here is removed from whatever the algorithm decided** and
placed in the group you name — so this both *merges* places the algorithm kept
apart and *splits* places it wrongly merged.

### How to find what needs fixing

Query the database view that lists low-confidence groups:

```sql
SELECT * FROM v_places_needing_review;      -- fuzzy / conflicting merges
```

Look up the `place_id`s for the spellings involved:

```sql
SELECT place_id, historical_name, county_id FROM places
WHERE historical_name IN ('Zalathnok', 'Zlathnok', 'Zalathnak');
```

### Examples

Force three spellings into one authority and name it:

```csv
place_id,group_key,canonical_name,modern_place
3421,zalathnok,Zalathnok,ZLATNIK
3690,zalathnok,Zalathnok,ZLATNIK
3420,zalathnok,Zalathnok,ZLATNIK
```

Split a place the algorithm wrongly absorbed — give it its own unique
`group_key`:

```csv
place_id,group_key,canonical_name,modern_place
1234,not-sisak-something-else,Something Else,
```

## `code_overrides.csv`

Overrides the automatic canonical grouping of the controlled vocabularies
(`pipeline/07_code_authority.py`). Columns:

| column | required | meaning |
|---|---|---|
| `table` | yes | which code list: `institution_codes`, `title_codes`, or `status_codes` |
| `code` | yes | the verbatim `code` value to reassign |
| `group_key` | yes | free label; all rows sharing one force the same canonical group |
| `canonical` | no | the canonical label for that group |

Candidate merges the algorithm did **not** apply automatically (a shorter form
that is a token-prefix of a fuller one) are listed in
`data/interim/code_merge_suggestions.csv`. Review that file and, to accept a
merge, add override rows. Query low-confidence auto-merges with:

```sql
SELECT code, canonical FROM institution_codes WHERE needs_review = 1;
```

### Example — merge all spellings of the Turopolje noble commune

```csv
table,code,group_key,canonical
institution_codes,Nobiles Campi Zagrabiensis,nobiles-campi-zagrabiensis,Turopoljska plemenita općina (Nobiles Campi Zagrabiensis)
institution_codes,Nobiles campi,nobiles-campi-zagrabiensis,Turopoljska plemenita općina (Nobiles Campi Zagrabiensis)
institution_codes,Nobiles campi Zagrabiensis,nobiles-campi-zagrabiensis,Turopoljska plemenita općina (Nobiles Campi Zagrabiensis)
```

## `geocode_cache.csv`

Coordinate cache produced by `pipeline/08_geocode.py` (OSM Nominatim, Croatia).
`06_place_authority.py` reads it to fill `place_authority.lat` / `lon`. Columns:
`query`, `lat`, `lon`, `display_name`, `source`.

- A row with empty `lat` is a name Nominatim could not match — **fill `lat`/`lon`
  by hand and set `source` to `manual`** to pin it.
- `08_geocode.py` never re-queries a name already present (except rows whose
  `source` is `error`, which it retries), so manual rows are preserved.
- To force a re-geocode of one name, delete its row and re-run `08_geocode.py`.

## `person_overrides.csv`

Overrides the automatic person name-normalisation
(`pipeline/09_person_authority.py`). Columns: `person_id`, `group_key`,
`canonical`. Persons sharing a `group_key` get the same `normalized_name`; use
it to merge spelling variants that fold differently (e.g. a dropped vowel), or
to set a preferred canonical spelling. Auto-merging is exact-fold only, so this
is where cross-fold family-name merges go.
