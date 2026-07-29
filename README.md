# Populus - Early-Modern Croatia tax lists

Structured, analysis-ready version of the tax censuses published in Ivan Kampuš
& Josip Adamček, *Popisi i obračuni poreza u Hrvatskoj u XV. i XVI. stoljeću*
(tax censuses and accounts of Croatia, 15th-16th c.).

The source is a single flat Excel sheet transcribed from the book. It is
faithful to the originals but hard to compute on: several columns pack multiple
facts into one cell, values are untyped and inconsistently spelled, the
geographic hierarchy repeats on every row, and there are no stable identifiers.
This repo turns it into a clean, typed, normalised **star schema** - a
`tax_entries` fact table plus dimension/lookup tables - delivered as UTF-8 CSVs
(the source of truth) and a built **SQLite** database, produced by a
reproducible, **pure-Python** pipeline. Nothing from the source is discarded:
every cleaned row keeps its original Excel row number, and raw spellings are
preserved alongside the merged/canonical forms used for analysis.

**Coverage:** ~29 census campaigns, **1495-1596** · **11,792 entries** · 4
counties · ~3,900 raw places (≈1,800 after variant merging) · ~4,250 taxpayers ·
tax types *dica* (land tax) and *dimnica* (hearth tax). Each entry records a
holder's parcel/estate in a place in one campaign, with counts of taxable and
abandoned *selišta* (serf-plots / hearths; Lat. *porta*, *fumus*).

---

## What the data looked like, and what was wrong with it

The original sheet is **11,814 rows × 15 columns** (the 15th column is empty),
one row per taxpayer holding. The columns, in Croatian, were:

`GODINA UBIRANJA POREZA` · `VRSTA I IZNOS POREZA` · `ŽUPANIJA (COMITATUS)` ·
`KOTAR PLEMIĆKOG SUCA` · `MJESTO` · `MJESTO DANAS` · `IME…` · `PREZIME…` ·
`OBITELJSKI STATUS…` · `PRVI POSJEDNIK: INSTITUCIJA, SLUŽBA` · `OSTALI
POSJEDNICI…` · `BROJ OPOREZIVIH SELIŠTA` · `BROJ NAPUŠTENIH… SELIŠTA` ·
`TITULA…`

Profiling every column surfaced the following problems.

### 1. Overloaded cells - several facts crammed into one column
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

### 2. Dirty, untyped values
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

### 3. Text-encoding damage
Croatian diacritics (č/ć/ž/š/đ) were mangled in intermediate tooling. The whole
pipeline reads and writes **UTF-8** end to end, so `Križevačka županija`,
`Zagrebačka`, etc. round-trip correctly.

### 4. Heavy denormalisation & no identifiers
County, Latin gloss, judicial-district (named by its noble judge), and campaign
metadata were repeated on all 11k rows, and there were **no stable IDs** to join
or link on.

**Solved** in `03_build_dimensions.py` / `04_build_fact.py`: the data is
normalised into a **star schema** with surrogate keys - a `tax_entries` fact
table referencing dimension tables (`census_campaigns`, `counties`,
`judicial_districts`, `places`, `persons`) and controlled-vocabulary code lists
(`settlement_types`, `status_codes`, `title_codes`, `institution_codes`).

### 5. Place-name spelling variants across census years
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

### 6. Controlled-vocabulary spelling variants
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

### 7. Environment constraint
`pandas` cannot be used on the original machine - its compiled DLL is blocked
by an Application Control policy. The entire pipeline is therefore **stdlib-only**
(`csv`, `sqlite3`, `re`, `difflib`, `unicodedata`) plus **`xlrd`** for the one
`.xls` read. This is a feature, not just a workaround: the output is trivially
portable and has almost no dependencies.

---

## Scope note: the Excel is a *subset* of the book

The Excel transcribes the book's **summary dica/dimnica assessment tables**
only. The book *also* contains detailed **household/nominal conscriptions** -
peasant-by-peasant rolls grouped by *Judicatus* / *Portio* with
`Domus`/`Coloni`/`Inquilini` subtotals (e.g. printed pp. ~372-423). Those are
**not** in the Excel and not in this dataset. If that finer-grained data is
needed, it must be transcribed separately from the PDF.

---

## Verification against the book

The structured data was spot-checked against random pages of the scanned book
(rendered from the PDF). Transcription fidelity is **excellent**:

