"""Controlled-vocabulary glosses (Latin -> English) for the small code lists.

These are starter authority lists; the book is the definitive source for
ambiguous terms. Values not listed keep an empty english gloss to be filled in
later.
"""

SETTLEMENT_TYPE_GLOSS = {
    "castrum": ("castrum", "castle / fortified seat"),
    "castellum": ("castellum", "small castle"),
    "fortalitium": ("fortalitium", "fortress"),
    "arx": ("arx", "citadel / stronghold"),
    "oppidum": ("oppidum", "market town"),
    "villa": ("villa", "village"),
    "praedium": ("praedium", "estate / manor farm"),
    "curia": ("curia", "noble manor court"),
    "possessio": ("possessio", "landed possession"),
    "abbatia": ("abbatia", "abbey"),
    "capitulum": ("capitulum", "cathedral chapter"),
    "cantoratus": ("cantoratus", "cantorate benefice"),
    "villicatus": ("villicatus", "bailiwick / steward's district"),
    "judicatus": ("judicatus", "judicial district"),
    "provincia": ("provincia", "province / fiscal district"),
    "districtus": ("districtus", "district"),
}

STATUS_GLOSS = {
    "Relicta": "widow (relict)",
    "Heredes": "heirs",
    "Orphani": "orphans",
    "Orphanus": "orphan",
    "quondam": "the late (deceased)",
    "Filius": "son",
    "Filii": "sons",
    "Puella": "unmarried girl / maiden",
    "Pauper": "pauper",
    "Relictarum": "of the widows",
    "Consors": "wife / consort",
    "Uxor": "wife",
    "Vidua": "widow",
}

TITLE_GLOSS = {
    "Dominus": "lord",
    "Domina": "lady",
    "Domini": "lords",
    "Dux": "duke",
    "Comes": "count",
    "Reverendissimus dominus": "most reverend lord",
    "Nobilis": "noble",
    "Nobiles": "nobles",
    "Nobiles campi Zagrabiensis": "nobles of the Zagreb field (Turopolje)",
    "Magnificus": "magnate (magnificent)",
    "Magnificus dominus": "magnificent lord",
    "Dominus, comes": "lord, count",
    "Domini, comites": "lords, counts",
}

# Common institutions/offices — the full list is large free text, so only the
# frequent, unambiguous ones are glossed here.
INSTITUTION_GLOSS = {
    "Župnik (plebanus)": "parish priest",
    "Litteratus": "literate / clerk (litteratus)",
    "Biskup zagrebački (Episcopus Zagrabiensis)": "Bishop of Zagreb",
    "Kaptol zagrebački (Capitulum Zagrabiense)": "Zagreb cathedral chapter",
    "Judex nobilium": "noble magistrate (judge of nobles)",
    "Prebendar (prebendarius)": "prebendary",
    "Prebendarius": "prebendary",
    "Vicecomes": "vice-count (deputy count)",
    "Vicejudex nobilium": "deputy noble magistrate",
    "Magister": "master",
    "Eremiti (Fratres heremitae)": "Pauline hermit friars",
    "Banus": "ban (viceroy)",
}
