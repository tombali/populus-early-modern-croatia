# Populus - Early-Modern Croatia tax lists

Structured, analysis-ready version of the tax censuses published in Ivan Kampuš
& Josip Adamček, *Popisi i obračuni poreza u Hrvatskoj u XV. i XVI. stoljeću*
(tax censuses and accounts of Croatia, 15th-16th c.).

This project turns the Excel transcription of the data from the Adamček and Kampuš book into a
clean, analysis-ready dataset:

- **Ready-to-use SQLite database** - the fully built,
  queryable database is committed at **`db/tax_lists.sqlite`**. Open it and
  start querying immediately - no build step required.
- **Normalised star schema** - a `tax_entries` fact table plus dimension and
  lookup tables, with typed columns and stable identifiers.
- **Two delivery formats** - UTF-8 CSVs as the source of truth, plus the built
  **SQLite** database above with ready-made analysis views.
- **Reproducible, pure-Python pipeline** - one command rebuilds everything;
  no heavyweight dependencies.
- **Nothing from the source is discarded** - every cleaned row keeps its
  original Excel row number for traceability.
- **Raw spellings preserved** - kept verbatim alongside the merged/canonical
  forms used for analysis, so fidelity and usability coexist.

## Credits

The original Excel transcription comes from the **Department of Croatian
History / demography section, Faculty of Humanities and Social Sciences,
University of Zagreb (FFZG)**:
<https://www.ffzg.unizg.hr/pov/zavod/demografija/>. Because these are
proto-statistical sources, the compilers documented the limits of the
processing here: <https://www.ffzg.unizg.hr/pov/zavod/demografija/?q=node/8>
(summarised in `docs/methodology.md`).

**Data entry (2007-2008; results published 2009):** Nataša Štefanec (project
lead), Tomislav Bali, Branimir Brgles, Stipe Mlikotić, Damir Stanić, Andreja
Talan.

The transcription was carried out within:
- the project *"Triplex Confinium: hrvatska riječna višegraničja"*, Odsjek za
  povijest, Zavod za hrvatsku povijest, Filozofski fakultet u Zagrebu
- the compulsory course *"Hrvatska povijest u ranom novom vijeku"*, Odsjek za
  povijest, Filozofski fakultet u Zagrebu.

The original Excel file is included in this repository at
`excel/tax-lists-kampuš-adamček.xls`.

## Data processing

Excel file is faithful to the data from the book, but hard to compute on: several columns pack multiple
facts into one cell, values are untyped and inconsistently spelled, the
geographic hierarchy repeats on every row, and there are no stable identifiers.

**Coverage:**

- ~29 census campaigns, **1495-1596**
- **11,792 entries**
- 4 counties
- ~3,900 raw places (≈1,800 after variant merging)
- ~4,250 taxpayers
- tax types *dica* (land tax) and *dimnica* (hearth tax)

Each entry records a holder's parcel/estate in a place in one campaign, with
counts of taxable and abandoned *selišta* (serf-plots / hearths; Lat. *porta*,
*fumus*).

The original sheet is **11,814 rows × 15 columns** (the 15th column is empty),
one row per taxpayer holding. The columns, in Croatian, were:

`GODINA UBIRANJA POREZA` · `VRSTA I IZNOS POREZA` · `ŽUPANIJA (COMITATUS)` ·
`KOTAR PLEMIĆKOG SUCA` · `MJESTO` · `MJESTO DANAS` · `IME…` · `PREZIME…` ·
`OBITELJSKI STATUS…` · `PRVI POSJEDNIK: INSTITUCIJA, SLUŽBA` · `OSTALI
POSJEDNICI…` · `BROJ OPOREZIVIH SELIŠTA` · `BROJ NAPUŠTENIH… SELIŠTA` ·
`TITULA…`

Profiling every column surfaced the following problems.

### 1. Pre-statistical recording irregularities
These are 16th-century pre-statistical records, and the compilers' own codebook
(captured in `docs/methodology.md`) documents irregularities that no automated
process fully resolves:
- a holder may be listed with **no place**, or a place with **no holder**;
- following holders are **assumed** to belong to the last-named place;
- when several people share a group of selišta without a per-person split, the
  extras go in `other_holders`;
- a cell may list **several toponyms** for one holder/count (kept together);
- often only a first name or only a surname is given;
- widows/sons/orphans are hard to identify without archival research.

