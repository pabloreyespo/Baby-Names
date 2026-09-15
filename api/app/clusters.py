"""Precomputed name families, run once by scripts/build_data.py.

Two layers:
1. Phonetic key (fonetica.key): spellings that sound the same share a key.
2. Typo tolerance between keys: a rare key attaches to a much more frequent head key
   one edit apart (Damerau-Levenshtein) when both are at least MIN_KEY_LEN long, start
   with the same letter, and their dominant registered sex agrees. The sex guard keeps
   Spanish masculine/feminine pairs (Valentín/Valentina, Mario/María, Juan/Juana) apart
   even though they are one letter away. Attachment is one level deep (star shaped),
   so families never chain Ana into Ani into Ali.

Spelling-level one-edit pairs between names are also stored, for the "one letter
away" view, independent of sound.
"""

from __future__ import annotations

import polars as pl
from rapidfuzz.distance import DamerauLevenshtein

from .fonetica import key

MIN_KEY_LEN = 5
RATIO = 20  # a typo key must be at least 20x rarer than the head it attaches to
ABS_MAX = 1000  # and rare in absolute terms; Marina is not a misspelling of María


def _deletions(s: str) -> list[str]:
    return [s] + [s[:i] + s[i + 1 :] for i in range(len(s))]


def _candidate_pairs(items: pl.DataFrame, col: str) -> pl.DataFrame:
    """Unordered pairs of rows whose `col` strings are one edit apart (symmetric deletion + verify)."""
    keyed = items.with_columns(k=pl.col(col).map_elements(_deletions, return_dtype=pl.List(pl.String))).explode("k")
    cand = keyed.join(keyed, on="k", suffix="_b").filter(pl.col(col) < pl.col(f"{col}_b")).unique(subset=[col, f"{col}_b"]).drop("k")
    ok = [DamerauLevenshtein.distance(a, b, score_cutoff=1) == 1 for a, b in zip(cand[col], cand[f"{col}_b"])]
    return cand.filter(pl.Series(ok))


def spelling_pairs(names: pl.DataFrame) -> pl.DataFrame:
    """names: nombre, inscritos. Returns nombre, inscritos, nombre_b, inscritos_b at edit distance 1 (case-insensitive)."""
    base = names.select("nombre", "inscritos").with_columns(low=pl.col("nombre").str.to_lowercase())
    p = _candidate_pairs(base, "low")
    return p.select("nombre", "inscritos", "nombre_b", "inscritos_b")


def phonetic_clusters(names: pl.DataFrame) -> pl.DataFrame:
    """names: nombre, inscritos, mujeres, hombres. Returns nombre, fon, cluster (int id).

    Cluster ids are arbitrary; the caller picks the most frequent member as representative.
    """
    n = names.with_columns(fon=pl.col("nombre").map_elements(key, return_dtype=pl.String))
    keys = n.group_by("fon").agg(
        inscritos=pl.col("inscritos").sum(),
        mujeres=pl.col("mujeres").sum(),
        hombres=pl.col("hombres").sum(),
    ).with_columns(fem=pl.col("mujeres") >= pl.col("hombres"), n=pl.col("fon").str.len_chars())

    long_keys = keys.filter(pl.col("n") >= MIN_KEY_LEN).select("fon", "fem")
    links = _candidate_pairs(long_keys, "fon").filter(
        (pl.col("fem") == pl.col("fem_b")) & (pl.col("fon").str.slice(0, 1) == pl.col("fon_b").str.slice(0, 1))
    )
    adj: dict[str, list[str]] = {}
    for a, b in zip(links["fon"], links["fon_b"]):
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)

    # Star attachment, no chaining: walk keys from most to least frequent. A key becomes a head
    # unless a head one edit away is at least RATIO times more frequent, in which case it is a
    # misspelling of that head. Attached keys can never receive attachments themselves.
    freq = dict(zip(keys["fon"], keys["inscritos"]))
    heads: set[str] = set()
    roots: dict[str, str] = {}
    for k in keys.sort("inscritos", descending=True)["fon"]:
        cands = [h for h in adj.get(k, ()) if h in heads and freq[h] >= RATIO * freq[k]] if freq[k] <= ABS_MAX else []
        if cands:
            roots[k] = max(cands, key=freq.__getitem__)
        else:
            heads.add(k)
            roots[k] = k

    ids = {r: i for i, r in enumerate(sorted(set(roots.values())))}
    fon_cluster = pl.DataFrame({"fon": list(roots), "cluster": [ids[r] for r in roots.values()]})
    return n.select("nombre", "fon").join(fon_cluster, on="fon").with_columns(pl.col("cluster").cast(pl.Int64))
