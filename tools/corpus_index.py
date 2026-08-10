"""corpus_index.py — persistent, word-boundary corpus index for red-hunting.

Every ad-hoc sweep script used to re-read and re-fold all ~35 corpus files into
memory and match by space-stripped substring — slow, and noisy (the folded
stem `nasena` matches the ordinary phrase `danas se nalazi`). This builds the
index ONCE into a SQLite db and queries it cheaply, matching on **folded whole
words** so cross-whitespace collisions disappear.

The index folds each word with the pipeline's own `authority_lib.fold`, so a
census spelling and a corpus word collapse to the same key exactly as the
place-authority step would collapse two spellings.

Stdlib only. Index lives at sources/corpus/index.sqlite (git-ignored with the
rest of sources/). Rebuild whenever corpus files change.

Usage
-----
  python tools/corpus_index.py build
  python tools/corpus_index.py search "Nassenyna" [--mode word|prefix|contains] [--limit 40]
  python tools/corpus_index.py sweep [--county 2] [--holders] [--contains] [--min-tax 1]

`search` looks up one term. `sweep` runs every remaining red's spellings (and
optionally holder surnames) against the index and prints grouped hits — the
"search all reds against the whole corpus" operation, from the index.
"""
import argparse
import os
import re
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
from authority_lib import fold  # noqa: E402  (canonical fold, matches step 06)

CORPUS = os.path.join(ROOT, "sources", "corpus")
INDEX = os.path.join(CORPUS, "index.sqlite")
DB = os.path.join(ROOT, "db", "tax_lists.sqlite")

WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)   # letter-runs only
PAGE_RE = re.compile(r"\[p\.?\s*(\d+)\]")

# tokens too generic to be worth indexing as search stems on the query side
STOP = {"superior", "inferior", "oppidum", "castrum", "castellum", "provincia",
        "waywodatus", "wayvodatus", "judicatus", "iudicatus", "villa",
        "sanctus", "sancta", "sancte", "sancti", "zenth", "apud", "prope",
        "pertinentiis", "pertinencia", "novum", "maior", "minor", "villicatus",
        "castri", "bona", "possessio", "predium", "terra", "cum", "sub",
        "citra", "nobiles", "sessionis", "unius", "utraque", "uterque",
        "ecclesia", "eccl", "plebanus", "plebani", "iwan", "ivan", "mihal",
        "michael", "martinus", "georgius", "petrus", "paulus", "stephanus",
        "crucis", "maria", "insula", "campus", "gorica", "comes"}


def foldtok(word):
    """Fold a single word to its match token (fold() may split/de-double)."""
    f = fold(word)
    return f.replace(" ", "")


def cmd_build(args):
    if not os.path.isdir(CORPUS):
        print(f"no corpus dir at {CORPUS}")
        return 1
    con = sqlite3.connect(INDEX)
    con.executescript(
        "DROP TABLE IF EXISTS docs; DROP TABLE IF EXISTS lines;"
        "DROP TABLE IF EXISTS postings;"
        "CREATE TABLE docs(doc_id INTEGER PRIMARY KEY, filename TEXT);"
        "CREATE TABLE lines(line_id INTEGER PRIMARY KEY, doc_id INT, "
        "  page TEXT, raw TEXT);"
        "CREATE TABLE postings(tok TEXT, line_id INT);")
    files = sorted(f for f in os.listdir(CORPUS)
                   if f.endswith(".txt"))
    line_id = 0
    n_post = 0
    for doc_id, fn in enumerate(files):
        con.execute("INSERT INTO docs VALUES(?,?)", (doc_id, fn))
        page = "?"
        with open(os.path.join(CORPUS, fn), encoding="utf-8") as fh:
            for raw in fh:
                raw = raw.rstrip("\n")
                m = PAGE_RE.search(raw)
                if m:
                    page = m.group(1)
                toks = {foldtok(w) for w in WORD_RE.findall(raw)}
                toks = {t for t in toks if len(t) >= 3}
                if not toks:
                    continue
                line_id += 1
                con.execute("INSERT INTO lines VALUES(?,?,?,?)",
                            (line_id, doc_id, page, re.sub(r"\s+", " ", raw).strip()))
                con.executemany("INSERT INTO postings VALUES(?,?)",
                                [(t, line_id) for t in toks])
                n_post += len(toks)
    con.execute("CREATE INDEX ix_post_tok ON postings(tok)")
    con.execute("CREATE INDEX ix_post_line ON postings(line_id)")
    con.commit()
    print(f"indexed {len(files)} files, {line_id} lines, {n_post} postings "
          f"-> {INDEX}")
    con.close()
    return 0


def _lookup(con, stem, mode, limit=60):
    if mode == "word":
        where, param = "p.tok = ?", (stem,)
    elif mode == "prefix":
        where, param = "p.tok LIKE ?", (stem + "%",)
    else:  # contains (within a single word — still no cross-whitespace noise)
        where, param = "p.tok LIKE ?", ("%" + stem + "%",)
    q = (f"SELECT d.filename, l.page, l.raw FROM postings p "
         f"JOIN lines l ON l.line_id = p.line_id "
         f"JOIN docs d ON d.doc_id = l.doc_id "
         f"WHERE {where} GROUP BY l.line_id LIMIT {int(limit)}")
    return list(con.execute(q, param))


