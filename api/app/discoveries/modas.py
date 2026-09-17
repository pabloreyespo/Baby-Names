"""Discovery: automatic detection of sudden popularity booms (fads, telenovelas, world cups).

No curated list of famous names: every phonetic family is scanned for a year whose share of
registrations beats its own five year baseline by a wide margin.
"""

from __future__ import annotations

from functools import lru_cache

import polars as pl

from .. import charts, stats
from ..data import YEAR_MAX, Data

SLUG = "modas"
TITLE = "Nombres que despegaron: un detector de modas"
DATE = "2026-09-16"
SUMMARY = "Sin lista previa de nombres famosos: una regla busca años en que un nombre se multiplica sobre su propio pasado, y deja al descubierto teleseries, mundiales y canciones."

MIN_TOTAL = 250  # registrations of the family across the century
MIN_YEAR = 50  # registrations in the boom year
RATIO = 4.0  # times its own baseline
WINDOW = 5  # years of baseline
FIRST = 1930  # first year with a full baseline behind it
FLASH, DURABLE = 0.25, 1.0  # share ten years later, relative to the boom year


@lru_cache(maxsize=1)  # Data is hashable by identity
def _shares(d: Data) -> pl.DataFrame:
    """Per year share of registrations of each phonetic family, on a full year grid."""
    f = d.names.join(d.freq.select("nombre", "cluster"), on="nombre", how="left").group_by("anio", "cluster").agg(pl.col("inscritos").sum())
    tot = f.group_by("anio").agg(t=pl.col("inscritos").sum())
    f = f.join(tot, on="anio").with_columns(share=100 * pl.col("inscritos") / pl.col("t"))
    keep = f.group_by("cluster").agg(s=pl.col("inscritos").sum()).filter(pl.col("s") >= MIN_TOTAL).select("cluster")
    years = pl.DataFrame({"anio": pl.int_range(d.names["anio"].min(), YEAR_MAX + 1, eager=True).cast(pl.Int32)})
    grid = years.join(keep, how="cross")
    return grid.join(f.select("anio", "cluster", "inscritos", "share"), on=["anio", "cluster"], how="left").fill_null(0).sort("cluster", "anio")


@lru_cache(maxsize=1)
def _booms(d: Data) -> pl.DataFrame:
    """One row per family that ever exploded: its biggest jump over its own baseline."""
    head = d.freq.sort("inscritos", descending=True).group_by("cluster").agg(nombre=pl.col("nombre").first(), grafias=pl.col("nombre"))
    g = _shares(d).with_columns(base=pl.col("share").shift(1).rolling_mean(WINDOW, min_samples=1).over("cluster"))
    g = g.with_columns(
        salto=pl.col("share") - pl.col("base"),
        veces=pl.col("share") / (pl.col("base") + 1e-4),
        despues=pl.col("share").shift(-10).over("cluster"),
    )
    hits = g.filter((pl.col("veces") >= RATIO) & (pl.col("inscritos") >= MIN_YEAR) & (pl.col("anio") >= FIRST))
    return (
        hits.sort("salto", descending=True)
        .group_by("cluster")
        .first()
        .join(head, on="cluster")
        .with_columns(resto=pl.col("despues") / pl.col("share"))
        .sort("salto", descending=True)
    )


def _curves(d: Data, clusters: list[int], labels: dict[int, str], desde: int = 1950) -> pl.DataFrame:
    return (
        _shares(d)
        .filter(pl.col("cluster").is_in(clusters) & (pl.col("anio") >= desde))
        .with_columns(nombre=pl.col("cluster").replace_strict(labels, return_dtype=pl.String))
        .select("anio", "nombre", "share")
    )


def _rows(df: pl.DataFrame) -> list[dict]:
    return [
        {
            "label": f"{r['nombre']} ({r['anio']})",
            "value": f"{stats.fmt(r['inscritos'])} inscripciones, {stats.pct(r['share'], 2)} del año frente a {stats.pct(r['base'], 3)} del quinquenio previo, {stats.dec(r['veces'])} veces su base. Grafías: {', '.join(r['grafias'][:5])}",
        }
        for r in df.iter_rows(named=True)
    ]