- **1574, doc. #91, Zamobor** (*Processus Blasii Pogledych*): all 6 entries
  matched exactly - place, holder, taxable *fumi*, and the split-out
  *"Desertati fumi 3/2"* abandoned counts.
- **1517, Slavonia list**: `Monozlo 253`, `Zylagh…Palatinus 0`, `Valpo 400`,
  `Walpho 350`, `Zwhamlaka 56`, `Rahowcza provincia 216`, `Bakowcza relicte
  47/desolati 2` - all matched, including abandoned-status parsing.
- The only apparent "miss" was a **search** using the wrong spelling: the 1517
  Zalathnok town is transcribed `Zlathnok` - present and correct, and exactly
  the kind of variant the place authority now reconciles.

---

## The resulting schema

**Fact table - `tax_entries`** (grain: one source row; keeps `source_row`):
campaign/county/district/place/person foreign keys, `settlement_type`,
`provincia`, `rate_forint`/`rate_denar`/`rate_note`, `family_status`, `title`,
`institution_office`, `other_holders`, `taxable_selista` (+`taxable_uncertain`),
`abandoned_selista` (+`abandoned_status`).

**Dimensions / lookups:** `census_campaigns`, `counties`, `judicial_districts`,
`places`, `persons`, `settlement_types`, `status_codes`, `title_codes`,
`institution_codes`, plus the variant-reconciliation tables `place_authority`
and `place_crosswalk`.

**Views:**
- `v_entries_full` - fully denormalised entries (raw values **and** the
  `*_canonical` code columns) for export/charting;
- `v_entries_authority` - entries with the variant-merged canonical place;
- `v_burden_by_county_year` - taxable & abandoned selišta by county × year × type;
- `v_places_needing_review` - low-confidence place groups awaiting confirmation.

See `docs/data_dictionary.md` for the full column-by-column mapping and code
lists.

---

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
  07_code_authority.py  code-list canonicalisation (adds `canonical` columns)
  05_load_sqlite.py     apply db/schema.sql, load all CSVs, FK check
  validate.py           reconcile counts/sums, FK + coverage checks, report
  run_all.py            run the whole chain in order
```

Every transform is traceable to the source via `source_row`, and validation
reconciles the fact-table row count and `SUM(taxable_selista)` back to the raw
extract on every run.

## Layout

```
excel/          original .xls (source of truth for the transcription)
pdf/            the scanned book (authority for ambiguous coding; gitignored)
pipeline/       the ETL steps (stdlib-only; xlrd for the one read step)
data/raw/       verbatim CSV dump of the .xls (+ source_row)
data/interim/   cleaned rows, parse_issues.csv, code_merge_suggestions.csv
data/clean/     one CSV per schema table (the CSV source of truth)
data/manual/    human curation inputs (place_overrides.csv, code_overrides.csv)
db/schema.sql   star-schema DDL, indexes, analysis views
db/tax_lists.sqlite   built database (gitignored; rebuild any time)
docs/           data dictionary
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
```

## Curating the merges

Automatic variant merging is high-precision but not infallible, so low-
confidence groups are flagged `needs_review = 1` and are fully editable:

- **Places** → `data/manual/place_overrides.csv`
- **Code lists** → `data/manual/code_overrides.csv`

An override both *merges* items the algorithm kept apart and *splits* items it
wrongly joined, and it always wins. See `data/manual/README.md` for the format
and worked examples, then re-run `python pipeline/run_all.py`.

## Known limitations & next steps

- **Geocoding** - `places.lat` / `lon` exist but are null; ~1,844 places lack a
  modern identification. `place_authority.modern_place` deduplicates the target
  list to ~1,800 places to geocode for mapping.
- **Person authority** - still open: ~531 groups of the same person spelled
  differently. The place/code technique applies directly and would populate the
  reserved `persons.normalized_name`.
- **Judge-name / provincia / abandoned_status variants** - minor (7 / 2 / 3
  groups); the same fold technique would reconcile them if wanted.
- **Un-glossed code terms** - most `institution_codes.english` entries are still
  blank; the book is the authority for filling them.
- **Review backlog** - ~236 place groups and a set of code groups carry
  `needs_review = 1` for optional human confirmation.

Provenance: the `.xls` is the source of truth for the transcription; the scanned
book is the authority for ambiguous coding and was used to verify the data.