Most importantly, the compilers mark any **editorially inferred value with an
asterisk `*`** (e.g. a surname inferred from the preceding entry, or any value
the source implies but doesn't state). This repo keeps the `*` verbatim **and**
sets `tax_entries.inferred = 1` on such rows (254 rows), so inferred data can be
filtered (`WHERE inferred = 0`) rather than silently trusted. The compilers'
authoritative list of **23 processed census years** is used by `validate.py`;
two stray single-row years (`1578`, `1675`) fall outside it and are flagged as
likely typos.

### 2. Overloaded cells - several facts crammed into one column
Many columns mixed multiple pieces of information, which blocks filtering,
grouping and math.

| Column | Example raw value | Facts jammed together |
|---|---|---|
| Tax type + amount | `Dica-1 forinta, 25 denara` · `dimnica-8 denara` | tax type + forint rate + denar rate + free-text note |
| County | `Križevačka županija (Comitatus Crisiensis)-Provincia Dombrensis` | county name + Latin gloss + sub-division, with mixed separators `-` `/` ` / ` |
| Place | `Rachchya-oppidum` · `Pokwpye-castrum` | toponym + settlement-type qualifier (`castrum` 236×, `oppidum` 159×, `praedium`, `villicatus`, …) |
| Abandoned selišta | `desolatus-per mortem 2` · `1 desertum` | a number **and** a Latin status word |
| Modern place | `PODBREŽJE?` | modern name + an embedded `?` uncertainty marker |

**Solved** in `pipeline/02_clean_split.py`: each overloaded column is parsed
into atomic, typed fields (e.g. `tax_type`, `rate_forint`, `rate_denar`,
`rate_note`; `place_historical` + `settlement_type`; `abandoned_selista` +
`abandoned_status`). Every rule is regex-based and logged.

### 3. Dirty, untyped values
- **Trailing/duplicate whitespace** made "the same" value look distinct
  (`Dica   `, `Relicta `, `Domini  `, `Comitatus Varasdiensis `).
- **The year column held non-years**: `c, 1500` (circa, 102×), range/annotation
  notes like `NEDOSTAJE 193-197` and `Nedostaje 1517: 89-97, 105-112`, plus a
  stray `1675` and a lone `1578`.
- **Numbers carried inline uncertainty**: `8(?)` in the otherwise-numeric
  taxable column; halves such as `0.5` are legitimate.

**Solved** in step 2: whitespace is collapsed and Unicode NFC-normalised;
`year` is extracted as an integer with a separate `year_circa` flag and
`year_note`; numerics are coerced to REAL with explicit `taxable_uncertain` /
`modern_uncertain` flags. Anything unparseable is **logged, never dropped**
(see `data/interim/parse_issues.csv` - currently a single folio-only
annotation).

### 4. Text-encoding damage
Croatian diacritics (č/ć/ž/š/đ) were mangled in intermediate tooling. The whole
pipeline reads and writes **UTF-8** end to end, so `Križevačka županija`,
`Zagrebačka`, etc. round-trip correctly.

### 5. Heavy denormalisation & no identifiers
County, Latin gloss, judicial-district (named by its noble judge), and campaign
metadata were repeated on all 11k rows, and there were **no stable IDs** to join
or link on.

**Solved** in `03_build_dimensions.py` / `04_build_fact.py`: the data is
normalised into a **star schema** with surrogate keys - a `tax_entries` fact
table referencing dimension tables (`census_campaigns`, `counties`,
`judicial_districts`, `places`, `persons`) and controlled-vocabulary code lists
(`settlement_types`, `status_codes`, `title_codes`, `institution_codes`).

### 6. Place-name spelling variants across census years
The biggest analytical hazard. The same toponym is transliterated many ways
across decades of Latin scribes - e.g. `Petrowina` / `Pethrouyna` /
`Petthrowyna`, or the town that appears as `Zalathnok` in 1507/1513 but
`Zlathnok` in 1517. Grouping on the raw name splits one place's history into
several fragments.

**Solved** in `06_place_authority.py`, which builds a **place authority /
crosswalk**: it keeps every raw spelling but assigns each to a canonical place.
It collapses 3,866 raw places to ~1,808 canonical ones using, strongest first:
manual override → identical orthographic *fold key* (a normalisation that
folds `cz→c`, `w→v`, `y→i`, `th→t`, doubled letters, etc.) → shared modern-place
name → fuzzy fold similarity (flagged for review). A guard **refuses to merge
two places with conflicting known modern names** (so Sisak ≠ Susedgrad,
Karlovec ≠ Guščerovec). Result: `Zalathnok`/`Zlathnok`/`Zalathnak` now form one
series (1507: 61 → 1513: 88 → 1517: 87 selišta).

### 7. Controlled-vocabulary spelling variants
The same institutions/titles/statuses were written many ways - editor markers
(`Episcopus Zagrabiensis)*`, `…(?)`), case (`Nobiles Campi` vs `campi`), typos
(`Strigoninesis` vs `strigoniensis`), and orthography (`…de Wereucze` vs
`…Werewcze`).

**Solved** in `07_code_authority.py`: `status_codes`, `title_codes` and
`institution_codes` keep the verbatim `code` **and** gain a `canonical` column
(same fold + fuzzy + override logic). Truncations that fold differently - e.g.
`Nobiles campi` vs `Nobiles campi Zagrabiensis` - are surfaced in
`data/interim/code_merge_suggestions.csv` and confirmed by hand; the five
spellings of the Turopolje noble commune are merged this way in
`data/manual/code_overrides.csv`.

## Verification

The structured data was spot-checked against random pages scanned from *Popisi i obračuni poreza u Hrvatskoj u XV. i XVI. stoljeću*. Transcription fidelity is **excellent**:

- **1574, doc. #91, Zamobor** (*Processus Blasii Pogledych*): all 6 entries
  matched exactly - place, holder, taxable *fumi*, and the split-out
  *"Desertati fumi 3/2"* abandoned counts.
- **1517, Slavonia list**: `Monozlo 253`, `Zylagh…Palatinus 0`, `Valpo 400`,
  `Walpho 350`, `Zwhamlaka 56`, `Rahowcza provincia 216`, `Bakowcza relicte
  47/desolati 2` - all matched, including abandoned-status parsing.
- The only apparent "miss" was a **search** using the wrong spelling: the 1517
  Zalathnok town is transcribed `Zlathnok` - present and correct, and exactly
  the kind of variant the place authority now reconciles.

## The resulting schema

**Fact table - `tax_entries`** (grain: one source row; keeps `source_row`):
campaign/county/district/place/person foreign keys, `settlement_type`,
`provincia`, `rate_forint`/`rate_denar`/`rate_note`, `family_status`, `title`,
`institution_office`, `other_holders`, `taxable_selista` (+`taxable_uncertain`),
`abandoned_selista` (+`abandoned_status`), and `inferred` (see below).

**Dimensions / lookups:** `census_campaigns`, `counties`, `judicial_districts`,
`places`, `persons` (with `normalized_name`), `settlement_types`,
`status_codes`, `title_codes`, `institution_codes`, plus the
variant-reconciliation tables `place_authority` and `place_crosswalk`, and
`place_mentions` (one row per toponym named in a place cell).

**Views:**
- `v_entries_full` - fully denormalised entries (raw values **and** the
  `*_canonical` code columns) for export/charting;
- `v_entries_authority` - entries with the variant-merged canonical place and
  its geocoded `lat`/`lon`;
- `v_burden_by_county_year` - taxable & abandoned selišta by county × year × type;
- `v_places_needing_review` - low-confidence place groups awaiting confirmation.

See `docs/data_dictionary.md` for the full column-by-column mapping and code
lists.

## Pipeline

```
pipeline/
  common.py             shared paths + whitespace/number helpers
  authority_lib.py      shared fold / fuzzy / union-find logic
  glosses.py            Latin→English glosses for the code lists
  01_extract.py         xlrd .xls  -> data/raw/tax_lists_raw.csv (verbatim)
  02_clean_split.py     split overloaded cols, type + flag, log parse issues
  03_build_dimensions.py  dedupe into dimension/lookup tables + surrogate keys
  04_build_fact.py      assemble tax_entries with foreign keys
  06_place_authority.py place variant reconciliation -> authority + crosswalk
                        (also fills lat/lon from the geocode cache)
  07_code_authority.py  code-list canonicalisation (adds `canonical` columns)
  09_person_authority.py  fill persons.normalized_name (name variant merging)
  10_place_mentions.py  split multi-toponym cells -> place_mentions table
  08_geocode.py         geocode modern_place via OSM Nominatim (network; optional,
                        cached; NOT in run_all)
  05_load_sqlite.py     apply db/schema.sql, load all CSVs, FK check
  validate.py           reconcile counts/sums, FK + coverage checks, report
  run_all.py            run the whole chain in order (01-04, 06, 07, 05, validate)
```

Every transform is traceable to the source via `source_row`, and validation
reconciles the fact-table row count and `SUM(taxable_selista)` back to the raw
extract on every run.

## Layout

```
excel/          original .xls (source of truth for the transcription)
pipeline/       the ETL steps (stdlib-only; xlrd for the one read step)
data/raw/       verbatim CSV dump of the .xls (+ source_row)
data/interim/   cleaned rows, parse_issues.csv, code_merge_suggestions.csv
data/clean/     one CSV per schema table (the CSV source of truth)
data/manual/    curation inputs: place/code/person_overrides, geocode_cache
db/schema.sql   star-schema DDL, indexes, analysis views
db/tax_lists.sqlite   built database (rebuildable any time)
docs/           data dictionary + methodology/codebook
```

## Rebuild

Requires Python 3 and `xlrd` (`pip install xlrd`). Everything else is stdlib.

```bash
cd pipeline
python run_all.py      # extract → clean → dimensions → fact → authorities → load → validate
```

Any step also runs on its own, e.g. `python 02_clean_split.py`. Editing a file
in `data/manual/` and re-running picks up your curation.

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

-- Institutions aggregated by canonical form (spelling variants merged)
SELECT institution_canonical, COUNT(*) AS n
FROM v_entries_full WHERE institution_canonical <> ''
GROUP BY institution_canonical ORDER BY n DESC LIMIT 20;

-- Groups still needing human confirmation
SELECT * FROM v_places_needing_review;
SELECT code, canonical FROM institution_codes WHERE needs_review = 1;

-- Strict analysis: exclude editorially-inferred (*) rows
SELECT COUNT(*) FROM v_entries_full WHERE inferred = 0;

-- Mapping: taxable selišta per geocoded location in 1517
SELECT place_canonical, place_modern, lat, lon, SUM(taxable_selista) AS selista
FROM v_entries_authority WHERE year = 1517 AND lat IS NOT NULL
GROUP BY authority_id ORDER BY selista DESC;

-- A family's holdings, spelling variants of the name merged
SELECT person_normalized, SUM(taxable_selista) AS selista
FROM v_entries_full WHERE person_normalized = 'Alapy' GROUP BY person_normalized;

-- Toponym-level search: every place cell naming this toponym (alone or grouped)
SELECT DISTINCT p.historical_name
FROM place_mentions m JOIN places p ON p.place_id = m.place_id
WHERE m.toponym LIKE '%Thewkowcz%';
```

## Visualizations

`web/index.html` is a self-contained, web-deployable page with two interactive
views built from the database (see `web/README.md`):

- **Map by year** - taxable *selišta* per place across the 23 campaigns; marker
  area = tax base, shape = county, colour = how confident the location is;
  today's county borders and the Sava/Drava rivers are drawn for context.
  Un-geocoded places are scattered around their county town.
- **Decline over time** - the county tax base collapsing across the century
  (Križevci ~18,000 in 1507 to under 100 by 1596).

Rebuild with `python web/build_web.py`; deploy via the GitHub Pages workflow
(`.github/workflows/pages.yml`) or any static host.

## Curating the merges

Automatic variant merging is high-precision but not infallible, so low-
confidence groups are flagged `needs_review = 1` and are fully editable:

- **Places** → `data/manual/place_overrides.csv`
- **Code lists** → `data/manual/code_overrides.csv`

An override both *merges* items the algorithm kept apart and *splits* items it
wrongly joined, and it always wins. See `data/manual/README.md` for the format
and worked examples, then re-run `python pipeline/run_all.py`.

## Known limitations & next steps

- **Geocoding** - done: `place_authority.lat` / `lon` are filled from
  `modern_place` via OSM Nominatim (`08_geocode.py`). Matches are accepted only
  inside the counties the lists cover (so a same-name place elsewhere in Croatia
  is rejected, not mis-mapped), and several query variants are tried per name.
  517 of 605 authorities with a modern name are located, making **7,136 of
  11,792 entries (60%) mappable** via `v_entries_authority`; all coordinates lie
  within the covered region. The remaining gaps are authorities with no modern
  identification (~1,200) or names Nominatim missed (~46, listed in
  `data/manual/geocode_cache.csv` with an empty `lat` for hand-filling; a few
  are pinned by hand with `source=manual`, e.g. Dolac = hist. Opatovina abbey).
- **Person authority** - done: `persons.normalized_name` merges spelling
  variants of a name (4,252 persons -> 3,565 normalized; 532 names had
  variants), exposed as `person_normalized` in `v_entries_full`. This normalises
  the *name*; disambiguating widows/heirs (compilers' notes 7-8) still needs
  archival research and can't be automated.
- **Multi-toponym cells** - done: `place_mentions` splits cells that name
  several toponyms (compilers' note 5) into one row per toponym (4,620 mentions;
  602 cells named >1), enabling the toponym-level search the compilers' own site
  supports.
- **Judge-name / provincia / abandoned_status variants** - minor (7 / 2 / 3
  groups); the same fold technique would reconcile them if wanted.
- **Un-glossed code terms** - most `institution_codes.english` entries are still
  blank; the book is the authority for filling them.
- **Review backlog** - ~236 place groups and a set of code groups carry
  `needs_review = 1` for optional human confirmation.

Provenance: the `.xls` is the source of truth for the transcription; the
book is the authority for ambiguous coding and was used to verify the data.
