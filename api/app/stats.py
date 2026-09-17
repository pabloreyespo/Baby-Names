"""Statistics ported from the notebook, parameterized by name and birth year.

Everything is computed for both sexes together, with a female/male split
alongside so the story can talk about gender balance.
"""

from __future__ import annotations

import polars as pl

from .data import YEAR_MAX, YEAR_MIN, Data

YEARS = pl.DataFrame({"anio": pl.int_range(YEAR_MIN, YEAR_MAX + 1, eager=True).cast(pl.Int32)})


def fmt(n: float | int) -> str:
    """Spanish thousands separator: 1.234.567."""
    return f"{int(round(n)):,}".replace(",", ".")


def pct(x: float, digits: int = 1) -> str:
    return f"{x:.{digits}f}".replace(".", ",") + "%"


def dec(x: float, digits: int = 1) -> str:
    return f"{x:.{digits}f}".replace(".", ",")


def by_name(frame: pl.DataFrame) -> pl.DataFrame:
    """Collapse rows to one per name with total, female and male counts, ranked."""
    return (
        frame.group_by("nombre")
        .agg(
            inscritos=pl.col("inscritos").sum(),
            vivos=pl.col("vivos").sum(),
            mujeres=pl.col("inscritos").filter(pl.col("sexo") == "F").sum(),
            hombres=pl.col("inscritos").filter(pl.col("sexo") == "M").sum(),
        )
        .with_columns(ranking=pl.col("inscritos").rank("min", descending=True).cast(pl.Int64))
    )


def name_series(d: Data, nombre: str) -> pl.DataFrame:
    """Per-year totals for one name: inscritos, vivos, mujeres, hombres. Zero-filled 1920-2021."""
    s = d.names.filter(pl.col("nombre") == nombre)
    tot = s.group_by("anio").agg(
        inscritos=pl.col("inscritos").sum(),
        vivos=pl.col("vivos").sum(),
        mujeres=pl.col("inscritos").filter(pl.col("sexo") == "F").sum(),
        hombres=pl.col("inscritos").filter(pl.col("sexo") == "M").sum(),
    )
    return YEARS.join(tot, on="anio", how="left").fill_null(0).sort("anio")


def rank_in_year(d: Data, nombre: str, anio: int) -> dict | None:
    y = by_name(d.names.filter(pl.col("anio") == anio))
    row = y.filter(pl.col("nombre") == nombre)
    if row.is_empty():
        return None
    r = row.row(0, named=True)
    total = int(y["inscritos"].sum())
    return {
        "inscritos": int(r["inscritos"]),
        "mujeres": int(r["mujeres"]),
        "hombres": int(r["hombres"]),
        "ranking": int(r["ranking"]),
        "n_nombres": y.height,
        "beats_pct": float((y["ranking"] > r["ranking"]).mean() * 100),
        "share_year": r["inscritos"] / total if total else 0.0,
    }


def by_sex(frame: pl.DataFrame, sexo: str) -> pl.DataFrame:
    """One row per name within one registry sex, ranked (ties share a rank)."""
    return (
        frame.filter(pl.col("sexo") == sexo)
        .group_by("nombre")
        .agg(inscritos=pl.col("inscritos").sum())
        .with_columns(ranking=pl.col("inscritos").rank("min", descending=True).cast(pl.Int64))
        .sort("ranking", "nombre")
    )


def rank_by_sex(d: Data, nombre: str, anio: int) -> dict | None:
    """Rank of `nombre` within its dominant registry sex that year, plus the names ranked two
    above and two below (the visitor's neighborhood)."""
    y = d.names.filter(pl.col("anio") == anio)
    mine = y.filter(pl.col("nombre") == nombre)
    if mine.is_empty():
        return None
    f = int(mine.filter(pl.col("sexo") == "F")["inscritos"].sum())
    m = int(mine.filter(pl.col("sexo") == "M")["inscritos"].sum())
    sexo = "F" if f >= m else "M"
    t = by_sex(y, sexo)
    r = int(t.filter(pl.col("nombre") == nombre)["ranking"][0])
    window = t.filter(pl.col("ranking").is_between(r - 2, r + 2)).sort("ranking", "inscritos", descending=[False, True])
    # Ties can blow the window up; keep two above, me, two below.
    above = window.filter(pl.col("ranking") < r).tail(2)
    below = window.filter(pl.col("ranking") > r).head(2)
    me = window.filter(pl.col("nombre") == nombre)
    return {"sexo": sexo, "ranking": r, "n_nombres": t.height, "window": pl.concat([above, me, below])}


