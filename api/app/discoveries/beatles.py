"""Discovery: the Beatles. Port of the notebook's second question, John, Paul, George and Ringo around 1963."""

from __future__ import annotations

import polars as pl

from .. import charts, stats
from ..data import YEAR_MAX, YEAR_MIN, Data

SLUG = "beatles"
TITLE = "John, Paul, George y Ringo: el efecto Beatles"
DATE = "2026-09-16"
SUMMARY = "Los cuatro nombres de la banda en el Registro Civil chileno, antes y después de 1963. Uno de ellos no existía en Chile hasta que existió la banda."

NOMBRES = ["John", "Paul", "George", "Ringo"]
CORTE = 1963  # último año previo a la beatlemanía, el corte del cuaderno original
ESCALA = 10_000


def _rate(frame: pl.DataFrame, nombre: str) -> pl.DataFrame:
    """Per-year registrations of the name and its rate per 10.000 male registrations, zero-filled."""
    tot = frame.group_by("anio").agg(t=pl.col("inscritos").sum())
    s = frame.filter(pl.col("nombre") == nombre).group_by("anio").agg(inscritos=pl.col("inscritos").sum())
    return (
        tot.join(s, on="anio", how="left")
        .fill_null(0)
        .select("anio", "inscritos", pl.lit(nombre).alias("nombre"), tasa=ESCALA * pl.col("inscritos") / pl.col("t"))
        .sort("anio")
    )


def _diff(serie: pl.DataFrame) -> dict:
    """Difference of mean rates before and after the cut, with the notebook's 95% interval."""
    pre, post = serie.filter(pl.col("anio") <= CORTE)["tasa"], serie.filter(pl.col("anio") > CORTE)["tasa"]
    dif = post.mean() - pre.mean()
    err = 1.96 * (post.std() ** 2 / len(post) + pre.std() ** 2 / len(pre)) ** 0.5
    return {"nombre": serie["nombre"][0], "antes": pre.mean(), "despues": post.mean(), "cambio": dif, "lo": dif - err, "hi": dif + err}


def _at(serie: pl.DataFrame, anio: int) -> int:
    return int(serie.filter(pl.col("anio") == anio)["inscritos"][0])


def build(d: Data) -> list[dict]:
    frame = d.names.filter(pl.col("sexo") == "M").select("anio", "nombre", "inscritos")
    series = {n: _rate(frame, n) for n in NOMBRES}
    juntos = pl.concat(series.values())
    difs = pl.DataFrame([_diff(s) for s in series.values()]).sort("cambio", descending=True)

    cifras, intervalos = [], []
    for n, s in series.items():
        pico = s.row(s["inscritos"].arg_max(), named=True)
        primero = s.filter(pl.col("inscritos") > 0)["anio"].min()
        cifras.append(
            {
                "label": n,
                "value": f"primera inscripción en {primero}, {stats.fmt(s['inscritos'].sum())} en total, máximo de {stats.fmt(pico['inscritos'])} en {pico['anio']}. "
                f"{stats.fmt(_at(s, CORTE))} en {CORTE} y {stats.fmt(_at(s, CORTE + 1))} en {CORTE + 1}",
            }
        )
    for r in difs.iter_rows(named=True):
        intervalos.append(
            {
                "label": r["nombre"],
                "value": f"{stats.dec(r['antes'], 2)} por diez mil antes de {CORTE + 1}, {stats.dec(r['despues'], 2)} después. "
                f"Diferencia {stats.dec(r['cambio'], 2)}, intervalo de 95% entre {stats.dec(r['lo'], 2)} y {stats.dec(r['hi'], 2)}",
            }
        )

    salto_john = _at(series["John"], CORTE + 1) / _at(series["John"], CORTE)
    ringo_1 = int(series["Ringo"].filter(pl.col("inscritos") > 0)["anio"].min())

    return [
        {
            "heading": None,
            "body": [
                f"Segunda pregunta del trabajo original: ¿se nota la banda en los registros chilenos? Los cuatro nombres se miden entre {YEAR_MIN} y {YEAR_MAX} "
                f"dentro de las inscripciones masculinas, con el corte en {CORTE}, el último año antes de que la beatlemanía saliera de Inglaterra."
            ],
            "chart": None,
        },
        {
            "heading": "Los cuatro nombres, año a año",
            "body": [
                "Inscripciones de cada nombre por cada diez mil inscripciones masculinas del año, para que la comparación no dependa del tamaño de cada generación. "
                f"La línea marca {CORTE}. Abajo, las cifras absolutas de cada nombre por separado."
            ],
            "chart": charts.multiline(juntos, "tasa", "nombre", "Por cada 10.000 inscritos", y_format=".1f", anio=CORTE, label=str(CORTE), height=340, domain=NOMBRES),
            "charts": [
                {"title": n, "spec": charts.line(s, "inscritos", "Inscripciones", anio=CORTE, label=str(CORTE), height=200)} for n, s in series.items()
            ],
            "items": {"title": "Cifras por nombre", "rows": cifras},
        },
        {
            "heading": f"Antes y después de {CORTE}",
            "body": [
                f"Diferencia entre la tasa promedio posterior a {CORTE} y la anterior, en inscripciones por cada diez mil. "
                "Las cuatro diferencias son positivas y ninguno de los intervalos de 95% cruza el cero.",
            ],
            "chart": charts.bars(difs, "cambio", "nombre", x_title="Cambio en inscripciones por 10.000", height=260),
            "items": {"title": "Diferencias e intervalos", "rows": intervalos},
        },
        {
            "heading": "Lectura",
            "body": [
                f"John multiplica por {stats.dec(salto_john)} sus inscripciones entre {CORTE} y {CORTE + 1}, de {stats.fmt(_at(series['John'], CORTE))} a {stats.fmt(_at(series['John'], CORTE + 1))} en un solo año. "
                "Ese salto, sin transición, es lo más parecido a una huella de la banda que dejan los datos.",
                "El resto del ascenso es más ambiguo: John, Paul y George son nombres ingleses corrientes y los años sesenta son también los años en que los nombres en inglés entran a Chile, "
                "así que parte del alza se explica por esa moda general y no por el cuarteto.",
                f"Ringo es la excepción limpia. No es un nombre inglés de uso común, es el apodo de un baterista, y su primera inscripción en Chile es de {ringo_1}, "
                "ya con la banda en marcha. Antes de eso, cero.",
            ],
            "chart": None,
        },
    ]
