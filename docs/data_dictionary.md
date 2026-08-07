# Data dictionary — Kampuš–Adamček tax lists

Source: Ivan Kampuš & Josip Adamček, *Popisi i obračuni poreza u Hrvatskoj u
XV. i XVI. stoljeću* (tax censuses and accounts in Croatia, 15th–16th c.). The
Excel transcription is `excel/tax-lists-kampuš-adamček.xls` (one sheet, 11,814
rows including the header; 11,792 data rows after blank rows are dropped).

Each source row is **one taxpayer's holding in one place in one census
campaign**, with the number of taxable and abandoned *selišta* (serf-plots /
hearths; Lat. *porta*, *fumus*). Two tax types appear: **dica** (a per-*selište*
land tax) and **dimnica** (a hearth tax).

See `docs/methodology.md` for the compilers' own codebook and the recording
irregularities behind several fields (the `*` inferred marker, multi-toponym
cells, "other holders", widow/orphan identification, etc.).

## Source column → target mapping

| Source column (Croatian) | Target field(s) | Notes |
|---|---|---|
| GODINA UBIRANJA POREZA | `census_campaigns.year`, `year_circa`, `year_note` | first 1400–1700 year extracted; `c, 1500` → year 1500 + circa flag; folio-missing annotations kept in `year_note` |
| VRSTA I IZNOS POREZA | `census_campaigns.tax_type`; `tax_entries.rate_forint`, `rate_denar`, `rate_note` | split on `-`; amounts parsed from `N forint(a)` / `N denara`; residual prose → `rate_note` |
| ŽUPANIJA (COMITATUS) | `counties.name_hr`, `comitatus_latin`; `tax_entries.provincia` | Latin gloss taken from `(...)`; subdivision after `)` (mixed `-` `/` separators) → `provincia` |
| KOTAR PLEMIĆKOG SUCA | `judicial_districts.judge_name` | the *processus judicis nobilium*, named by its noble judge |
| MJESTO | `places.historical_name`; `tax_entries.settlement_type` | known suffix (`-castrum`, `-oppidum`, `-praedium`, …) split into `settlement_type` |
| MJESTO DANAS | `places.modern_place`, `modern_uncertain` | embedded `?` → `modern_uncertain = 1`; consolidated per toponym |
| IME PRVOG … POSJEDNIKA | `persons.first_name` | |
| PREZIME … | `persons.surname`, `normalized_name` | orthographic variants preserved; `normalized_name` reserved for authority work |
| OBITELJSKI STATUS … | `tax_entries.family_status` → `status_codes` | e.g. Relicta, Heredes, Orphani |
| PRVI POSJEDNIK: INSTITUCIJA, SLUŽBA | `tax_entries.institution_office` → `institution_codes` | free text; common terms glossed |
| OSTALI UPISANI POSJEDNICI … | `tax_entries.other_holders` | kept verbatim |
| BROJ OPOREZIVIH SELIŠTA | `tax_entries.taxable_selista`, `taxable_uncertain` | `8(?)` → value 8 + uncertain flag |
| BROJ NAPUŠTENIH … SELIŠTA | `tax_entries.abandoned_selista`, `abandoned_status` | number and status word (`deserta`, `combusta`, `desolatus …`) separated |
| TITULA … | `tax_entries.title` → `title_codes` | e.g. Dominus, Domina, Dux |
| (15th column) | — | empty in source; dropped |

## Tables

**Fact — `tax_entries`** (grain: one source row; keeps `source_row` for
traceability): `entry_id`, `source_row`, `campaign_id`, `county_id`,
`district_id`, `place_id`, `person_id`, `settlement_type`, `provincia`,
`rate_forint`, `rate_denar`, `rate_note`, `family_status`, `title`,
`institution_office`, `other_holders`, `taxable_selista`, `taxable_uncertain`,
`abandoned_selista`, `abandoned_status`, `inferred`.

`inferred = 1` marks a row where any source value carried the compilers' `*`
marker (an editorially inferred value; see `docs/methodology.md`). The `*` is
also kept verbatim in the field itself. Filter with `WHERE inferred = 0` for
only explicitly-attested rows.

**Dimensions / lookups**

