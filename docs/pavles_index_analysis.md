# Pavleš, *Podravina u srednjem vijeku* — index analysis for census-unknown resolution

Analysis of the book's full place/person index (*Abecedarij mjesnih i osobnih imena /
Index locorum et personarum*, pp. 252–270) against our unresolved census places (the 323
red authorities, `lat IS NULL`). Goal: identify which pages to obtain so Pavleš's
treatment can locate our unknowns. Compiled 2026-08.

**Index conventions** (stated p. 252): regular type = toponyms; *italic* = persons/families;
**bold** page numbers = where the object is treated most fully.

## Scope

Pavleš covers the **Đurđevec–Koprivnica–Virje–Ludbreg Podravina** → matches our
**county-1 (north) and county-3** reds. County-2 (Varaždin) and county-4 (Zagreb) reds,
and the small `-owcz` hamlets around Čazma/Garešnica/Moslavina, are largely out of his
area. The book's toponym-by-toponym gazetteer sits ~**pp. 137–210**, where most bold
treatments fall.

## Handled without pages: two duplicate reds merged

Alternate spellings of already-resolved places (merged via `place_overrides.csv`):

- `Dymychffeld` (34 sel, c1) → **Dimičkovina** (Gymelchfeld authority)
- `Nezethyno` (24 sel, c1) → **Nešetino** (Nesethyno authority)

## Tier 1 — confident matches with dedicated treatment

| Red (census) | Sel. | Pavleš entry | Pages (**bold** = main) |
|---|---|---|---|
| Brezewcze cum pert. | 354 | Berzenze (Breznica/Brezovica); Brezovica (đurđ. vlast.) | **161–162**, **186**, **191–192**, 197, 199 |
| Zeredyscha ad Zenth Gergwara | 38 | Sredice ili Središče (Zerdahel); Zenthgerghwara→"vidi Sredice" | **160–161**, 141, 157, 162, 203 |
| Wolywercz / Wolywercz-Kothenyak | 10+5 | Oliverec (= "i **Walywercz**"; index cross-refs Walywercz→Oliverec) | **156–157**, 143, 214, 229 |
| Petrowcz (c3) | 26 | Petrovec | **122**, 133 |
| Oresya (c3) *(also a Wamhyda appurtenance)* | 23 | Orešje | 109, 199 |
| Zuhamlacha | 21 | Suha Mlaka / Zuha Mlaka | 90, 106 |
| Leschan | 13 | Lešćan | 175 |
| Bedenye | 8 | Bedenye | 38 (+ Bednja vlast. 34–46) |
| Gedrocz / Gedrowcz | 6 | Gedrovec | **220** |

## Tier 2 — probable, worth a look

| Red | Sel. | Pavleš candidate | Pages |
|---|---|---|---|
| Dobrachwcha cum pert. | 90 | Dobra kuća | 194 |
| Dobrowych (Dobrowyncz) | 92 | Dobrouch | 212–213 |
| Nagh Thopalocz / Thopolyancz | 9+2 | Topolovec | 79, 188, 193 |
| Filyphfalwa / Philipfalwa | 14 | Filipovec (Filip-falva) | **217**, 215, 219 |
| Bellyanowcz / Belyowcz | 41.5 | Belanovo selo | 81 |
| Laskaeghaz (László-egyház) | 5 | Sv. Ladislav (crkva Sv. Ladislava) | **204–205** |

## Tier 3 — lordship/context chapters for the Vlach *waywodatus* reds

c3 Vlach settlements (no individual index lines; treated in the đurđevečko-vlastelinstvo
narrative): `Wlachin`, `Rawennyk`, `Wogrynincz`, `Kozachyna-waywodatus`, `Kerhennyna`,
`Zkakala`, `Kwthetincz`, `Krayowcz`, `Zehanowcz`, `Powsyncz`. Useful spread:
**68–69, 74, 174, 176, 195, 201** (Đurđevec) and the gazetteer run **137–165**.

## High-value reds NOT locatable from the index (open questions)

Large, likely-Podravina, but no clean index match:

- `Fyerky` — 260 sel, c1 (not Virje, whose old name was Prodavić)
- `Zthara` — 178 sel, c1 (a *nova/stara* split?)
- `Zwpya` — 131 sel, c1
- `Waswarowcz` — 74 sel, c1 (Vasvár / "Vašarovec"?)
- `Kozachyna` — 69 sel, c1

## Resolved from the high-yield scans (applied)

From pp. 38, 90, 106–109, 122, 156–162, 175, 186, 191 (all as approximate `needs_review`
= yellow pins; most are *nestala sela* / lost sites Pavleš locates only relative to a town):

