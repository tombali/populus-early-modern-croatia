# The "invisible giants" — large reds not in Pavleš, mined from the source corpus

The biggest unresolved (`lat IS NULL`) census places in **county 1 (Körös/Križevačka)** have
no match in Pavleš's Podravina gazetteer (they lie outside his area). This is the result of
running them against the full-text `sources/corpus/` (Heller *Comitatus Crisiensis*, Adamček,
Diplomatarium Crisiense, Pálosfalvi *Noble Elite of Körös*, Pálffy 1556, Buturac, Csánki, Pesty…)
via the partial-match search tool `scratchpad/corpus_search.py` (fold-key substring search over
every corpus file, with page markers).

Method note: census **holder + judicial district** (from `tax_entries`) is often the decisive
clue — a magnate/institution landlord identifies the estate even when the toponym is opaque.

## Resolved & applied

| Red | Sel. | Holder(s) in census | → Identification | Source | Pin |
|---|---|---|---|---|---|
| **Kozachyna / Kwzachyna** | 69.5 | de Ervence + de Zenče (1495); Zempchey (1517) | **Kozacsina**, part of **Szencse**, in the **Svetačje** archdeaconate nr **Bijela Stijena** (=Fejérkő) | Pálosfalvi (Georgius de Erwencze held Szencse & Kozacsina); Buturac (Zencsefő kod Fejérkő; "Svetačje od Bijele Stijene do Novske") | 45.35, 17.19 |
| **Baganoz** | 63 | **Szapolyai** + *plebanus* (1507) | **Bagyanovc / Szentkereszt** = modern **Badljevina** (Pakrac) | Pálffy 1556 #119 "Zent Kewroczth = Szentkereszt/Bagyanovc, Križevačka ž. (Badljevina)"; Pálosfalvi (Horváth held Bagyanovc & Kustyerolc) | 45.513, 17.192 |
| **Jelye / Jellye** | 76 | **King** (1507) → **Abbatia bellensis** (1517) | estate of the **Bijela (Béla) Benedictine abbey**, modern **Bijela kod Sirača** | Buturac ("benediktinska opatija u Bijeloj kod Sirača") | 45.563, 17.290 |
| **Fyerky** | 260 (2nd-largest red) | **Franjo Berislavić** (1507) | **Fejérkő = Bijela Stijena** — the Berislavić castle-lordship | Buturac p.413 ("Franjo Berislavić, vlasnici grada i gospoštije **Bijele Stijene**, g. 1507"); Pálosfalvi ("Beriszló (Fejérkő [Bijela Stijena])", "huge estate … with two castles"); Pálffy 1556 & Klaić ("Feyerkew = Bijela stijena") | 45.342, 17.194 |

The Garazda-district giants (**Baganoz**, **Jelye**, **Fyerky**) all cluster in the **Pakrac–Daruvar
SE Bilogora** — corroborated by Pálffy 1556's neighbouring fortresses (Veliki Zdenci, Veliki
Grđevac, Gornji Sređani, Sopje). Fyerky (Fejérkő/Bijela Stijena) is the same complex as the
already-pinned **Kozacsina/Szencse** — both part of Berislavić's "Bijela Stijena i Svetačje."

## Identified but site not yet pinned (sourced leads)

- **Zwpya** (131; **Bishop of Zagreb**, district Csapolovec) → a Zagreb-bishopric Körös estate.
  No corpus name-match yet (only generic *zuppan/župa*). Bishop's Körös blocks were Ivanić /
  Dubrava / Čazma / Gorica — none an obvious fold-match to *Zwpya*. Open.

- **Waswarowcz** (74; Egervári → Kanizsai → **bishop of Knin**) → **Vasvárovec**, named after the
  **Waswary** family attested on the **đurđevec lordship** (1534, *podravina14*). đurđevec-area,
  exact site unlocated.

- **Zthara** (178; **Bánffy** + Kishorváth) → literally **"Stara [Ves]"** (corpus: *Ztara Wez* =
  Stara Ves, *Zthara sela* = Stara Sela). A large "Old Village" held by the Bánffy; which one is
  open.

## Also resolved from the mid-tier dig (applied)

