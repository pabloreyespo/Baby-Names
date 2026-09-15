"""Discovery: name families. Spellings that sound the same, plus names one letter apart.

Everything heavy is precomputed by scripts/build_data.py (see app/clusters.py):
`freq` carries a phonetic key and a family id per name, and `pairs` holds every
unordered pair of names at Damerau-Levenshtein distance 1.
"""

from __future__ import annotations

import polars as pl

from .. import charts, stats
from ..data import Data

SLUG = "vecinos"
TITLE = "Christopher, Cristofer, Khristopher: las familias de un nombre"
DATE = "2026-09-15"
SUMMARY = "Agrupamos los nombres por cómo suenan y por las faltas de una letra. Cuántas formas de escribir un nombre existen en Chile, y cuáles son las familias más grandes."


def build(d: Data) -> list[dict]:
    f = d.freq.select("nombre", "inscritos", "mujeres", "hombres", "fon", "cluster")
    n_names = f.height

    fam = f.group_by("cluster").agg(
        n=pl.len(),
        inscritos=pl.col("inscritos").sum(),
        rep=pl.col("nombre").sort_by("inscritos", descending=True).first(),
        rep_inscritos=pl.col("inscritos").max(),
        miembros=pl.col("nombre").sort_by("inscritos", descending=True).head(8),
    ).with_columns(dominante=100 * pl.col("rep_inscritos") / pl.col("inscritos"))
    multi = fam.filter(pl.col("n") > 1)
    variant_names = int((multi["n"] - 1).sum())
    variant_people = int((multi["inscritos"] - multi["rep_inscritos"]).sum())
    total_people = int(f["inscritos"].sum())

    intro = (
        f"Tomamos los {stats.fmt(n_names)} nombres distintos del Registro Civil y los convertimos a una clave fonética del castellano chileno: "
        "ph y f suenan igual, también c, k y q ante a, o, u; la x inicial suena como j (Ximena, Jimena, Gimena) y en medio como ks (Alexander, Aleksander); "
        "g y j ante e, i; la h es muda; y, ll e i se confunden; v y b también. Sobre esa clave sumamos las faltas de una sola letra, con dos frenos: "
        "una clave rara solo se pega a una veinte veces más común, y nunca cruza de sexo registral, así Valentín y Valentina siguen siendo dos nombres.",
        f"Resultado: {stats.fmt(fam.height)} familias. {stats.fmt(multi.height)} tienen más de una ortografía y reúnen {stats.fmt(variant_names)} formas alternativas. "
        f"{stats.fmt(variant_people)} personas, el {stats.pct(100 * variant_people / total_people)} de todas las inscripciones, llevan una ortografía que no es la dominante de su familia.",
    )

    biggest = multi.sort("n", descending=True).head(15)
    contested = multi.filter(pl.col("inscritos") >= 5000).sort("dominante").head(15)

    def clouds(fams: pl.DataFrame, k: int = 6) -> list[dict]:
        return [
            {
                "title": f"{r['rep']}, {r['n']} formas",
                "spec": charts.cloud(f.filter(pl.col("cluster") == r["cluster"]).select("nombre", "inscritos"), "nombre", "inscritos", highlight=r["rep"], width=300, height=200, max_words=40),
            }
            for r in fams.head(k).iter_rows(named=True)
        ]

    def items(fams: pl.DataFrame, value) -> list[dict]:
        return [{"label": r["rep"], "value": value(r)} for r in fams.iter_rows(named=True)]

    p = d.pairs
    twins = (
        p.with_columns(menor=pl.min_horizontal("inscritos", "inscritos_b"), par=pl.col("nombre") + " / " + pl.col("nombre_b"))
        .join(f.select(nombre=pl.col("nombre"), ca=pl.col("cluster")), on="nombre")
        .join(f.select(nombre_b=pl.col("nombre"), cb=pl.col("cluster")), on="nombre_b")
        .filter(pl.col("ca") != pl.col("cb"))
        .sort("menor", descending=True)
        .head(15)
    )

    return [
        {"heading": None, "body": list(intro), "chart": None},
        {
            "heading": "Las familias con más ortografías",
            "body": ["Nombres importados y largos acumulan variantes: cada th, ph, k o h muda es una oportunidad de escribirlo distinto. Cada nube es una familia; el tamaño de cada forma sigue a sus inscripciones."],
            "chart": charts.bars(biggest.select("rep", "n"), "n", "rep", x_title="Formas de escribir el nombre", height=420),
            "charts": clouds(biggest),
            "items": {"title": "Las quince familias con más formas", "rows": items(biggest, lambda r: f"{r['n']} formas, la dominante concentra el {stats.pct(r['dominante'])}. Otras: {', '.join(r['miembros'][1:6])}")},
        },
        {
            "heading": "Donde ninguna ortografía manda",
            "body": [
                "Familias con al menos cinco mil inscripciones donde la forma más común se queda con la menor parte del total. Son los nombres que la gente escribe como le suena."
            ],
            "chart": charts.bars(contested.select("rep", "dominante"), "dominante", "rep", x_title="% de la familia en la ortografía dominante", height=420),
            "charts": clouds(contested),
            "items": {"title": "Las quince familias más disputadas", "rows": items(contested, lambda r: f"{stats.pct(r['dominante'])} de {stats.fmt(r['inscritos'])} inscripciones. Otras: {', '.join(r['miembros'][1:5])}")},
        },
        {
            "heading": "A una letra, pero otro nombre",
            "body": [
                "Pares de nombres a una sola edición de distancia que quedaron en familias distintas porque suenan diferente o pertenecen a sexos registrales opuestos. "
                "Ordenados por la inscripción del miembro menos común."
            ],
            "chart": charts.bars(twins.select("par", "menor"), "menor", "par", x_title="Inscripciones del menos común", height=420),
            "items": {"title": "Los quince pares", "rows": [{"label": r["par"], "value": f"{stats.fmt(r['inscritos'])} y {stats.fmt(r['inscritos_b'])} inscripciones"} for r in twins.iter_rows(named=True)]},
        },
    ]