def top_by_sex(d: Data, anio: int, sexo: str, n: int = 10) -> pl.DataFrame:
    return by_sex(d.names.filter(pl.col("anio") == anio), sexo).head(n)


def top_names(d: Data, anio: int, n: int = 10) -> pl.DataFrame:
    y = by_name(d.names.filter(pl.col("anio") == anio)).sort("inscritos", descending=True).head(n)
    return y.unpivot(index=["nombre", "inscritos"], on=["mujeres", "hombres"], variable_name="sexo", value_name="inscripciones")


def alltime(d: Data, nombre: str) -> dict:
    r = d.freq.filter(pl.col("nombre") == nombre).row(0, named=True)
    f, m = int(r["mujeres"]), int(r["hombres"])
    return {
        "inscritos": int(r["inscritos"]),
        "vivos": int(r["vivos"]),
        "mujeres": f,
        "hombres": m,
        "share_f": f / (f + m) if f + m else 0.0,
        "ranking": int(r["ranking"]),
        "ranking_vivos": int(r["ranking_vivos"]),
        "beats_pct": float((d.freq["ranking"] > r["ranking"]).mean() * 100),
        "n_nombres": d.freq.height,
        "share_living": float(r["vivos"] / d.freq["vivos"].sum()),
    }


def gender_balance(share_f: float) -> str:
    if share_f >= 0.9:
        return "casi exclusivamente femenino"
    if share_f >= 0.7:
        return "mayoritariamente femenino"
    if share_f > 0.3:
        return "compartido entre mujeres y hombres"
    if share_f > 0.1:
        return "mayoritariamente masculino"
    return "casi exclusivamente masculino"


def cohort(d: Data, nombre: str, anio: int, radius: int = 5) -> dict:
    lo, hi = max(YEAR_MIN, anio - radius), min(YEAR_MAX, anio + radius)
    w = by_name(d.names.filter(pl.col("anio").is_between(lo, hi)))
    total, total_vivos = int(w["inscritos"].sum()), int(w["vivos"].sum())
    row = w.filter(pl.col("nombre") == nombre)
    mine = int(row["inscritos"][0]) if not row.is_empty() else 0
    vivos = int(row["vivos"][0]) if not row.is_empty() else 0
    rank = int((w["inscritos"] > mine).sum() + 1) if mine else None
    return {
        "lo": lo,
        "hi": hi,
        "inscritos": mine,
        "share": mine / total if total else 0.0,
        "ranking": rank,
        "vivos": vivos,
        "share_vivos": vivos / total_vivos if total_vivos else 0.0,
        "ranking_vivos": int((w["vivos"] > vivos).sum() + 1) if vivos else None,
        "n_vivos": int((w["vivos"] > 0).sum()),
        "n_nombres": w.height,
    }


def age_band(anio: int, census_year: int = 2024) -> str:
    age = census_year - anio
    return "pob_0_14" if age <= 14 else "pob_15_64" if age <= 64 else "pob_65_mas"


def poblacion_en(d: Data, cut: int, anio: int) -> dict:
    """Comuna population in a given year (Zenodo annual series) and its share of the country.
    Before a split the parent's figure is used, so `fuente` is the cut the number belongs to."""
    year = d.poblacion.filter(pl.col("anio") == anio)
    row = year.filter(pl.col("cut") == cut).row(0, named=True)
    total = year.filter(pl.col("cut") == pl.col("fuente"))["poblacion"].sum()  # own series only, parents are not double counted
    return {"poblacion": int(row["poblacion"]), "fuente": int(row["fuente"]), "share": row["poblacion"] / total if total else 0.0}


