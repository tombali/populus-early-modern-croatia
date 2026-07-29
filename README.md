# Populus — Early-Modern Croatia tax lists

Structured, analysis-ready version of the tax censuses in Ivan Kampuš & Josip
Adamček, *Popisi i obračuni poreza u Hrvatskoj u XV. i XVI. stoljeću* (tax
censuses of Croatia, 15th–16th c.).

The original data is a single flat Excel sheet where several columns pack
multiple facts into one cell, values are untyped, and the geographic hierarchy
repeats on every row. This repo turns it into a clean **star schema** — a
`tax_entries` fact table plus dimension/lookup tables — delivered as UTF-8 CSVs
and a SQLite database, produced by a reproducible pure-Python pipeline.

Coverage: **1495–1596** (~29 census campaigns), **11,792 entries**, 4 counties,
~3,900 places, ~4,250 taxpayers, tax types *dica* and *dimnica*.

## Layout

```
excel/          original .xls (source of truth for the transcription)
pdf/            the scanned book (authority for ambiguous coding)
pipeline/       the ETL steps (stdlib-only; xlrd for the one read step)
data/raw/       verbatim CSV dump of the .xls
data/interim/   cleaned rows + parse_issues.csv
data/clean/     one CSV per schema table (the CSV source of truth)
data/manual/    human curation inputs (place_overrides.csv) — see its README
db/schema.sql   star-schema DDL, indexes, analysis views
db/tax_lists.sqlite   built database (gitignored; rebuild any time)
docs/           data dictionary
```

## Rebuild

Requires Python 3 and `xlrd` (`pip install xlrd`). Everything else is stdlib.
(Note: `pandas` is intentionally avoided — its compiled DLL is blocked by an
Application Control policy on the original machine.)

```bash
cd pipeline
python run_all.py          # extract → clean → dimensions → fact → load → validate
```

Or run any step on its own, e.g. `python 02_clean_split.py`.

## Query examples

```sql
-- Tax burden by county over time
SELECT * FROM v_burden_by_county_year ORDER BY year, county;

-- Abandoned/taxable ratio per campaign
SELECT year, tax_type,
       ROUND(SUM(abandoned_selista) * 1.0 /
             NULLIF(SUM(taxable_selista), 0), 3) AS abandoned_ratio
FROM v_entries_full GROUP BY year, tax_type ORDER BY year;

-- Largest holders (by taxable selišta) in 1520
SELECT surname, first_name, SUM(taxable_selista) AS selista
FROM v_entries_full WHERE year = 1520 AND surname <> ''
GROUP BY surname, first_name ORDER BY selista DESC LIMIT 20;

-- One place's selišta over time, spelling variants merged
SELECT place_canonical, year, SUM(taxable_selista) AS selista
FROM v_entries_authority WHERE place_canonical = 'Zalathnok'
GROUP BY year ORDER BY year;

-- Place-name groups still needing human confirmation
SELECT * FROM v_places_needing_review;

-- Aggregate institutions by canonical form (spelling variants merged)
SELECT institution_canonical, COUNT(*) AS n
FROM v_entries_full WHERE institution_canonical <> ''
GROUP BY institution_canonical ORDER BY n DESC LIMIT 20;
```

## Next steps

- **Geocoding** — fill `places.lat` / `lon` from `modern_place` for mapping.
- **Place authority** — done (`place_authority` / `place_crosswalk`); confirm
  the ~236 `needs_review` groups via `data/manual/place_overrides.csv`.
- **Code-list canonicals** — done (`canonical` columns on institution/title/
  status codes); confirm flagged groups via `data/manual/code_overrides.csv`.
- **Person authority** — still open: reconcile name spelling variants into
  `persons.normalized_name` (~531 variant groups; same technique as places).
- **Judge-name variants** — minor (7 groups in `judicial_districts`); same
  fold technique would fold them if wanted.
- **Visualization** — `v_entries_full` and `v_entries_authority` export cleanly
  to any charting tool.

See `docs/data_dictionary.md` for the full column-by-column mapping.