| Red | → Modern / area | Pavleš | Anchor |
|---|---|---|---|
| Wolywercz + Wolywercz-Kothenyak (merged) | **Oliverec** (Olywercz/Walywercz) — đurđevečko, nr Virje/Novigrad P. | 156–157 | 46.082, 16.982 |
| Zeredyscha ad Zenth Gergwara | **Sredice/Središče (Zerdahel)** — đurđevečko, nr Novigrad P. | 160–161 | 46.085, 16.97 |
| Bozyas | **Bezje Veliko i Malo** (Nogbozyo/Kysbozyo) — nr Novigrad P. | 161–162 | 46.093, 16.96 |
| Oresya (c3) | **Orešje** — NW of Koprivnica, nr Subotica | 109 | 46.190, 16.741 |
| Janenowcz | **Janovec/Janenovec** — lost, NW of Koprivnica | 109 | 46.183, 16.748 |
| Cheztylowcz + Chesthylowcz (merged) | **Čestilovec** — lost, NW of Koprivnica | 109 | 46.178, 16.76 |
| Zuhamlacha | **Zuha Mlaka** — Globoki/Botinovec/Dolanec zone N of Koprivnica | 106 | 46.201, 16.765 |

Result: reds 321 → **312**, yellow 630 → **637**. Validation passing.

**Not resolved from these scans (county mismatch / needs more):** Petrovec + Kaznetina
(p.122 — that Petrovec is by Vinica, c2; our Petrowcz is c3), Bedenye (p.38 — near Bednja,
inconclusive), and the big **Brezewcze cum pertinentiis** (354 sel): the p.191 Brezovica is
a *small* đurđevečko site, not a 354-selišta estate — Brezewcze is more likely the Vaška
Brezovica (Adamček), still to be decided.

## Resolved from the "middle" scans (pp. 79–83, 188–214, applied)

This batch was four blocks: **Rasinja lordship** (79–83), the **đurđevečko-vlastelinstvo
gazetteer** (188–201), the **Sveti Ladislav / Sveti Mihalj / bishop's Podravina estates**
(202–210), and **small Komarnica-district estates** (211–214). All new pins are
approximate `needs_review` = yellow.

| Red (census) | Sel.* | → Modern / area | Pavleš | Anchor |
|---|---|---|---|---|
| Dobrowych (Dobrowoych/Dobrowyncz/Dobryncz) | 92 | **Dobrouch** — nestalo selo between Koprivnica and Koprivnički Bregi, by Peturkova gorica | Karta 22, 212–213 | 46.135, 16.87 |
| Laskaeghaz (László-egyház) | 5 | **Sveti Ladislav** — lost bishop's estate/church kod Borovljana, E of Koprivnica | 202–208, Karta 20–21 | 46.111, 16.892 |
| Thopolyancz + Thopolchazenthgergh (merged) | 2+2 | **Topolovo** — biskupski posjed uz Sredice/Delovi, kod Novigrada Podravskog | Karta 21, 209–210 | 46.115, 16.975 |

*Multi-year `SUM(taxable_selista)`, not per-year.

Result: reds 312 → **308**, yellow 637 → **640**. Validation passing.

### No-scan quick wins applied alongside (Adamček / Buturac / p.81)

| Red | Sel. | → Modern | Source |
|---|---|---|---|
| Brezewcze cum pertinentiis (**largest single red**) | 354 | **Brezovica kod Virovitice** (same estate as Nešetino) | Buturac + Adamček |
| Dobrachwcha cum pertinentiis | 90 | **Dobra Kuća** (castrum nr Đulovac/Daruvar) — *not* the đurđevec "Dobra kuća brdo" of p.194 | Adamček; Buturac alt.: Korjeničani nr Bastaji |
| Bellyanowcz / Belyowcz / Belyancz | 41.5 | **Belanovo selo** (nestalo selo rasinjskog vlastelinstva, JZ od Rasinje) | Pavleš p.81–82 |

Cumulative after this batch + quick wins: reds → **305**.

**Distinguished three separate "St-Ladislav" census entries** (do NOT merge):
`Zenth Laczlo` → Ladislav Sokolovački (SW, already pinned); `Zenthlazlo` → Tomašica
(Garešnica/Bilogora, yellow); `Laskaeghaz` → the lost Podravina Sv. Ladislav kod Borovljana
(this batch).

**Confirmatory only (already green / not in red list):** the Rasinja-lordship villages
(Kuzminec, Koledinec, Vojvodinec, Zablatje, Antolovec, Zelnica, Gorica, Grbaševec,
Botinovec, Subotica, Vrhovec, Delekovec, Selnica, Torčec, Imbriovec, Vidak) and the
đurđevec-vlastelinstvo villages (Sušica, Hrastovec, Brestovec, Gregorjanec, Javorovec,
Miketinec, Valentovci, Farkaševci, Čaovci, Dravice, Prikraj, Molve, Beludovec, Doroslavec)
are not among the 308 reds — this batch confirmed their placement but yielded no new pins.

**Available for future precision refinement (currently yellow, could be greened):**
Gorbonokfew (→ Kloštar Podravski/Gorbonok), Belwdowyna (→ Beludovec N of Rovišče),
Felsew Bakwa ×3 (→ Bukovica "de Prodaviz" nr Virovitica, p.192), the Zdenčan/Temerje
cluster (aid 1655/1656/1658/1475, p.214), Werthlyn (p.193). Pavleš gives enough to
tighten these, but they already carry approximate coordinates.

## Consolidated page list to photograph

- **Priority:** 38, 90, 106, 109, 122, 156–157, 160–162, 175, 186, 191–192, 220
- **Then:** 79, 81, 188, 193, 194, 204–205, 212–213, 217
- **Context (Vlach/lordship):** 68–69, 74, 137–165, 174, 176, 195, 201