def cmd_search(args):
    if not os.path.exists(INDEX):
        print("no index — run: python tools/corpus_index.py build")
        return 1
    con = sqlite3.connect(INDEX)
    stem = foldtok(args.term)
    rows = _lookup(con, stem, args.mode, args.limit)
    print(f"'{args.term}' -> fold '{stem}' [{args.mode}] : {len(rows)} hits")
    for fn, page, raw in rows:
        print(f"  [{fn[:34]:34} p.{page:>4}] {raw[:120]}")
    con.close()
    return 0


def _reds(con_db, county):
    tax = {r[0]: (r[1] or 0) for r in con_db.execute(
        "SELECT authority_id, ROUND(SUM(taxable_selista),1) "
        "FROM v_entries_authority WHERE authority_id IS NOT NULL "
        "GROUP BY authority_id")}
    sp, pids = {}, {}
    for aid, h, p in con_db.execute(
            "SELECT authority_id, historical_name, place_id FROM place_crosswalk"):
        sp.setdefault(aid, set()).add(h)
        pids.setdefault(aid, set()).add(p)
    q = ("SELECT authority_id, canonical_name, county_id FROM place_authority "
         "WHERE COALESCE(hide_from_map,0)=0 AND lat IS NULL")
    if county:
        q += f" AND county_id = {int(county)}"
    reds = [{"a": a, "n": n, "c": c} for a, n, c in con_db.execute(q)]
    reds.sort(key=lambda r: -tax.get(r["a"], 0))
    return reds, tax, sp, pids


def cmd_sweep(args):
    if not os.path.exists(INDEX):
        print("no index — run: python tools/corpus_index.py build")
        return 1
    con = sqlite3.connect(INDEX)
    con_db = sqlite3.connect(DB)
    reds, tax, sp, pids = _reds(con_db, args.county)
    mode = "contains" if args.contains else "word"

    def holder_surnames(ps):
        ph = ",".join("?" * len(ps))
        out = set()
        for (s,) in con_db.execute(
                f"SELECT DISTINCT p.surname FROM tax_entries te "
                f"LEFT JOIN persons p ON te.person_id=p.person_id "
                f"WHERE te.place_id IN ({ph}) AND p.surname IS NOT NULL",
                list(ps)):
            out.add(s)
        return out

    shown = 0
    for r in reds:
        if tax.get(r["a"], 0) < args.min_tax:
            continue
        a = r["a"]
        spellings = sp.get(a, {r["n"]})
        stems = set()
        for h in spellings:
            for w in re.split(r"[ ,\-]+", h):
                if w.lower() in STOP:
                    continue
                t = foldtok(w)
                if len(t) >= 4:
                    stems.add(t)
        holder_stems = set()
        if args.holders:
            for s in holder_surnames(pids.get(a, [])):
                for w in re.split(r"[ ,\-*()]+", s):
                    if w.lower() in STOP:
                        continue
                    t = foldtok(w)
                    if len(t) >= 5:
                        holder_stems.add(t)

        seen, out_lines = set(), []
        for stem in sorted(stems, key=len, reverse=True):
            for fn, page, raw in _lookup(con, stem, mode, 40):
                key = (fn, raw[:40])
                if key in seen:
                    continue
                seen.add(key)
                out_lines.append(f"     PLACE  [{fn[:30]} p.{page}] ({stem}) {raw[:110]}")
        for stem in sorted(holder_stems, key=len, reverse=True):
            for fn, page, raw in _lookup(con, stem, "word", 25):
                key = (fn, raw[:40])
                if key in seen:
                    continue
                seen.add(key)
                out_lines.append(f"     HOLDER [{fn[:30]} p.{page}] ({stem}) {raw[:110]}")

        if out_lines or not args.hits_only:
            shown += 1
            print(f"\n#### c{r['c']} tax={tax.get(a,0):<6} {r['n'][:30]:<30} "
                  f"[{'|'.join(sorted(spellings))[:60]}]")
            if not out_lines:
                print("     (no word-boundary hits)")
            for ln in out_lines:
                print(ln)
    print(f"\n[{shown} reds shown; mode={mode}; "
          f"county={args.county or 'all'}; min_tax={args.min_tax}]")
    con.close()
    con_db.close()
    return 0


def _lev(a, b, maxd):
    """Levenshtein distance, capped: returns the distance, or maxd+1 if it
    exceeds maxd. Full DP with a per-row minimum cutoff for early exit."""
    la, lb = len(a), len(b)
    if abs(la - lb) > maxd:
        return maxd + 1
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        row_min = cur[0]
        ai = a[i - 1]
        for j in range(1, lb + 1):
            cost = 0 if ai == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if cur[j] < row_min:
                row_min = cur[j]
        if row_min > maxd:
            return maxd + 1
        prev = cur
    return prev[lb] if prev[lb] <= maxd else maxd + 1