def city_share(d: Data, comuna: dict, col: str = "poblacion") -> float:
    """Comuna share of the national population, overall or within one age band."""
    total = d.comunas[col].sum()
    return float(comuna[col] / total) if total else 0.0


def year_in_city(d: Data, series: pl.DataFrame, anio: int, comuna_nac: dict, comuna_act: dict) -> dict:
    """Estimates for the visitor's birth year.

    born_cl: registered that year nationally (exact).
    born_city: born that year in the birth comuna, scaled by the comuna's share of the population.
    alive_cl: of that cohort, estimated alive today.
    alive_city: cohort members estimated to live in the current comuna today, scaled by the
    comuna's share of the national population in the visitor's age band.
    """
    row = series.filter(pl.col("anio") == anio).row(0, named=True)
    born_cl, alive_cl = int(row["inscritos"]), int(row["vivos"])
    band = age_band(anio)
    pob = poblacion_en(d, comuna_nac["cut"], anio)
    share_nac = pob["share"]
    share_act = city_share(d, comuna_act, band)
    return {
        "born_cl": born_cl,
        "born_city": int(round(born_cl * share_nac)),
        "born_city_iv": interval(born_cl, share_nac),
        "share_nac": share_nac,
        "pob_nac": pob["poblacion"],
        "fuente_nac": pob["fuente"],
        "alive_cl": alive_cl,
        "alive_city": int(round(alive_cl * share_act)),
        "alive_city_iv": interval(alive_cl, share_act),
        "share_act": share_act,
        "band": {"pob_0_14": "menores de 15", "pob_15_64": "de 15 a 64 años", "pob_65_mas": "de 65 años o más"}[band],
    }


def random_top_name(d: Data, n: int = 100) -> str:
    return str(d.freq.head(n)["nombre"].sample(1)[0])


COLS = ["nombre", "inscritos", "vivos", "mujeres", "hombres"]


def neighbors(d: Data, nombre: str) -> pl.DataFrame:
    """Registry names one edit away from `nombre` (insert, delete, substitute or swap adjacent
    letters, case-insensitive). Read from the precomputed pairs table."""
    p = d.pairs
    other = pl.concat([p.filter(pl.col("nombre") == nombre)["nombre_b"], p.filter(pl.col("nombre_b") == nombre)["nombre"]])
    return d.freq.filter(pl.col("nombre").is_in(other.to_list())).select(COLS).sort("inscritos", descending=True)


def family(d: Data, nombre: str) -> pl.DataFrame:
    """Every way `nombre` is written in the registry (same phonetic family, see clusters.py), the
    name itself included, most common first. `exacto` is True when the spelling sounds identical
    (same key: accents, hyphens, ph/f, k/c...), False when it is a one-letter typo of that sound."""
    me = d.freq.filter(pl.col("nombre") == nombre).row(0, named=True)
    return (
        d.freq.filter(pl.col("cluster") == me["cluster"])
        .select(COLS + ["fon"])
        .with_columns(exacto=pl.col("fon") == me["fon"])
        .sort("inscritos", descending=True)
    )


def interval(n: int, p: float, z: float = 1.645) -> tuple[int, int]:
    """90% interval for how many of `n` people fall in a place with population share `p`,
    binomial with a normal approximation. The lower bound is at least 1: the visitor exists."""
    import math

    mu = n * p
    sd = math.sqrt(max(n * p * (1 - p), 0.0))
    lo, hi = int(math.floor(mu - z * sd)), int(math.ceil(mu + z * sd))
    return max(1, lo), max(1, hi)


def rango(lo: int, hi: int) -> str:
    return f"{fmt(lo)}" if lo == hi else f"entre {fmt(lo)} y {fmt(hi)}"


def big_rango(lo: int, hi: int) -> str:
    """Short form for the chapter's big number: "1 a 7" or "3"."""
    return fmt(lo) if lo == hi else f"{fmt(lo)} a {fmt(hi)}"
