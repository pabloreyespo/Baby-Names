"""Discovery: biblical names. Juan, José and María first, then a wider set of Old and New Testament names."""

from __future__ import annotations

import polars as pl

from .. import charts, stats
from ..data import YEAR_MAX, YEAR_MIN, Data

SLUG = "biblicos"
TITLE = "Juan, José y María: el siglo de los nombres bíblicos"
DATE = "2026-09-16"
SUMMARY = "Los tres nombres más inscritos en Chile vienen de la Biblia. Cómo cayeron desde 1920 y qué otros nombres bíblicos tomaron su lugar."

TRIO = ["María", "José", "Juan"]
# ponytail: closed list in the most common Chilean spelling, no variants (Josefa, Juana, Mariana) and no clustering
FEMENINOS = ["María", "Ana", "Isabel", "Marta", "Magdalena", "Sara", "Raquel", "Rebeca", "Ester", "Rut", "Noemí", "Judith", "Débora", "Susana", "Eva", "Lía"]
MASCULINOS = [
    "José", "Juan", "Manuel", "Pedro", "Pablo", "Miguel", "Daniel", "David", "Gabriel", "Rafael", "Andrés", "Felipe", "Tomás", "Simón", "Esteban", "Mateo", "Lucas",
    "Marcos", "Santiago", "Samuel", "Benjamín", "Elías", "Isaac", "Jacob", "Abraham", "Moisés", "Jesús", "Emmanuel", "Adán", "Noé", "Jonás", "Salomón", "Ezequiel",
    "Jeremías", "Isaías", "Zacarías", "Josué", "Joaquín", "Bartolomé",
]
BIBLICOS = FEMENINOS + MASCULINOS
SEXO = {"F": "mujeres", "M": "hombres"}


def _share(frame: pl.DataFrame, mask: pl.Expr, label: str, by: str = "serie") -> pl.DataFrame:
    """Per-year percentage of registrations matching mask, zero-filled."""
    tot = frame.group_by("anio").agg(t=pl.col("inscritos").sum())
    s = frame.filter(mask).group_by("anio").agg(v=pl.col("inscritos").sum())
    return tot.join(s, on="anio", how="left").fill_null(0).select("anio", pl.lit(label).alias(by), porcentaje=100 * pl.col("v") / pl.col("t")).sort("anio")


def _at(df: pl.DataFrame, anio: int) -> float:
    return float(df.filter(pl.col("anio") == anio)["porcentaje"][0])


def _peak(df: pl.DataFrame) -> tuple[int, float]:
    r = df.row(df["porcentaje"].arg_max(), named=True)
    return int(r["anio"]), float(r["porcentaje"])


def _decade_share(frame: pl.DataFrame, lo: int, hi: int) -> pl.DataFrame:
    """Share of each biblical name within all registrations of the window lo..hi."""
    win = frame.filter(pl.col("anio").is_between(lo, hi))
    tot = win["inscritos"].sum()
    return win.filter(pl.col("nombre").is_in(BIBLICOS)).group_by("nombre").agg(porcentaje=100 * pl.col("inscritos").sum() / tot)