# terminal modern-identification markers only (NOT every attestation year):
#   "(Im.)"  = 1973 Imenik naselja settlement name (Heller's modern id)
#   "Gegend X" = Heller's "in the area of X"; "Danas X" = Bösendorfer-style
MODERN_RE = re.compile(r"\(Im\.\)|Gegend |Danas ")


def cmd_fuzzy(args):
    """For each red, find Heller entries whose token is within edit-distance
    1-2 of a red spelling AND that carry a modern-name marker — catching the
    Heller-predates-Popisi case where the spelling drifts by a char or two."""
    if not os.path.exists(INDEX):
        print("no index — run: python tools/corpus_index.py build")
        return 1
    con = sqlite3.connect(INDEX)
    con_db = sqlite3.connect(DB)
    reds, tax, sp, pids = _reds(con_db, args.county)

    # load Heller lines + build token vocab (Heller docs only)
    heller_docs = {r[0] for r in con.execute(
        "SELECT doc_id FROM docs WHERE filename LIKE 'heller%'")}
    lines = {}   # line_id -> (doc_id, page, raw, filename)
    for lid, did, page, raw in con.execute(
            "SELECT l.line_id,l.doc_id,l.page,l.raw FROM lines l"):
        if did in heller_docs:
            lines[lid] = (did, page, raw)
    fn_of = {r[0]: r[1] for r in con.execute("SELECT doc_id,filename FROM docs")}
    tok_lines = {}
    for tok, lid in con.execute("SELECT p.tok,p.line_id FROM postings p"):
        if lid in lines:
            tok_lines.setdefault(tok, set()).add(lid)
    vocab = [t for t in tok_lines if len(t) >= 4]

    def entry_has_modern(lid):
        did = lines[lid][0]
        for k in range(lid, lid + 6):          # this line + a few after
            if k in lines and lines[k][0] == did and MODERN_RE.search(lines[k][2]):
                return lines[k][2]
        return None

    shown = 0
    for r in reds:
        if tax.get(r["a"], 0) < args.min_tax:
            continue
        stems = set()
        for h in sp.get(r["a"], {r["n"]}):
            for w in re.split(r"[ ,\-]+", h):
                if w.lower() in STOP:
                    continue
                t = foldtok(w)
                if len(t) >= 5:
                    stems.add(t)
        hits = []
        for stem in stems:
            md = 1 if len(stem) <= 6 else 2
            for tok in vocab:
                # require close length (drift is 1-2 chars, not wholesale)
                if tok == stem or abs(len(tok) - len(stem)) > 1:
                    continue
                d = _lev(stem, tok, md)
                if 1 <= d <= md:
                    for lid in sorted(tok_lines[tok])[:3]:
                        modern = entry_has_modern(lid)
                        if modern:
                            hits.append((d, stem, tok, fn_of[lines[lid][0]],
                                         lines[lid][1], lines[lid][2], modern))
        if hits:
            # keep the best candidates only: lowest edit-distance, then longest
            # stem; dedupe by matched token; cap per red to stay readable.
            hits.sort(key=lambda x: (x[0], -len(x[1])))
            seen, kept = set(), []
            for h in hits:
                if h[2] in seen:
                    continue
                seen.add(h[2])
                kept.append(h)
                if len(kept) >= args.per_red:
                    break
            shown += 1
            print(f"\n#### c{r['c']} tax={tax.get(r['a'],0):<6} {r['n'][:28]:<28} "
                  f"[{'|'.join(sorted(sp.get(r['a'],{r['n']})))[:46]}]")
            for d, stem, tok, fn, page, raw, modern in kept:
                print(f"   d{d} {stem}~{tok} [{fn[:22]} p.{page}] {raw[:70]}")
                if modern != raw:
                    print(f"       →{modern[:96]}")
    print(f"\n[{shown} reds with fuzzy Heller+modern-name candidates; "
          f"county={args.county or 'all'}]")
    con.close()
    con_db.close()
    return 0


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build", help="(re)build the index").set_defaults(func=cmd_build)
    s = sub.add_parser("search", help="look up one term")
    s.add_argument("term")
    s.add_argument("--mode", choices=["word", "prefix", "contains"], default="word")
    s.add_argument("--limit", type=int, default=60)
    s.set_defaults(func=cmd_search)
    w = sub.add_parser("sweep", help="run all reds against the index")
    w.add_argument("--county", type=int)
    w.add_argument("--holders", action="store_true", help="also search holder surnames")
    w.add_argument("--contains", action="store_true",
                   help="match stem inside words (wider, noisier) vs whole-word")
    w.add_argument("--min-tax", type=float, default=0.0)
    w.add_argument("--hits-only", action="store_true",
                   help="skip reds with no hits")
    w.set_defaults(func=cmd_sweep)
    f = sub.add_parser("fuzzy", help="fuzzy-match reds to Heller entries w/ modern names")
    f.add_argument("--county", type=int)
    f.add_argument("--min-tax", type=float, default=0.0)
    f.add_argument("--per-red", type=int, default=3, help="max candidates per red")
    f.set_defaults(func=cmd_fuzzy)
    args = ap.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
