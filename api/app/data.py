"""Load processed parquet files once and derive the tables every endpoint uses.

Port of the notebook setup cells: column names and the mortality correction
("vivos" = registrations scaled by the survival fraction). Rankings are
computed on demand in stats.py.
"""

from __future__ import annotations

import os
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import polars as pl

PROCESSED = Path(os.getenv("NOMBRES_DATA", Path(__file__).resolve().parents[2] / "data" / "processed"))
YEAR_MIN, YEAR_MAX = 1920, 2021


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def norm_key(s: str) -> str:
    return strip_accents(s.strip().lower())


@dataclass(frozen=True, eq=False)  # eq=False: hash by identity so lru_cache can key on Data
class Data:
    names: pl.DataFrame  # anio, nombre, sexo, inscritos, proporcion, vivos
    freq: pl.DataFrame  # nombre, inscritos, vivos, mujeres, hombres, ranking, ranking_vivos
    comunas: pl.DataFrame  # cut, region, provincia, comuna, poblacion, hombres, mujeres, pob_*, edad_promedio, key
    name_index: dict[str, list[str]]  # normalized key -> canonical spellings, most frequent first
    pairs: pl.DataFrame  # precomputed one-edit spelling pairs: nombre, inscritos, nombre_b, inscritos_b

    def canonical(self, nombre: str) -> str | None:
        hits = self.name_index.get(norm_key(nombre))
        if not hits:
            return None
        wanted = nombre.strip().lower()
        # Honor accents only when the visitor typed them; "MARIA" means the common "María".
        if wanted != strip_accents(wanted):
            exact = [h for h in hits if h.lower() == wanted]
            if exact:
                return exact[0]
        return hits[0]

    def comuna(self, name: str) -> dict | None:
        m = self.comunas.filter(pl.col("key") == norm_key(name))
        return None if m.is_empty() else m.row(0, named=True)


@lru_cache(maxsize=1)
def load() -> Data:
    df = pl.read_parquet(PROCESSED / "names.parquet").with_columns(pl.col("anio").cast(pl.Int32), pl.col("inscritos").cast(pl.Int64))
    mort = (
        pl.read_parquet(PROCESSED / "mortality.parquet")
        .select(anio=pl.col("nacimiento").cast(pl.Int32), sexo_tabla=pl.col("sexo"), sobrevive=pl.col("vivos"))
    )
    # Sex "I" (indeterminate) follows the male table, as in the notebook.
    df = (
        df.with_columns(sexo_tabla=pl.when(pl.col("sexo") == "F").then(pl.lit("F")).otherwise(pl.lit("M")))
        .join(mort, on=["anio", "sexo_tabla"], how="left")
        .with_columns(vivos=(pl.col("inscritos") * pl.col("sobrevive").fill_null(0.0)).round(0).cast(pl.Int64))
        .drop("sexo_tabla", "sobrevive")
    )

    freq = df.group_by("nombre").agg(
        inscritos=pl.col("inscritos").sum(),
        vivos=pl.col("vivos").sum(),
        mujeres=pl.col("inscritos").filter(pl.col("sexo") == "F").sum(),
        hombres=pl.col("inscritos").filter(pl.col("sexo") == "M").sum(),
    )
    # method "min": tied names share a rank (the notebook used "first").
    freq = (
        freq.with_columns(
            ranking=pl.col("inscritos").rank("min", descending=True).cast(pl.Int64),
            ranking_vivos=pl.col("vivos").rank("min", descending=True).cast(pl.Int64),
        )
        .join(pl.read_parquet(PROCESSED / "clusters.parquet"), on="nombre", how="left")  # fon, cluster
        .sort("inscritos", descending=True)
    )
    pairs = pl.read_parquet(PROCESSED / "pairs.parquet")

    comunas = pl.read_parquet(PROCESSED / "comunas.parquet")
    comunas = comunas.with_columns(key=pl.col("comuna").map_elements(norm_key, return_dtype=pl.String))

    index: dict[str, list[str]] = {}
    for n in freq["nombre"]:  # already most frequent first
        index.setdefault(norm_key(n), []).append(n)

    return Data(names=df, freq=freq, comunas=comunas, name_index=index, pairs=pairs)
