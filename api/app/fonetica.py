"""Phonetic key for Spanish-as-written-in-Chile first names.

Two spellings share a key when a Chilean would pronounce them the same:
Christopher, Cristofer, Khristopher -> "kristofer"; Alexander, Aleksander,
Alexsander -> "aleksander"; Ximena, Jimena, Gimena -> "jimena".

Rules are applied in order. Deliberate choices:
- "ch" followed by a vowel stays the Spanish "ch" sound; before a consonant or at the
  end it is the Greek/English hard "k" (Christian, Zach).
- "x" at the start is the old Spanish "j" (Ximena); elsewhere it is "ks" (Alexander).
- "y" and "ll" both become "i", so Bryan and Brian meet; Brayan stays apart on purpose,
  it sounds different.
- Doubled letters collapse (Rebecca / Rebeca, Alexsander / Aleksander).
"""

from __future__ import annotations

import re
import unicodedata

_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"ll"), "i"),  # before collapsing doubles
    (re.compile(r"(.)\1+"), r"\1"),  # collapse doubles early (Higgins, Rebecca)
    (re.compile(r"ph"), "f"),
    (re.compile(r"th"), "t"),
    (re.compile(r"ch(?=[^aeiou]|$)"), "k"),  # Christian, Zach
    (re.compile(r"sh"), "ch"),  # Sharon / Charon
    (re.compile(r"ch"), "C"),  # protect real ch before dropping h
    (re.compile(r"sc(?=[ei])"), "s"),  # Francesca
    (re.compile(r"ck|qu|q"), "k"),
    (re.compile(r"c(?=[ei])"), "s"),
    (re.compile(r"c"), "k"),
    (re.compile(r"z"), "s"),
    (re.compile(r"^x"), "j"),  # Ximena
    (re.compile(r"x"), "ks"),  # Alexander
    (re.compile(r"gu(?=[ei])"), "G"),  # hard g: Miguel, Guillermo
    (re.compile(r"g(?=[ei])"), "j"),  # Gimena, Gerardo
    (re.compile(r"h"), ""),  # silent
    (re.compile(r"y"), "i"),
    (re.compile(r"v"), "b"),
    (re.compile(r"w"), "u"),
    (re.compile(r"(.)\1+"), r"\1"),  # collapse doubles
]


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def key(name: str) -> str:
    s = re.sub(r"[^a-z]", "", strip_accents(name.strip().lower()))
    for pattern, repl in _RULES:
        s = pattern.sub(repl, s)
    return s.replace("C", "ch").replace("G", "g")
