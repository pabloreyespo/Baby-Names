"""Discovery: the content of names. How long names are year by year, and which letters
they are made of, as a stream of the nine most common letters plus everything else."""

from __future__ import annotations

import polars as pl

from .. import charts, stats
from ..data import Data, strip_accents

SLUG = "letras"
TITLE = "De qué están hechos los nombres"
DATE = "2026-09-15"
SUMMARY = "El largo promedio de los nombres inscritos año a año, en mujeres y en hombres, y la mezcla de letras que los compone desde 1920."
TOP_LETTERS = 9
OTRAS = "otras"
SEXO = {"F": "mujeres", "M": "hombres"}


def _letters(d: Data) -> pl.DataFrame:
    """One row per distinct name with its ascii letters and its length."""
    return (
        d.names.select("nombre")
        .unique()
        .with_columns(pl.col("nombre").map_elements(lambda s: strip_accents(s).lower(), return_dtype=pl.String).str.extract_all("[a-z]").alias("letras"))
        .with_columns(largo=pl.col("letras").list.len())
    )


def _mean_length(frame: pl.DataFrame, label: str) -> pl.DataFrame:
    return (
        frame.group_by("anio")
        .agg(largo=(pl.col("largo") * pl.col("inscritos")).sum() / pl.col("inscritos").sum())
        .with_columns(serie=pl.lit(label))
        .sort("anio")
    )


def _at(df: pl.DataFrame, col: str, anio: int) -> float:
    return float(df.filter(pl.col("anio") == anio)[col][0])


def build(d: Data) -> list[dict]:
    frame = d.names.join(_letters(d), on="nombre")
    total = _mean_length(frame, "todos")
    by_sex = pl.concat([_mean_length(frame.filter(pl.col("sexo") == sx), lab) for sx, lab in SEXO.items()])
    largo = pl.concat([total, by_sex])

    # Share of each letter among all letters written in the names inscribed that year.
    letters = frame.select("anio", "inscritos", "letras").explode("letras").group_by("anio", "letras").agg(n=pl.col("inscritos").sum())
    ranking = letters.group_by("letras").agg(n=pl.col("n").sum()).sort("n", descending=True)
    top = ranking.head(TOP_LETTERS)["letras"].to_list()
    stream = (
        letters.with_columns(letra=pl.when(pl.col("letras").is_in(top)).then(pl.col("letras")).otherwise(pl.lit(OTRAS)))
        .group_by("anio", "letra")
        .agg(n=pl.col("n").sum())
        .with_columns(porcentaje=100 * pl.col("n") / pl.col("n").sum().over("anio"))
        .sort("anio")
    )
    domain = top + [OTRAS]
    stream = stream.with_columns(orden=pl.col("letra").replace_strict({l: i for i, l in enumerate(domain)}, return_dtype=pl.Int32))

    lengths = frame.group_by("largo").agg(inscritos=pl.col("inscritos").sum()).sort("inscritos", descending=True)
    top_len = lengths.row(0, named=True)
    moved = (
        stream.filter(pl.col("anio").is_in([1920, 2021]))
        .pivot(on="anio", index="letra", values="porcentaje")
        .with_columns(cambio=pl.col("2021") - pl.col("1920"))
        .sort("cambio", descending=True)
    )
    otras = stream.filter(pl.col("letra") == OTRAS)
    a, b = _at(total, "largo", 1920), _at(total, "largo", 2021)
    f21, m21 = _at(by_sex.filter(pl.col("serie") == "mujeres"), "largo", 2021), _at(by_sex.filter(pl.col("serie") == "hombres"), "largo", 2021)
    peak = total.row(total["largo"].arg_max(), named=True)

    return [
        {
            "heading": None,
            "body": [
                f"Cada nombre inscrito es una cadena de letras. Contando solo letras, sin tildes ni guiones, y pesando cada nombre por sus inscripciones, "
                f"el nombre promedio pasó de {stats.dec(a, 2)} letras en 1920 a {stats.dec(b, 2)} en 2021, con su punto más alto en {int(peak['anio'])} "
                f"({stats.dec(peak['largo'], 2)} letras). El largo más frecuente de toda la serie es {top_len['largo']} letras, con {stats.fmt(top_len['inscritos'])} inscripciones."
            ],
            "chart": charts.line(total.select("anio", "largo"), "largo", "Letras por nombre", height=300),
        },
        {
            "heading": "Ellas y ellos",
            "body": [
                f"El mismo promedio calculado dentro de cada sexo registral. En 2021 los nombres femeninos promedian {stats.dec(f21, 2)} letras y los masculinos {stats.dec(m21, 2)}."
            ],
            "chart": charts.multiline(by_sex.select("anio", "serie", "largo"), "largo", "serie", "Letras por nombre", y_format=".1f", height=300, domain=list(SEXO.values())),
            "items": {
                "title": "Largos más usados",
                "rows": [{"label": f"{r['largo']} letras", "value": f"{stats.fmt(r['inscritos'])} inscripciones"} for r in lengths.head(10).iter_rows(named=True)],
            },
        },
        {
            "heading": "La mezcla de letras",
            "body": [
                f"Cada banda es el porcentaje que aporta una letra al total de letras escritas en los nombres de ese año. "
                f"Las {TOP_LETTERS} más usadas de todo el periodo tienen banda propia, el resto del abecedario va junto en {OTRAS}. "
                "El grosor total no significa nada; lo que se lee es cuánto crece o se angosta cada banda.",
                f"La letra más usada es siempre la {top[0]}. La banda que más se angostó es la {moved['letra'][-1]} y la que más creció es la {moved['letra'][0]}. "
                f"La franja {OTRAS}, el resto del abecedario, pasó de {stats.pct(_at(otras, 'porcentaje', 1920), 1)} a {stats.pct(_at(otras, 'porcentaje', 2021), 1)}: las letras poco usadas ganaron terreno.",
            ],
            "chart": charts.stream(stream.select("anio", "letra", "porcentaje", "orden"), "porcentaje", "letra", "% de las letras del año", domain=domain, range_=charts.ramp(TOP_LETTERS) + [charts.INK_SOFT], order="orden", height=360),
            "items": {
                "title": "Cambio de cada banda entre 1920 y 2021",
                "rows": [
                    {"label": f"Letra {r['letra']}" if r["letra"] != OTRAS else "El resto del abecedario", "value": f"{stats.pct(r['1920'], 2)} en 1920, {stats.pct(r['2021'], 2)} en 2021"}
                    for r in moved.iter_rows(named=True)
                ],
            },
        },
    ]