| Table | Grain | Key columns |
|---|---|---|
| `census_campaigns` | year × tax_type (× note) | `year`, `year_circa`, `year_note`, `tax_type` |
| `counties` | county | `name_hr`, `comitatus_latin` |
| `judicial_districts` | judge within a county | `judge_name`, `county_id` |
| `places` | toponym within a county | `historical_name`, `county_id`, `modern_place`, `modern_uncertain` |
| `persons` | first name + surname | `first_name`, `surname`, `normalized_name` |
| `settlement_types` | code list | `code`, `latin`, `english` |
| `status_codes` | code list | `code`, `english`, `canonical`, `needs_review` |
| `title_codes` | code list | `code`, `english`, `canonical`, `needs_review` |
| `institution_codes` | code list | `code`, `english`, `canonical`, `needs_review` |
| `place_authority` | canonical place (variant-merged) | `authority_id`, `canonical_name`, `modern_place`, `county_id`, `n_variants`, `n_entries`, `method`, `needs_review`, `lat`, `lon`, `hide_from_map` |
| `place_crosswalk` | raw place → authority | `place_id`, `authority_id`, `method`, `needs_review` |
| `place_mentions` | one toponym named in a place cell | `mention_id`, `place_id`, `toponym`, `source_fragment` |

**Views**: `v_entries_full` (denormalised entries for export/charting);
`v_burden_by_county_year` (taxable & abandoned selišta by county × year ×
type); `v_entries_authority` (entries with the canonical variant-merged place,
so one toponym aggregates across census years); `v_places_needing_review`
(low-confidence authority groups awaiting human confirmation).

## Place-name authority (variant reconciliation)

`pipeline/06_place_authority.py` groups the 3,866 raw `places` rows (many of
which are spelling variants of the same toponym across census years) into
~1,800 canonical **authorities**. Grouping evidence, strongest first:

1. **manual override** — `data/manual/place_overrides.csv`, always wins;
2. **identical orthographic fold key** within a county (high confidence) — a
   normalisation that collapses early-modern Latin/Slavic spelling variation
   (cz→c, w→v, y→i, th→t, doubled letters, …);
3. **shared modern identification** within a county (high confidence);
4. **fuzzy fold-key similarity** within a county (flagged `needs_review = 1`).

A guard prevents fuzzy-merging two places with **conflicting** non-empty
`modern_place` values (they are different places — e.g. Sisak vs Susedgrad),
so cross-identifications don't chain together. `method` records how each group
formed; `needs_review = 1` marks fuzzy or conflicting groups to curate via the
override file (see `data/manual/README.md`). Example: `Zalathnok`, `Zlathnok`
and `Zalathnak` now share one authority, so the town's selišta form a single
series across 1507/1513/1517.

### Geocoding

`place_authority.lat` / `lon` hold coordinates geocoded from `modern_place`
(via OpenStreetMap Nominatim). A match is accepted only if its modern županija
is one the tax lists cover (`ALLOWED_COUNTIES` in `08_geocode.py`: Grad Zagreb,
Zagrebačka, Krapinsko-zagorska, Sisačko-moslavačka, Karlovačka, Varaždinska,
Koprivničko-križevačka, Bjelovarsko-bilogorska, Virovitičko-podravska), which
rejects same-name places elsewhere in Croatia. Several query variants are tried
per name to recover compound (`LEKENIK. LUKAVEC`), abbreviated (`SV. ĐURĐ`) and
parenthetical forms. Because coordinates are a property of the modern
identification, they live on the deduplicated authority, not on each raw
spelling — `places` no longer carries `lat`/`lon`. The `v_entries_authority`
view exposes `lat`/`lon` per entry for mapping. Run `pipeline/08_geocode.py`
(a network step, not part of `run_all`) to build/refresh the cache
`data/manual/geocode_cache.csv`; `06_place_authority.py` then reads that cache.
The cache is hand-editable — set a row's `source` to `manual` to pin a
correction, or add a row for a name Nominatim missed.

### Non-settlement rows (`hide_from_map`)

