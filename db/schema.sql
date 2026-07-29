-- Star schema for the Kampuš–Adamček Croatian tax lists (15th–16th c.).
-- Fact table: tax_entries. Everything else is a dimension / lookup.
PRAGMA foreign_keys = ON;

DROP VIEW  IF EXISTS v_entries_authority;
DROP VIEW  IF EXISTS v_places_needing_review;
DROP VIEW  IF EXISTS v_entries_full;
DROP VIEW  IF EXISTS v_burden_by_county_year;
DROP TABLE IF EXISTS place_crosswalk;
DROP TABLE IF EXISTS place_authority;
DROP TABLE IF EXISTS tax_entries;
DROP TABLE IF EXISTS places;
DROP TABLE IF EXISTS persons;
DROP TABLE IF EXISTS judicial_districts;
DROP TABLE IF EXISTS census_campaigns;
DROP TABLE IF EXISTS counties;
DROP TABLE IF EXISTS settlement_types;
DROP TABLE IF EXISTS status_codes;
DROP TABLE IF EXISTS title_codes;
DROP TABLE IF EXISTS institution_codes;

-- ---------------------------------------------------------------- dimensions
CREATE TABLE counties (
    county_id       INTEGER PRIMARY KEY,
    name_hr         TEXT NOT NULL,
    comitatus_latin TEXT
);

CREATE TABLE census_campaigns (
    campaign_id INTEGER PRIMARY KEY,
    year        INTEGER,          -- NULL for the one folio-only annotation row
    year_circa  INTEGER,          -- 1 if the year is approximate ("c, 1500")
    year_note   TEXT,             -- original text when more than a bare year
    tax_type    TEXT              -- 'dica' | 'dimnica'
);

CREATE TABLE judicial_districts (
    district_id INTEGER PRIMARY KEY,
    judge_name  TEXT NOT NULL,    -- the processus judicis nobilium, named by its judge
    county_id   INTEGER REFERENCES counties(county_id)
);

CREATE TABLE places (
    place_id         INTEGER PRIMARY KEY,
    historical_name  TEXT NOT NULL,   -- toponym as spelled in the source
    county_id        INTEGER REFERENCES counties(county_id),
    modern_place     TEXT,            -- present-day identification (may be empty)
    modern_uncertain INTEGER,         -- 1 if the identification is marked '?'
    lat              REAL,            -- reserved for a later geocoding phase
    lon              REAL
);

CREATE TABLE persons (
    person_id       INTEGER PRIMARY KEY,
    first_name      TEXT,
    surname         TEXT,
    normalized_name TEXT              -- reserved for name-authority work
);

-- Controlled vocabularies. `code` is the verbatim source spelling (kept for
-- 100% fidelity); `canonical` is a variant-merged representative for analysis
-- and charting (see pipeline/07_code_authority.py). `needs_review` = 1 marks
-- fuzzy-merged groups to confirm via data/manual/code_overrides.csv.
CREATE TABLE settlement_types (code TEXT PRIMARY KEY, latin TEXT, english TEXT);
CREATE TABLE status_codes (
    code TEXT PRIMARY KEY, english TEXT, canonical TEXT, needs_review INTEGER);
CREATE TABLE title_codes (
    code TEXT PRIMARY KEY, english TEXT, canonical TEXT, needs_review INTEGER);
CREATE TABLE institution_codes (
    code TEXT PRIMARY KEY, english TEXT, canonical TEXT, needs_review INTEGER);

-- --------------------------------------------------------------------- fact
CREATE TABLE tax_entries (
    entry_id          INTEGER PRIMARY KEY,
    source_row        INTEGER NOT NULL,   -- 1-based row in the original .xls
    campaign_id       INTEGER REFERENCES census_campaigns(campaign_id),
    county_id         INTEGER REFERENCES counties(county_id),
    district_id       INTEGER REFERENCES judicial_districts(district_id),
    place_id          INTEGER REFERENCES places(place_id),
    person_id         INTEGER REFERENCES persons(person_id),
    settlement_type   TEXT    REFERENCES settlement_types(code),
    provincia         TEXT,               -- fiscal sub-district, when noted
    rate_forint       REAL,               -- tax rate: forints per selište
    rate_denar        REAL,               -- tax rate: denars per selište
    rate_note         TEXT,               -- free-text rate qualifier
    family_status     TEXT    REFERENCES status_codes(code),
    title             TEXT    REFERENCES title_codes(code),
    institution_office TEXT   REFERENCES institution_codes(code),
    other_holders     TEXT,               -- verbatim co-holder free text
    taxable_selista   REAL,               -- taxable hearths/serf-plots (porta/dim)
    taxable_uncertain INTEGER,            -- 1 if the count was marked '(?)'
    abandoned_selista REAL,               -- abandoned/burnt/deserted plots
    abandoned_status  TEXT,               -- deserta / combusta / desolatus ...
    inferred          INTEGER             -- 1 if any source value carried the
                                          -- authors' '*' inferred-data marker
);

