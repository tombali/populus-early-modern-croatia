"""Shared helpers for authority/variant reconciliation (places, code lists).

`fold` collapses early-modern Latin/Slavic orthographic variation to a match
key; `vowel_skeleton` and `UnionFind` support fuzzy clustering. Kept here so the
place-authority and code-authority steps use identical logic.
"""
import re
import unicodedata

_ORTHO_REPS = [("cz", "c"), ("ch", "c"), ("sz", "s"), ("th", "t"),
               ("ph", "f"), ("gh", "g"), ("ck", "k"), ("w", "v"),
               ("y", "i"), ("u", "v")]


def fold(name):
    """Collapse early-modern Latin/Slavic orthographic variation to a key.

    Drops diacritics and every non-letter (so `*`, `(?)`, parentheses and
    stray punctuation are ignored), lowercases, applies orthographic
    equivalences, and de-doubles letters.
    """
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z]", " ", s).lower().strip()
    for _ in range(2):
        for a, b in _ORTHO_REPS:
            s = s.replace(a, b)
    s = re.sub(r"(.)\1+", r"\1", s)      # de-double letters
    s = re.sub(r"\s+", " ", s).strip()
    return s


def vowel_skeleton(key):
    """Fuzzy helper: fold key with vowels stripped (a/e/i/o dropped, v kept)."""
    return re.sub(r"[aeio]", "", key)


class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        self.parent[self.find(a)] = self.find(b)