def build(d: Data) -> list[dict]:
    frame = d.names.select("anio", "nombre", "sexo", "inscritos")
    name = pl.col("nombre")

    trio = pl.concat([_share(frame, name == n, n) for n in TRIO])
    trio_rows = []
    for n in TRIO:
        s = trio.filter(pl.col("serie") == n)
        y, v = _peak(s)
        trio_rows.append({"label": n, "value": f"{stats.pct(_at(s, YEAR_MIN))} de los inscritos en {YEAR_MIN}, máximo {stats.pct(v)} en {y}, {stats.pct(_at(s, YEAR_MAX), 2)} en {YEAR_MAX}"})

    total = _share(frame, name.is_in(BIBLICOS), "todos")
    by_sex = pl.concat([_share(frame.filter(pl.col("sexo") == sx), name.is_in(BIBLICOS), lab) for sx, lab in SEXO.items()])
    sin_trio = _share(frame, name.is_in(BIBLICOS) & ~name.is_in(TRIO), "sin María, José ni Juan")
    wide = pl.concat([total, by_sex, sin_trio])
    domain = ["todos", *SEXO.values(), "sin María, José ni Juan"]
    y0, v0 = _peak(sin_trio)

    early, late = _decade_share(frame, 1920, 1929), _decade_share(frame, YEAR_MAX - 9, YEAR_MAX)
    change = (
        early.join(late, on="nombre", how="full", suffix="_b", coalesce=True)
        .fill_null(0)
        .with_columns(cambio=pl.col("porcentaje_b") - pl.col("porcentaje"))
        .sort("cambio", descending=True)
    )
    up, down = change.head(10), change.tail(10)
    hoy = late.sort("porcentaje", descending=True).head(15)
    change_rows = [
        {"label": r["nombre"], "value": f"{stats.pct(r['porcentaje'], 2)} en los años veinte, {stats.pct(r['porcentaje_b'], 2)} en {YEAR_MAX - 9}-{YEAR_MAX}"}
        for r in pl.concat([up, down]).iter_rows(named=True)
    ]

    return [
        {
            "heading": None,
            "body": [
                "Los tres nombres más inscritos en Chile desde 1920 son María, José y Juan, y los tres salen de la Biblia. "
                "Partimos por ellos, que era la comparación original de este proyecto, y luego ampliamos la mirada a unos sesenta nombres del "
                "Antiguo y Nuevo Testamento para ver si la caída del trío es una caída de los nombres bíblicos o solo un cambio de favoritos."
            ],
            "chart": None,
        },
        {
            "heading": "El trío",
            "body": ["Porcentaje de los inscritos de cada año que recibió el nombre, sumando ambos sexos registrales. Los tres pierden más de un noventa por ciento de su peso relativo en el siglo."],
            "chart": charts.multiline(trio, "porcentaje", "serie", "% de inscripciones del año", y_format=".1f", height=300, domain=TRIO),
            "items": {"title": "Cifras del trío", "rows": trio_rows},
        },
        {
            "heading": "Todos los nombres bíblicos",
            "body": [
                "La misma medida para el conjunto completo, en total, dentro de cada sexo registral y quitando a María, José y Juan. "
                f"Sin el trío, los nombres bíblicos tocan su punto más alto en {y0} con un {stats.pct(v0)} de las inscripciones: la Biblia no se fue, cambió de nombres."
            ],
            "chart": charts.multiline(wide, "porcentaje", "serie", "% de inscripciones del año", y_format=".1f", height=340, domain=domain),
            "items": {
                "title": "Nombres considerados",
                "rows": [{"label": "Femeninos", "value": ", ".join(FEMENINOS)}, {"label": "Masculinos", "value": ", ".join(MASCULINOS)}],
            },
        },
        {
            "heading": "Quiénes subieron y quiénes bajaron",
            "body": [
                f"Cambio en puntos porcentuales del peso de cada nombre entre los años veinte y {YEAR_MAX - 9}-{YEAR_MAX}. "
                "A la izquierda los diez que más subieron, a la derecha los diez que más bajaron."
            ],
            "chart": None,
            "charts": [
                {"title": "Los que subieron", "spec": charts.bars(up, "cambio", "nombre", x_title="Puntos porcentuales", height=300)},
                {"title": "Los que bajaron", "spec": charts.bars(down.sort("cambio"), "cambio", "nombre", x_title="Puntos porcentuales", height=300)},
            ],
            "items": {"title": "Cifras por nombre", "rows": change_rows},
        },
        {
            "heading": "Los bíblicos de hoy",
            "body": [
                f"Los quince nombres bíblicos más inscritos en {YEAR_MAX - 9}-{YEAR_MAX}, medidos como porcentaje de todas las inscripciones de esos diez años. "
                f"Encabeza {hoy['nombre'][0]} con un {stats.pct(float(hoy['porcentaje'][0]), 2)}, lejos del peso que tenía María a comienzos del siglo."
            ],
            "chart": charts.bars(hoy, "porcentaje", "nombre", x_title="% de inscripciones de la década", height=380),
        },
        {
            "heading": "Lectura",
            "body": [
                f"María pasó de nombrar a {stats.pct(_at(trio.filter(pl.col('serie') == 'María'), YEAR_MIN))} de los bebés en {YEAR_MIN} a menos del uno por ciento. "
                f"El relevo lo tomaron {', '.join(up['nombre'].head(4).to_list())}: nombres igual de bíblicos, casi ausentes de los registros de los años veinte."
            ],
            "chart": None,
        },
    ]
