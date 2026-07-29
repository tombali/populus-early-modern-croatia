# Source methodology & codebook (from the compilers)

This is the compilers' own account of how the tax-list database was made and
what its columns mean, with notes on how each point maps to this repo. The
originals are 16th-century pre-statistical fiscal records, so the data has
irregularities that no automated process can fully resolve — treat it as a
faithful transcription with documented caveats, not a clean statistical series.

## How holdings were recorded (and the irregularities this causes)

The 16th-century method was to list a place name and a holder's name side by
side. Being a pre-statistical period, practice varied, which caused most of the
database's hard cases:

1. **Only the holder is listed, with no place.**
2. **Only the place is listed, with no holder.**
3. **A place and holder are listed, then further holder names follow** without
   an *ibidem* (or similar) tying them to that place. These following holders
   were generally **assumed to belong to the named place**.
4. **One holder is usually tied to a number of selišta in a place**, but often
   two or more people hold a group of selišta together without saying how many
   belong to each. → handled by a **separate column for all holders after the
   first** (`other_holders` here).
5. **Two or more places are sometimes listed against the same holder and the
   same selišta count.** All such places are kept in one cell (as in the
   source); the search must consider every case where a toponym appears,
   whether alone or in a group. → in this repo the raw cell is kept in
   `place_historical`; see the *known limitation* below.
6. **Often only a first name is given, sometimes only a surname.** Where the
   source made it clear the people belong to the same family, a name was tied
   to the surname mentioned just before, **marked with an asterisk `*`**.
7. **Widows appear as holders.** No identification problem when the late
   husband is named by surname; a problem when only his first name is given.
   Unresolved without archival research per person.
8. **Sons / daughters / orphans as holders** may carry the family surname, or
   only the father's name, or nothing — an identification problem requiring
   case-by-case research.
9. Because these are proto-statistical sources that cannot be processed
   systematically, **expect possible deviations from the real situation.**
10. The original Adamček–Kampuš edition also contains shorter lists of persons
    and institutions **exempt** from tax, and lists of **debtors**. These are
    more narrative and are **not yet processed** (see the "subset of the book"
    note in the README).
11. **Wherever the lists don't state a value but a solution could be inferred
    with high probability, that value is given and marked with an asterisk
    `*`.**

### The asterisk `*` — inferred data

Per notes 6 and 11, `*` is the compilers' marker for **an editorially inferred
value**, not a defect. This repo keeps the `*` verbatim in the field **and**
sets a row-level `tax_entries.inferred = 1` flag (254 rows) so inferred data can
be filtered or excluded from strict analyses. Example: `WHERE inferred = 0` for
only explicitly-attested rows.

## Variables (columns) and clarifications

| Src | Column | Notes from the compilers |
|---|---|---|
| A | GODINA UBIRANJA POREZA | year the tax was collected |
| B | VRSTA I IZNOS POREZA | type and amount of tax |
| C | ŽUPANIJA (COMITATUS) | county |
| D | KOTAR PLEMIĆKOG SUCA (PROCESSUS JUDICIS NOBILIUM) | noble judge's district |
| E | MJESTO | place |
| F | MJESTO DANAS | present-day place — **subject to additions and change** |
| G | IME PRVOG UPISANOG POSJEDNIKA | first name of the first holder |
| H | PREZIME PRVOG UPISANOG POSJEDNIKA | surname of the first holder on the parcel |
| I | OBITELJSKI STATUS… | family status of the first holder (e.g. widow, son, daughter, orphan) |
| J | PRVI POSJEDNIK: FIZIČKA OSOBA, SLUŽBA | Often the holder is not a named physical person but a **legal person** (parish priest, monastery, diocese, chapter), or is identified only by **title/status/office** (king, *predijalac*, prebendary, ban, bishop…). Where a holder has a name *and* an office, the office of the first holder goes here so that **alphabetical sorting classifies institutions and offices as holders**. |
| K | OSTALI UPISANI POSJEDNICI… | other holders (physical & legal persons) on the parcel, with status/office/title |
| L | BROJ OPOREZIVIH SELIŠTA (PORTA, DIM) | number of taxable selišta (porta / hearth) |
| M | BROJ NAPUŠTENIH… SELIŠTA | number of abandoned / burnt / destroyed selišta, if recorded |
| N | TITULA PRVOG UPISANOG POSJEDNIKA | title of the first holder |

(In this repo column J is stored as `institution_office`; see
`docs/data_dictionary.md` for the full source → schema mapping.)

## Processed census years (authoritative)

1495, 1500, 1507, 1509, 1512, 1513, 1517, 1520, 1533, 1543, 1546, 1553, 1554,
1566, 1567, 1568, 1570, 1573, 1574, 1576, 1579, 1582, 1596 — **23 campaigns**.

All 23 are present in the data. Two extra year values appear (`1578` and `1675`,
one row each) that are **not** in this list; `pipeline/validate.py` flags them as
likely transcription typos. They are kept verbatim for fidelity.

## Planned continuation (per the compilers)

The web data is to be periodically extended with further published and
unpublished sources of similar provenance: two 17th-century muster rolls, the
**1598 tax census**, and 16th-century tax lists for **Međimurje**. Accompanying
**maps** are being built to reconstruct, year by year, the geographic position of
the places and the number/density of their selišta, intended to be generated
from the database on user-defined criteria. (Toponym reconstruction draws on
resources of the Institute for the Croatian Language and Linguistics.)

## Known limitation carried into this repo

Per point 5, a single `place_historical` cell can contain **several toponyms**
(e.g. `Zelina, Bwkowcz`, or `Zomzedwara-castrum / Judicati Ztenyowcz, Ztopnyk,
Nowak…`). The place authority (`06_place_authority.py`) groups spelling variants
but does **not** split a multi-toponym cell into separate searchable places, so
a per-toponym search — which the compilers' own web system supports — is not yet
reproduced here. Splitting these into a place-mention table is a candidate next
step.