A few `place_authority` rows are not settlements at all but **fiscal
estate-lumps** the scribe entered as a heading. These read `Bona-<noble>`,
where *bona* is Latin for "estates / goods" — e.g. the register elsewhere
spells it out as *bona egregii Johannes Alapi* ("the estates of the honourable
John Alapić") or *bona non soluta in eodem processu* ("estates whose tax went
unpaid in this district"). The compilers left such lines' modern-name column
blank because there is no single locus to identify: the sum covers a magnate's
scattered holdings across a whole district. The four in the data
(`Bona-Hampo`, `Bona-Johannes Alapi`, `Bona-Nicolaus Zrini`, `Bona-Zlwny`, all
1533) carry a lump `taxable_selista` but no per-village breakdown.

`06_place_authority.py` sets `hide_from_map = 1` on any authority whose
`canonical_name` begins `Bona-`, and `web/build_web.py` filters these out of the
map (`WHERE COALESCE(pa.hide_from_map, 0) = 0`) — they can never be pinned to a
point. The rows are **kept in the DB** (and remain browsable in the explorer)
for completeness; only the map excludes them. The rule is prefix-driven, so any
future `Bona-*` line is hidden automatically; extend the condition in `06` if
other fiscal headings (bare `processus …`, `… relaxata in eodem processu`) should
be hidden too.

## Code-list canonicalisation (variant reconciliation for controlled vocab)

The same "keep raw, add canonical" idea applies to the controlled vocabularies.
`status_codes`, `title_codes` and `institution_codes` keep the verbatim source
spelling in `code` (100% faithful) and add a `canonical` column that merges
equivalent spellings for analysis/charting, built by
`pipeline/07_code_authority.py`:

1. **manual override** — `data/manual/code_overrides.csv`, always wins;
2. **identical fold key** — drops `*`, `(?)`, case, punctuation and orthographic
   variation (so `Episcopus Zagrabiensis)*` = `Episcopus Zagrabiensis)`);
3. **fuzzy fold similarity** — catches typos (`Strigoninesis` ≈ `strigoniensis`,
   `Wereucze` ≈ `Werewcze`), flagged `needs_review = 1`.

The canonical for a group is a real attested member (cleanest, then most-used).
Truncations that fold differently (e.g. `Nobiles campi` vs
`Nobiles campi Zagrabiensis`) are **not** auto-merged; they are listed in
`data/interim/code_merge_suggestions.csv` and confirmed via the override file.
Use the canonical columns through `v_entries_full`
(`institution_canonical`, `title_canonical`, `family_status_canonical`).

`settlement_types` needs no canonical column — it was already normalised in
step 2.

## Conventions & known limitations

- Encoding is UTF-8 throughout; whitespace is collapsed and NFC-normalised.
- Boolean-ish flags (`year_circa`, `modern_uncertain`, `taxable_uncertain`)
  use `1` / empty (NULL in SQLite).
- **Numbers**: `selišta` and rates are stored as REAL (halves like `0.5` occur).
- **Place orthography** *is* reconciled via `place_authority` /
  `place_crosswalk` (see above) — group by `authority_id` or
  `place_canonical` to aggregate a toponym across its spelling variants.
- **Person orthography** *is* reconciled via `persons.normalized_name`
  (`09_person_authority.py`, exact-fold of the full name + optional
  `data/manual/person_overrides.csv`); group by `person_normalized` in
  `v_entries_full`. This normalises the *name*, not the *person* — true
  disambiguation of widows/heirs (notes 7-8) needs archival research.
- **Multi-toponym cells**: `place_mentions` splits a `place_historical` that
  names several toponyms (note 5) into one row per toponym, so a name is
  searchable whether recorded alone or grouped (`SELECT place_id FROM
  place_mentions WHERE toponym LIKE …`). `source_fragment` keeps the raw piece.
- **Geocoding deferred**: `places.lat` / `lon` are present but null; ~1,844
  places lack a modern identification (see `validate.py` report).
- **Inferred values**: the compilers' `*` marker (an editorially inferred
  value, per `docs/methodology.md`) is kept verbatim and surfaced as
  `tax_entries.inferred`.
- **Year anomalies**: all 23 census years the compilers list as processed are
  present; two extra single-row years (`1578`, `1675`) are not in that list and
  are flagged by `validate.py` as likely typos (kept verbatim).
- **Parse issues** (currently 1: a folio-only annotation with no year) are
  logged to `data/interim/parse_issues.csv` — never silently dropped.
- County glosses fixed one malformed source value (`Zagrebčka` → Zagreb);
  see `COUNTY_ALIASES` in `pipeline/02_clean_split.py`.
