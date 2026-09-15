"""Discovery: names with k, w and y over the years, overall and by sex."""

from __future__ import annotations

import polars as pl

from .. import charts, stats
from ..data import Data

SLUG = "k-w-y"
TITLE = "Las letras que Chile importó: k, w e y"
DATE = "2026-09-15"
SUMMARY = "Tres letras casi ausentes del castellano y su ascenso en los nombres chilenos desde 1920, en mujeres y en hombres."
LETTERS = ["k", "w", "y"]
SEXO = {"F": "mujeres", "M": "hombres"}
LOW = pl.col("nombre").str.to_lowercase()


def _shares(frame: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Per-year share of registrations whose name starts with / contains each letter."""
    tot = frame.group_by("anio").agg(t=pl.col("inscritos").sum())

    def share(mask: pl.Expr, letter: str) -> pl.DataFrame:
        s = frame.filter(mask).group_by("anio").agg(v=pl.col("inscritos").sum())
        return tot.join(s, on="anio", how="left").fill_null(0).select("anio", letra=pl.lit(letter), porcentaje=100 * pl.col("v") / pl.col("t")).sort("anio")

    starts = pl.concat([share(LOW.str.starts_with(L), L) for L in LETTERS])
    anywhere = pl.concat([share(LOW.str.contains(L, literal=True), L) for L in LETTERS])
    return starts, anywhere


def _top(frame: pl.DataFrame, letter: str, mode: str, n: int = 8) -> pl.DataFrame:
    f = frame.group_by("nombre").agg(pl.col("inscritos").sum())
    mask = LOW.str.starts_with(letter) if mode == "start" else LOW.str.contains(letter, literal=True)
    return f.filter(mask).sort("inscritos", descending=True).head(n)


def _top_names(frame: pl.DataFrame, letter: str, mode: str, n: int = 8) -> list[str]:
    return _top(frame, letter, mode, n)["nombre"].to_list()


def _clouds(frame: pl.DataFrame, mode: str) -> list[dict]:
    return [{"title": f"Letra {L}", "spec": charts.cloud(_top(frame, L, mode, 30), "nombre", "inscritos", width=300, height=200, max_words=30)} for L in LETTERS]


def _peak(df: pl.DataFrame, letter: str) -> tuple[int, float]:
    s = df.filter(pl.col("letra") == letter)
    r = s.row(s["porcentaje"].arg_max(), named=True)
    return int(r["anio"]), float(r["porcentaje"])


def _at(df: pl.DataFrame, letter: str, anio: int) -> float:
    return float(df.filter((pl.col("letra") == letter) & (pl.col("anio") == anio))["porcentaje"][0])


def _letter_items(df: pl.DataFrame, frame: pl.DataFrame, mode: str) -> dict:
    rows = []
    for L in LETTERS:
        y, v = _peak(df, L)
        rows.append(
            {
                "label": f"Letra {L}",
                "value": f"{stats.pct(_at(df, L, 1920), 2)} en 1920, {stats.pct(_at(df, L, 2021), 2)} en 2021, máximo {stats.pct(v, 2)} en {y}. Más frecuentes: {', '.join(_top_names(frame, L, mode))}",
            }
        )
    return {"title": "Cifras por letra", "rows": rows}


def build(d: Data) -> list[dict]:
    frame = d.names.select("anio", "nombre", "sexo", "inscritos")
    starts, anywhere = _shares(frame)
    sections = [
        {
            "heading": None,
            "body": [
                "La k, la w y la y son letras marginales en el castellano. Casi no hay palabras patrimoniales que empiecen con ellas, "
                "y sin embargo en los nombres de pila chilenos han tenido una vida propia. Miramos las inscripciones del Registro Civil "
                "entre 1920 y 2021 y medimos qué porcentaje de los bebés de cada año recibió un nombre que empieza con cada letra, "
                "y qué porcentaje recibió un nombre que la contiene en cualquier posición. Luego separamos por sexo registral."
            ],
            "chart": None,
        },
        {
            "heading": "Al inicio del nombre",
            "body": ["Porcentaje de los inscritos de cada año cuyo nombre empieza con la letra. Debajo, los nombres más frecuentes que empiezan con cada una, con tamaño según sus inscripciones."],
            "chart": charts.multiline(starts, "porcentaje", "letra", "% de inscripciones del año", y_format=".1f", height=300),
            "charts": _clouds(frame, "start"),
            "items": _letter_items(starts, frame, "start"),
        },
        {
            "heading": "En cualquier posición",
            "body": ["La misma medida, pero contando la letra en cualquier posición del nombre."],
            "chart": charts.multiline(anywhere, "porcentaje", "letra", "% de inscripciones del año", y_format=".1f", height=300),
            "charts": _clouds(frame, "any"),
            "items": _letter_items(anywhere, frame, "any"),
        },
    ]

    parts, rows = [], []
    for sx, label in SEXO.items():
        sub = frame.filter(pl.col("sexo") == sx)
        _, any_sx = _shares(sub)
        any_sx = any_sx.with_columns(serie=pl.col("letra") + f" · {label}")
        parts.append(any_sx)
        for L in LETTERS:
            y, v = _peak(any_sx, L)
            rows.append({"label": f"{label.capitalize()}, letra {L}", "value": f"máximo {stats.pct(v, 2)} en {y}, hoy {stats.pct(_at(any_sx, L, 2021), 2)}. Ejemplos: {', '.join(_top_names(sub, L, 'any', 5))}"})
    by_sex = pl.concat(parts)
    domain = [f"{L} · {lab}" for L in LETTERS for lab in SEXO.values()]
    sections.append(
        {
            "heading": "Mujeres y hombres",
            "body": [
                "La misma medida, nombres que contienen la letra, pero calculada dentro de cada sexo registral. "
                "La y es sobre todo un fenómeno femenino, la w es masculina, y la k se reparte."
            ],
            "chart": charts.multiline(by_sex, "porcentaje", "serie", "% de inscripciones del año", y_format=".1f", height=340, domain=domain),
            "items": {"title": "Cifras por sexo y letra", "rows": rows},
        }
    )

    ky, kv = _peak(starts, "k")
    yy, _ = _peak(anywhere, "y")
    y_names = ", ".join(_top_names(frame, "y", "any", 3))
    w_names = ", ".join(_top_names(frame, "w", "any", 3))
    sections.append(
        {
            "heading": "Lectura",
            "body": [
                f"La y es la más antigua de las tres en Chile, sostenida por nombres como {y_names}; su punto más alto en cualquier posición fue {yy}. "
                f"La k es la llegada tardía: casi inexistente antes de 1960, alcanzó su máximo al inicio del nombre en {ky} con un {stats.pct(kv, 2)} de las inscripciones. "
                f"La w se mantiene rara, empujada casi solo por {w_names}."
            ],
            "chart": None,
        }
    )
    return sections