| Red | Sel. | Holder(s) | → Identification | Source | Pin |
|---|---|---|---|---|---|
| **Crysancz** | 19 (c2) | Spychko / Zpyko | **Križanec** (nr Varaždin) — "Johannes Spychko **de Crysancz**" | Klaić, *Topografske sitnice* (Špičko de Crysancz, 1500); county + phonetic match | 46.245, 16.343 |
| **Kerhnyewyna** (+ **Kerhennyna**, 8 sel — merged) | 11 (c1) | Ladislaus, Michael (Kerhen family) | **Kerhevina** — lost possession of the **Kerhen** family "in the region of **Fejérkő**" (=Bijela Stijena) | Pálosfalvi (Kerhen/Kerhnewych "always bore the name of the possession of Kerhevina … around Fejérkő") | 45.36, 17.22 (approx) |
| **Kazmethyna** | 7 (c1) | Andreas Dominus | **Kaznetina** — in the appurtenances of Koprivnica, "Gegend Mučna/Vlajislav" | Heller Cris ("Kaznethyn p/v in pertinentiis Kaproncza"); podravina04 ("Kaznetina … nekad dio koprivničkog vlastelinstva") | 46.115, 16.745 (approx, nr Velika Mučna) |
| **Maroucha** | 4 (c1) | Ladislaus | **Marocha** nr **Ivanska** (Čazma province) — *not* the Zagreb-county Moravče homonym | Heller Cris ("1507 Maroucha prov Chasmensis … Gegend Ivanska") | 45.782, 16.806 (approx) |

Kerhevina is another piece of the **Fejérkő/Bijela Stijena** complex (with Fyerky and Kozacsina).

## Swept to exhaustion (reds ≤3 sel): confirmed-but-unpinnable

A full dig of all remaining reds (ranks ~130–290) found many that the corpus **attests but does not
locate** — the gazetteers confirm the toponym existed without giving a modern equivalent, so they
stay red rather than get a speculative pin:
- **Ramagawelge** (Paulus de Raven; Heller attests, no modern), **Koroska/Bedowcz** (Heller:
  "Koroska Zenth Ilona … eccl Szent Illona", no modern), **Ozwgyo-Zenthgergh** (Batthyány; Heller
  "Ozwgyo cup Zenthgeorgh" nr Sveti Đurđ), **Wydyncz** (Heller attests only), **Chernacz** (in the
  Berislavić Totuševina estate list, but several homonyms), **Janowcz** (c1, ambiguous vs the
  already-pinned Janovec).
- **Church-dedication reds** with no distinctive toponym: Omnii Sancti, Sanctus Stephanus, Sancta
  Anna/Elena/Katharina/Maria, Zenth Nedele, Sanctus Benedictus.
- The **c3 Vlach *waywodatus* cluster** (Wlachin, Rawennyk, Wogrynincz, Zkakala, Kwthetincz,
  Krayowcz, Powsyncz/Powsevcz, Zehanowcz) — 17th-c. resettlements absent from the medieval
  gazetteers; Orrosovc/Csakovc/Povsinc are a known lost tenant cluster (Pálosfalvi) with no coords.

## Next-tier leads (from the top-30 corpus dig, `reds_dig.txt`)

- **Orosowcz / Orrosowcz** (42; **Gabriel Oros**) → **Orrosovc**, the single-village seat of the
  **Orros de Orrosovc** family, with tenant plots at "Orrosovc, Csakovc and **Povsinc** (Verőce)"
  — i.e. adjacent to our red `Powsincz`, in the SE-Bilogora Dobra Kuća/Prodaviz noble milieu
  (Pálosfalvi 44, 226–227, 30). Lost village, no coordinates yet. **Reconfirmed** by a 2nd red
  `Orossowcz, Chakawcz` (13 sel, holder Nicolaus Oros) = the same Orrosovc + Csakovc pair; and the
  c3 red `Powsyncz/Powsynch` is the Verőce Povsinc of the same tenant cluster. All three lost,
  region (SE Bilogora, Dobra Kuća/Prodaviz orbit) known but no coordinates.
- **Zenthendree** (90, c3; **Báthory**) → **Szentandrás**, Heller Cris attests it in **distr.
  Garić**, tied to **Ravenica/Raven** and later **"Denkovec-Szentandrás"** (Heller p.132). But
  Heller's is the Garić (Moslavina) one while the census tags c3 — possible homonym; needs care.
- **Mahowcz** (56, c4; Horvat de **Zelina**, Pezer, ad Rakovec) → Heller Zagrab. cross-refs
  **Mahovo** (1598 Mahowschycza), but the Zelina/Rakovec holders point NE (Zelina/Vrbovec), not
  Mahovo near Popovača — unresolved.
- **Gerwasowcz** (43; Nicolaus Gerwas + *plebanus* Koprivnica) → a Komarnica/đurđevec-district
  toponym in Pavleš's name-etymology list (p.14, grouped with Oliverec); no precise site given.
- **Czeraberda / Chereborda** (50 + 44; both **Bánffy**) → "Cerova brda / Cere brda"; the
  rankopavleš snippet groups "Urbona, Cherova berda et Rachina … Pousini". Bánffy Bilogora
  estates; unlocated. (Same Bánffy holder as **Zthara**.)

## The tool

`scratchpad/corpus_search.py` — fold-key substring search over `sources/corpus/*.txt`, printing
source + page + line for each hit. Reusable for any remaining red: seed it with the historical
spelling's fold-key and phonetic variants.