-- Place-name authority: groups the many historical spellings of one toponym
-- into a single canonical place (see pipeline/06_place_authority.py).
CREATE TABLE place_authority (
    authority_id   INTEGER PRIMARY KEY,
    canonical_name TEXT NOT NULL,      -- representative historical spelling
    modern_place   TEXT,               -- present-day identification, if known
    county_id      INTEGER REFERENCES counties(county_id),
    n_variants     INTEGER,            -- distinct raw place rows in this group
    n_entries      INTEGER,            -- tax entries falling under this place
    method         TEXT,               -- how the group was formed
    needs_review   INTEGER             -- 1 = fuzzy/conflicting, confirm by hand
);

CREATE TABLE place_crosswalk (
    place_id        INTEGER PRIMARY KEY REFERENCES places(place_id),
    historical_name TEXT,
    county_id       INTEGER REFERENCES counties(county_id),
    authority_id    INTEGER REFERENCES place_authority(authority_id),
    method          TEXT,
    needs_review    INTEGER
);
CREATE INDEX ix_crosswalk_authority ON place_crosswalk(authority_id);

CREATE INDEX ix_entries_campaign ON tax_entries(campaign_id);
CREATE INDEX ix_entries_county   ON tax_entries(county_id);
CREATE INDEX ix_entries_place    ON tax_entries(place_id);
CREATE INDEX ix_entries_person   ON tax_entries(person_id);
CREATE INDEX ix_campaigns_year   ON census_campaigns(year);

-- --------------------------------------------------------------------- views
-- Fully denormalised entries, convenient for export and charting.
CREATE VIEW v_entries_full AS
SELECT e.entry_id, e.source_row,
       c.year, c.year_circa, c.tax_type,
       co.name_hr AS county, co.comitatus_latin,
       e.provincia, d.judge_name,
       p.historical_name AS place, e.settlement_type,
       p.modern_place, p.modern_uncertain,
       pe.first_name, pe.surname,
       e.family_status,      sc.canonical AS family_status_canonical,
       e.title,              tc.canonical AS title_canonical,
       e.institution_office, ic.canonical AS institution_canonical,
       e.rate_forint, e.rate_denar,
       e.taxable_selista, e.taxable_uncertain,
       e.abandoned_selista, e.abandoned_status, e.inferred
FROM tax_entries e
LEFT JOIN census_campaigns  c  ON c.campaign_id = e.campaign_id
LEFT JOIN counties          co ON co.county_id  = e.county_id
LEFT JOIN judicial_districts d ON d.district_id = e.district_id
LEFT JOIN places            p  ON p.place_id    = e.place_id
LEFT JOIN persons           pe ON pe.person_id  = e.person_id
LEFT JOIN status_codes      sc ON sc.code       = e.family_status
LEFT JOIN title_codes       tc ON tc.code       = e.title
LEFT JOIN institution_codes ic ON ic.code       = e.institution_office;

-- Tax burden aggregated by county, year and tax type.
CREATE VIEW v_burden_by_county_year AS
SELECT co.name_hr AS county, c.year, c.tax_type,
       COUNT(*)                       AS n_entries,
       SUM(e.taxable_selista)         AS taxable_selista,
       SUM(e.abandoned_selista)       AS abandoned_selista
FROM tax_entries e
JOIN census_campaigns c ON c.campaign_id = e.campaign_id
LEFT JOIN counties   co ON co.county_id  = e.county_id
WHERE c.year IS NOT NULL
GROUP BY co.name_hr, c.year, c.tax_type;

-- Entries with the canonical (variant-merged) place resolved, so the same
-- toponym aggregates across census years despite spelling drift.
CREATE VIEW v_entries_authority AS
SELECT e.entry_id, e.source_row,
       c.year, c.tax_type, co.name_hr AS county,
       pa.authority_id,
       pa.canonical_name AS place_canonical,
       pa.modern_place   AS place_modern,
       p.historical_name AS place_historical,
       e.settlement_type,
       e.taxable_selista, e.abandoned_selista
FROM tax_entries e
LEFT JOIN places           p  ON p.place_id      = e.place_id
LEFT JOIN place_crosswalk  x  ON x.place_id      = e.place_id
LEFT JOIN place_authority  pa ON pa.authority_id = x.authority_id
LEFT JOIN census_campaigns c  ON c.campaign_id   = e.campaign_id
LEFT JOIN counties         co ON co.county_id    = e.county_id;

-- Authority groups still awaiting human confirmation (fuzzy merges or clusters
-- with conflicting modern identifications). Curate these via the override file.
CREATE VIEW v_places_needing_review AS
SELECT pa.authority_id, pa.canonical_name, pa.modern_place, pa.method,
       pa.n_variants, pa.n_entries,
       GROUP_CONCAT(x.historical_name, ' | ') AS spellings
FROM place_authority pa
JOIN place_crosswalk x ON x.authority_id = pa.authority_id
WHERE pa.needs_review = 1
GROUP BY pa.authority_id
ORDER BY pa.n_entries DESC;
