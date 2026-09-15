"""Discovery: unisex names. Which names are registered for both women and men, how many people
carry them, how their balance moved decade by decade, and which ones consolidated into one sex."""

from __future__ import annotations

import polars as pl

from .. import charts, stats
from ..data import Data

SLUG = "unisex"
TITLE = "Los nombres unisex"
DATE = "2026-09-15"
SUMMARY = "Nombres con al menos 100 inscripciones en cada sexo y entre un 10% y un 90% de inscripciones femeninas: cuáles son, cuánta gente los lleva y cómo cambiaron en un siglo."
MIN_PER_SEX = 100
LOW, HIGH = 10, 90
MIN_PERIOD = 500


def _share(frame: pl.DataFrame) -> pl.DataFrame:
    return (
        frame.filter(pl.col("sexo").is_in(["F", "M"]))
        .group_by("nombre")
        .agg(total=pl.col("inscritos").sum(), mujeres=pl.col("inscritos").filter(pl.col("sexo") == "F").sum())
        .with_columns(hombres=pl.col("total") - pl.col("mujeres"), share_f=100 * pl.col("mujeres") / pl.col("total"))
    )


def _items(df: pl.DataFrame) -> list[dict]:
    return [
        {"label": r["nombre"], "value": f"{stats.pct(r['share_f'], 1)} femenino · {stats.fmt(r['mujeres'])} mujeres, {stats.fmt(r['hombres'])} hombres"}
        for r in df.iter_rows(named=True)
    ]


def build(d: Data) -> list[dict]:
    allt = _share(d.names)
    cand = allt.filter((pl.col("mujeres") >= MIN_PER_SEX) & (pl.col("hombres") >= MIN_PER_SEX))
    uni = cand.filter(pl.col("share_f").is_between(LOW, HIGH)).sort("share_f", descending=True)
    both = uni.select("nombre", "mujeres", "hombres").unpivot(index="nombre", variable_name="sexo", value_name="inscritos")
    balanced = uni.with_columns(b=(pl.col("share_f") - 50).abs()).sort("b", "total", descending=[False, True])
    people = int(uni["total"].sum())

    top5 = uni.sort("total", descending=True).head(5)["nombre"].to_list()
    decades = (
        d.names.filter(pl.col("nombre").is_in(top5) & pl.col("sexo").is_in(["F", "M"]))
        .with_columns(anio=(pl.col("anio") // 10 * 10))
        .group_by("nombre", "anio")
        .agg(total=pl.col("inscritos").sum(), mujeres=pl.col("inscritos").filter(pl.col("sexo") == "F").sum())
        .filter(pl.col("total") >= 20)
        .with_columns(share_f=100 * pl.col("mujeres") / pl.col("total"))
        .sort("nombre", "anio")
    )

    early = _share(d.names.filter(pl.col("anio") < 1970)).filter(pl.col("total") >= MIN_PERIOD).select("nombre", share_a=pl.col("share_f"))
    late = _share(d.names.filter(pl.col("anio") >= 2000)).filter(pl.col("total") >= MIN_PERIOD).select("nombre", share_b=pl.col("share_f"))
    moved = early.join(late, on="nombre").with_columns(cambio=pl.col("share_b") - pl.col("share_a"))
    crossed = moved.filter(((pl.col("share_a") - 50) * (pl.col("share_b") - 50)) < 0)
    switch = moved.filter(pl.col("cambio").abs() >= 3).sort(pl.col("cambio").abs(), descending=True).head(15).sort("cambio", descending=True)

    return [
        {
            "heading": None,
            "body": [
                f"Llamamos unisex a un nombre que cumple dos condiciones: al menos {MIN_PER_SEX} inscripciones como mujer y al menos {MIN_PER_SEX} como hombre, "
                f"y una proporción femenina entre {LOW}% y {HIGH}%. De los {stats.fmt(cand.height)} nombres que cumplen la primera, solo {stats.fmt(uni.height)} cumplen también la segunda, "
                f"y entre todos suman {stats.fmt(people)} personas. Son los nombres que en Chile no dejan adivinar el sexo con solo leerlos."
            ],
            "chart": charts.cloud(uni.select("nombre", "total"), "nombre", "total", height=360),
        },
        {
            "heading": "La proporción femenina",
            "body": [
                f"Cada barra es la parte femenina de las inscripciones del nombre. La línea punteada marca el 50%; a la derecha dominan las mujeres, a la izquierda los hombres. "
                f"El más equilibrado es {balanced['nombre'][0]}, con {stats.pct(balanced['share_f'][0], 1)} femenino sobre {stats.fmt(balanced['total'][0])} inscripciones."
            ],
            "chart": charts.diverging(uni.select("nombre", "share_f"), "nombre", "share_f", x_title="% de inscripciones femeninas", height=24 * uni.height + 40),
            "items": {"title": f"Los {uni.height} nombres unisex, del más equilibrado al menos", "rows": _items(balanced)},
        },
        {
            "heading": "Cuántas personas hay detrás",
            "body": ["Inscripciones totales por sexo de los mismos nombres. Un nombre puede repartirse casi al 50% y seguir siendo raro, o inclinarse a un lado y sumar miles."],
            "chart": charts.stacked_bars(both, "inscritos", "nombre", "sexo", x_title="Inscripciones", height=24 * uni.height + 40),
        },
        {
            "heading": "Década a década",
            "body": [
                "Proporción femenina por década de los cinco nombres unisex más inscritos. Solo se dibujan décadas con al menos 20 inscripciones del nombre. "
                "Una línea que sube se feminiza; una que baja se masculiniza."
            ],
            "chart": charts.multiline(decades.select("anio", "nombre", "share_f"), "share_f", "nombre", "% de inscripciones femeninas", y_format=".0f", domain=top5),
        },
        {
            "heading": "Los que se consolidaron",
            "body": [
                f"Comparamos la proporción femenina de cada nombre antes de 1970 con la de 2000 en adelante, exigiendo al menos {MIN_PERIOD} inscripciones en cada periodo. "
                f"De {stats.fmt(moved.height)} nombres presentes en ambos periodos, "
                + (f"{crossed.height} cruzaron el 50%: {', '.join(crossed['nombre'].to_list())}. " if crossed.height else "ninguno cruzó del lado masculino al femenino ni al revés. ")
                + f"Los {stats.fmt(int((moved['cambio'].abs() >= 3).sum()))} movimientos mayores a tres puntos son casi todos consolidaciones: nombres que ya dominaba un sexo y terminaron siendo casi exclusivos. "
                "Un valor positivo significa que el nombre se volvió más femenino."
            ],
            "chart": charts.bars(switch.select("nombre", "cambio"), "cambio", "nombre", x_title="Cambio en puntos porcentuales de inscripciones femeninas", height=24 * switch.height + 40) if switch.height else None,
            "items": {
                "title": "Los quince movimientos mayores",
                "rows": [{"label": r["nombre"], "value": f"{stats.pct(r['share_a'], 0)} femenino antes de 1970, {stats.pct(r['share_b'], 0)} desde 2000"} for r in switch.iter_rows(named=True)],
            },
        },
    ]