def _series(df: pl.DataFrame, d: Data, desde: int = 1950) -> tuple[pl.DataFrame, list[str]]:
    labels = {r["cluster"]: r["nombre"] for r in df.iter_rows(named=True)}
    orden = df["nombre"].to_list()
    return _curves(d, df["cluster"].to_list(), labels, desde), orden


def build(d: Data) -> list[dict]:
    b = _booms(d)
    top = b.head(15)
    seis, orden = _series(b.head(6), d)

    cerrados = b.filter(pl.col("resto").is_not_null())
    fugaces = cerrados.filter(pl.col("resto") < FLASH).sort("salto", descending=True).head(4)
    quedaron = cerrados.filter(pl.col("resto") >= DURABLE).sort("salto", descending=True).head(4)
    f_df, f_ord = _series(fugaces, d)
    q_df, q_ord = _series(quedaron, d)

    anios = pl.DataFrame({"anio": pl.int_range(FIRST, YEAR_MAX + 1, eager=True).cast(pl.Int32)})
    por_anio = anios.join(b.group_by("anio").agg(saltos=pl.len()), on="anio", how="left").fill_null(0).sort("anio")
    pico = por_anio.row(por_anio["saltos"].arg_max(), named=True)

    recientes = b.filter(pl.col("anio") >= 2013).sort("veces", descending=True)
    mayor = recientes.sort("salto", descending=True).row(0, named=True)
    r_df, r_ord = _series(recientes.head(6), d, desde=2000)

    return [
        {
            "heading": None,
            "body": [
                "Casi todos los nombres suben y bajan despacio. Unos pocos despegan: un año pesan lo de siempre y al siguiente se multiplican. "
                "Detrás de esos saltos suele haber una teleserie, una canción, una película o un mundial.",
                "Este artículo no parte de una lista de nombres famosos. Parte de una regla aplicada a todo el registro. "
                f"Las grafías se agrupan en familias fonéticas, de modo que Nataly, Nathaly y Natalie cuentan como un solo nombre. Para cada familia con al menos {stats.fmt(MIN_TOTAL)} inscripciones "
                f"en el siglo se calcula su porcentaje de las inscripciones de cada año y se compara con el promedio de los {WINDOW} años anteriores. "
                f"Queda marcado como salto el año que supera {stats.dec(RATIO, 0)} veces ese promedio con al menos {MIN_YEAR} inscripciones. De cada familia se conserva un solo salto, "
                "el mayor medido en puntos porcentuales ganados sobre su propia base.",
                f"El detector encuentra {stats.fmt(b.height)} familias con al menos un salto entre {FIRST} y {YEAR_MAX}. Ningún nombre fue elegido a mano.",
            ],
            "chart": None,
        },
        {
            "heading": "Los quince saltos más grandes",
            "body": [
                "Puntos porcentuales ganados sobre la base del quinquenio anterior. "
                f"Encabeza {top['nombre'][0]} en {top['anio'][0]}, con {stats.pct(float(top['share'][0]), 2)} de las inscripciones del año contra {stats.pct(float(top['base'][0]), 3)} del quinquenio previo."
            ],
            "chart": charts.bars(top, "salto", "nombre", x_title="Puntos porcentuales sobre su base", height=400),
            "items": {"title": "Cifras de cada salto", "rows": _rows(top)},
        },
        {
            "heading": "La forma del despegue",
            "body": [
                "Las seis familias con el salto más grande, como porcentaje de las inscripciones de cada año desde 1950. "
                "La subida ocupa dos o tres años, nunca una década. Lo que viene después distingue dos destinos: caída casi tan rápida como la subida, "
                "o un ascenso que sigue mucho más allá del año del salto."
            ],
            "chart": charts.multiline(seis, "share", "nombre", "% de inscripciones del año", y_format=".1f", height=340, domain=orden),
        },
        {
            "heading": "Fuegos artificiales y nombres que se quedaron",
            "body": [
                "Un despegue no garantiza permanencia. Comparando el peso del año del salto con el de diez años después se separan dos destinos: "
                f"los que caen bajo un cuarto de su punto máximo y los que diez años más tarde valen lo mismo o más. "
                f"De las {stats.fmt(cerrados.height)} familias con diez años de historia posterior, {stats.fmt(cerrados.filter(pl.col('resto') < FLASH).height)} resultaron fugaces y "
                f"{stats.fmt(cerrados.filter(pl.col('resto') >= DURABLE).height)} siguieron creciendo."
            ],
            "chart": None,
            "charts": [
                {"title": "Fugaces", "spec": charts.multiline(f_df, "share", "nombre", "% del año", y_format=".1f", height=260, domain=f_ord)},
                {"title": "Se quedaron", "spec": charts.multiline(q_df, "share", "nombre", "% del año", y_format=".1f", height=260, domain=q_ord)},
            ],
            "items": {
                "title": "Qué pasó diez años después",
                "rows": [
                    {"label": f"{r['nombre']} ({r['anio']})", "value": f"{stats.pct(r['share'], 2)} en el año del salto, {stats.pct(r['despues'], 2)} diez años después"}
                    for r in pl.concat([fugaces, quedaron]).iter_rows(named=True)
                ],
            },
        },
        {
            "heading": "Cuándo despega un nombre",
            "body": [
                "Cantidad de familias que registran su salto en cada año. La línea es plana hasta los años sesenta y se dispara con la televisión: "
                f"el máximo está en {pico['anio']}, con {pico['saltos']} nombres despegando a la vez.",
                "La concentración importa más que el total: cuando varios nombres poco frecuentes despegan el mismo año, el origen compartido suele ser una sola emisión.",
            ],
            "chart": charts.line(por_anio, "saltos", "Familias que despegan ese año", height=280),
        },
        {
            "heading": "Los despegues recientes",
            "body": [
                f"Las seis familias que más se multiplicaron sobre su base entre 2013 y {YEAR_MAX}, como porcentaje de las inscripciones del año desde 2000. "
                "El bloque turco es el más nítido del período: Elif en 2016, Emir en 2017, Melek en 2018 y Naim en 2021 eran nombres casi ausentes del registro chileno "
                "antes de la llegada de las teleseries turcas a la televisión abierta, en 2014.",
                f"El salto reciente más grande en puntos porcentuales es otro: la familia de {mayor['nombre']} en {mayor['anio']}, con {stats.fmt(mayor['inscritos'])} inscripciones. "
                "Es también el caso más ambiguo, porque esa familia fonética junta el mapuche Ailén con el turco Aylin y el detector no puede separarlos.",
            ],
            "chart": charts.multiline(r_df, "share", "nombre", "% de inscripciones del año", y_format=".2f", height=320, domain=r_ord),
            "items": {"title": "Saltos desde 2013", "rows": _rows(recientes)},
        },
        {
            "heading": "Lectura",
            "body": [
                "El detector no sabe nada de cultura popular y aun así devuelve una lista de cultura popular. "
                "Las coincidencias más limpias son las fechadas: Ronaldo en 1998 y Kylian en 2018, los dos años de mundial; Dylan en 1995 y Alanis en 1997, "
                "los años de una serie y de un disco; Evolet en 2009, al año siguiente de la película; Miley en 2010, en plena Hannah Montana; "
                "Melek, Emir y Elif entre 2016 y 2018, con las teleseries turcas al aire.",
                "Ninguna de esas atribuciones sale de los datos: el registro civil solo entrega el salto y su fecha, y la coincidencia queda a cargo de quien lee. "
                "Del registro sí sale el patrón, y es constante: el despegue se arma en dos o tres años, arrastra una decena de grafías nuevas "
                "y en la mayoría de los casos se apaga antes de una década, dejando una generación fechada por su nombre.",
            ],
            "chart": None,
        },
    ]
