"""Builds the ordered list of chapters for one visitor. Sentence case, Spanish."""

from __future__ import annotations

from typing import Any

import polars as pl

from . import charts, stats
from .data import Data


def slide(id: str, kicker: str, title: str, body: list[str], **extra: Any) -> dict:
    return {"id": id, "kicker": kicker, "title": title, "body": body, **extra}


def _join(names: list[str]) -> str:
    return ", ".join(names[:-1]) + f" y {names[-1]}" if len(names) > 1 else names[0]


def build(d: Data, nombre: str, anio: int, comuna_nac: dict, comuna_act: dict) -> dict:
    year = stats.rank_in_year(d, nombre, anio)
    series = stats.name_series(d, nombre)
    total = stats.alltime(d, nombre)
    coh = stats.cohort(d, nombre, anio)
    yc = stats.year_in_city(d, series, anio, comuna_nac, comuna_act)
    slides: list[dict] = []

    # 1. portada
    if year:
        split = (
            f"{stats.fmt(year['mujeres'])} mujeres y {stats.fmt(year['hombres'])} hombres"
            if year["mujeres"] and year["hombres"]
            else ("todas mujeres" if year["mujeres"] else "todos hombres")
        )
        body = [
            f"En {anio} se inscribieron {stats.fmt(year['inscritos'])} personas con el nombre {nombre} en Chile, {split}. "
            f"Eso lo dejó en el puesto {year['ranking']} entre {stats.fmt(year['n_nombres'])} nombres distintos ese año.",
            f"Dicho de otra forma, {nombre} fue más común que el {stats.pct(year['beats_pct'])} de los nombres inscritos en {anio}. "
            f"Una de cada {stats.fmt(1 / year['share_year'])} personas nacidas ese año recibió tu nombre.",
        ]
        rs0 = stats.rank_by_sex(d, nombre, anio)
        body.append(f"Contando solo {'mujeres' if rs0['sexo'] == 'F' else 'hombres'}, ocupa el puesto {rs0['ranking']} entre {stats.fmt(rs0['n_nombres'])} nombres.")
        big, big_label = f"N° {year['ranking']}", f"Puesto entre los nombres de {anio}"
    else:
        body = [
            f"En {anio} no se inscribió a nadie con el nombre {nombre} en el Registro Civil. "
            "Puede que hayas nacido fuera de Chile, que el nombre se escriba distinto en el registro, o que seas la única persona con ese nombre y año.",
            f"En todo el periodo 1920-2021 el nombre suma {stats.fmt(total['inscritos'])} inscripciones.",
        ]
        big, big_label = "0", "Inscripciones ese año"
    slides.append(slide("portada", f"Edición {anio}", f"{nombre}, {anio}", body, big=big, big_label=big_label, cover=True))

    # 2. los nombres de tu año, por sexo, más tu vecindario de ranking
    SEXO = {"F": "mujeres", "M": "hombres"}
    rs = stats.rank_by_sex(d, nombre, anio)
    tops = {sx: stats.top_by_sex(d, anio, sx) for sx in SEXO}
    in_top = rs is not None and nombre in set(tops[rs["sexo"]]["nombre"])
    body = [
        f"Los diez nombres más inscritos en {anio} para mujeres y para hombres, en rankings separados. "
        + (
            f"{nombre} está en el top diez de {SEXO[rs['sexo']]}."
            if in_top
            else f"{nombre} quedó fuera del top diez de {SEXO[rs['sexo']]}, en el puesto {rs['ranking']} de {stats.fmt(rs['n_nombres'])}."
            if rs
            else f"{nombre} no aparece ese año."
        )
    ]
    charts_ = [
        {"title": f"Top diez {label}", "spec": charts.bars(tops[sx].select("nombre", "inscritos"), "inscritos", "nombre", highlight=nombre, x_title="Inscripciones", height=320)}
        for sx, label in SEXO.items()
    ]
    if rs and not in_top:
        w = rs["window"].with_columns(etiqueta=pl.lit("N° ") + pl.col("ranking").cast(pl.String) + pl.lit(" ") + pl.col("nombre"))
        body.append(f"Tu vecindario en el ranking de {SEXO[rs['sexo']]}: los nombres justo encima y justo debajo del tuyo. Los empates comparten puesto.")
        charts_.append(
            {
                "title": f"Puestos {w['ranking'].min()} a {w['ranking'].max()} de {SEXO[rs['sexo']]}",
                "spec": charts.bars(w.select("etiqueta", "inscritos"), "inscritos", "etiqueta", highlight=f"N° {rs['ranking']} {nombre}", x_title="Inscripciones", height=60 + 36 * w.height),
            }
        )
    slides.append(slide("tu-anio", "La competencia", f"Los nombres de {anio}", body, charts=charts_))

    # 3. a lo largo del tiempo
    peak = series.row(series["inscritos"].arg_max(), named=True)
    first = int(series.filter(pl.col("inscritos") > 0)["anio"].min())
    body = [
        f"El Registro Civil anotó por primera vez a {nombre} en {first}. "
        f"El año de mayor popularidad fue {peak['anio']}, con {stats.fmt(peak['inscritos'])} inscripciones.",
        (
            f"En tu año de nacimiento hubo {stats.fmt(year['inscritos'])}, "
            + ("justo en la cima." if peak["anio"] == anio else f"un {stats.pct(100 * year['inscritos'] / peak['inscritos'])} del máximo histórico.")
        )
        if year
        else "Tu año no registra inscripciones, la línea toca cero ahí.",
    ]
    slides.append(
        slide(
            "tiempo",
            "Un siglo de registros",
            f"{nombre} a lo largo del tiempo",
            body,
            chart=charts.line(series.rename({"inscritos": "inscripciones"}), "inscripciones", "Inscripciones por año", anio=anio, label=f"Tú, {anio}"),
        )
    )

    # 4. mujeres y hombres
    balance = stats.gender_balance(total["share_f"])
    recent = series.filter(pl.col("anio") >= 2000)
    rf, rm = int(recent["mujeres"].sum()), int(recent["hombres"].sum())
    recent_share = rf / (rf + rm) if rf + rm else total["share_f"]
    body = [
        f"Desde 1920, {nombre} se ha inscrito {stats.fmt(total['mujeres'])} veces para mujeres y {stats.fmt(total['hombres'])} para hombres: "
        f"un {stats.pct(100 * total['share_f'])} femenino. Es un nombre {balance}.",
        (
            f"Desde el año 2000 la proporción femenina es {stats.pct(100 * recent_share)}, "
            + ("prácticamente la misma que en todo el siglo." if abs(recent_share - total["share_f"]) < 0.05 else "distinta al promedio histórico: el nombre cambió de sexo dominante o se abrió al otro.")
        )
        if rf + rm
        else "Desde el año 2000 no registra inscripciones.",
    ]
    gender_df = series.unpivot(index="anio", on=["mujeres", "hombres"], variable_name="sexo", value_name="inscripciones")
    slides.append(
        slide(
            "genero",
            "Sexo registral",
            "Mujeres y hombres con tu nombre",
            body,
            big=stats.pct(100 * total["share_f"], 0),
            big_label="De las inscripciones son de mujeres",
            chart=charts.multiline(gender_df, "inscripciones", "sexo", "Inscripciones por año", anio=anio, label=f"Tú, {anio}"),
        )
    )

    # 5. la familia del nombre: mismo sonido, y vecinos a una letra que son otro nombre
    fam = stats.family(d, nombre)
    variants = fam.filter(pl.col("nombre") != nombre)
    fam_total = int(fam["inscritos"].sum())
    head = fam.row(0, named=True)
    nb = stats.neighbors(d, nombre)
    outsiders = nb.filter(~pl.col("nombre").is_in(fam["nombre"].to_list()))
    if variants.is_empty():
        body = [
            f"Agrupamos los {stats.fmt(total['n_nombres'])} nombres del registro por cómo suenan en castellano chileno (ph y f, k, c y q, x, j y g, h muda, y, ll e i, v y b) "
            f"y sumamos las faltas de una letra sobre esa pronunciación. {nombre} no tiene otra forma de escribirse en Chile: es una familia de un solo miembro."
        ]
    else:
        exact = variants.filter(pl.col("exacto")).height
        dominant = head["nombre"] == nombre
        body = [
            f"Agrupamos los nombres por cómo suenan en castellano chileno (acentos, guiones, nombres compuestos pegados, ph y f, c, k y q, x, j y g, h muda, y, ll e i, v y b) "
            f"y sumamos las faltas de ortografía de una letra sobre esa pronunciación. "
            f"{nombre} tiene {stats.fmt(variants.height)} {'otra forma' if variants.height == 1 else 'otras formas'} de escribirse en el registro: "
            f"{stats.fmt(exact)} que suenan exactamente igual y {stats.fmt(variants.height - exact)} que son faltas de una letra. La nube muestra cada forma con su tamaño según inscripciones; la lista completa está abajo.",
            (
                f"Tu ortografía es la dominante: el {stats.pct(100 * total['inscritos'] / fam_total)} de las {stats.fmt(fam_total)} inscripciones de la familia."
                if dominant
                else f"La forma dominante es {head['nombre']}, con {stats.fmt(head['inscritos'])} inscripciones; {nombre} es el {stats.pct(100 * total['inscritos'] / fam_total)} de la familia."
            ),
        ]
    if not outsiders.is_empty():
        onames = outsiders["nombre"].to_list()
        body.append(
            f"A una sola letra de distancia también están {_join(onames[:5])}{'...' if len(onames) > 5 else ''}, "
            "pero suenan distinto o pertenecen al otro sexo registral, así que los contamos como otros nombres, no como variantes."
        )
    slides.append(
        slide(
            "vecinos",
            "Mismo nombre, otras letras",
            "La familia de tu nombre",
            body,
            big=stats.fmt(fam.height),
            big_label="Formas de escribir tu nombre en el registro",
            chart=charts.cloud(fam.select("nombre", "inscritos"), "nombre", "inscritos", highlight=nombre),
            formas=fam.select("nombre", "inscritos", "exacto").to_dicts(),
        )
    )

    # 6. los que siguen vivos
    vivos_pct = 100 * total["vivos"] / total["inscritos"] if total["inscritos"] else 0
    body = [
        f"Con las tablas de mortalidad del INE estimamos que, de las {stats.fmt(total['inscritos'])} personas inscritas como {nombre} desde 1920, "
        f"hoy siguen vivas unas {stats.fmt(total['vivos'])} ({stats.pct(vivos_pct)}): el {stats.pct(100 - vivos_pct)} de tus tocayos ya no están.",
        f"Entre los nombres que aún tienen portadores vivos, {nombre} ocupa el puesto {stats.fmt(total['ranking_vivos'])} de {stats.fmt(total['n_nombres'])}. "
        f"Aproximadamente una de cada {stats.fmt(1 / total['share_living']) if total['share_living'] else '∞'} personas vivas en Chile lleva tu nombre.",
    ]
    vivos_df = series.unpivot(index="anio", on=["inscritos", "vivos"], variable_name="serie", value_name="personas").with_columns(
        pl.col("serie").replace({"inscritos": "Inscritos", "vivos": "Vivos hoy"})
    )
    slides.append(
        slide(
            "vivos",
            "Corrección por mortalidad",
            "Los que siguen aquí",
            body,
            big=stats.fmt(total["vivos"]),
            big_label="Personas vivas con tu nombre, estimación",
            chart=charts.multiline(vivos_df, "personas", "serie", "Personas", anio=anio, label=f"Tú, {anio}"),
        )
    )

    # 7. ciudad natal
    iv_nac = stats.interval(total["vivos"], stats.city_share(d, comuna_nac))
    body = [
        f"{comuna_nac['comuna']} ({comuna_nac['region']}) tenía {stats.fmt(yc['pob_nac'])} habitantes según el Censo {yc['censo_nac']}, el más cercano a tu año de nacimiento, "
        f"el {stats.pct(100 * yc['share_nac'], 2)} del país. "
        f"En {anio} se inscribieron {stats.fmt(yc['born_cl'])} {nombre} en todo Chile; si se repartieron como la población, "
        + f"{stats.rango(*yc['born_city_iv'])} {nombre} nacieron en {comuna_nac['comuna']} ese mismo año, contándote a ti.",
        f"Sumando todas las edades, hoy vivirían en {comuna_nac['comuna']} {stats.rango(*iv_nac)} personas llamadas {nombre}. "
        "El registro de nombres no tiene geografía, así que ambas cifras son estimaciones con un intervalo del 90%, y el mínimo siempre es 1: tú.",
    ]
    slides.append(
        slide(
            "ciudad-natal",
            "Donde naciste",
            comuna_nac["comuna"],
            body,
            big=stats.big_rango(*yc["born_city_iv"]),
            big_label=f"{nombre} nacidos en {comuna_nac['comuna']} en {anio}, estimación",
        )
    )

    # 8. donde vives
    iv_act = stats.interval(total["vivos"], stats.city_share(d, comuna_act))
    same = comuna_act["comuna"] == comuna_nac["comuna"]
    cohort_line = (
        f"De los {stats.fmt(yc['born_cl'])} {nombre} inscritos en {anio}, estimamos que hoy viven {stats.fmt(yc['alive_cl'])}. "
        f"{comuna_act['comuna']} concentra el {stats.pct(100 * yc['share_act'], 2)} de los chilenos {yc['band']}, "
        + f"así que {stats.rango(*yc['alive_city_iv'])} {nombre} de tu edad vivirían hoy en tu comuna, contándote a ti."
    )
    if same:
        body = [
            f"Sigues viviendo donde naciste. {comuna_act['comuna']} creció o se movió, pero tú te quedaste. "
            f"El {stats.pct(100 * comuna_act['pob_65_mas'] / comuna_act['poblacion'])} de sus habitantes tiene 65 años o más, y el {stats.pct(100 * comuna_act['pob_0_14'] / comuna_act['poblacion'])} menos de 15.",
            cohort_line,
        ]
        comp = pl.DataFrame({"comuna": [comuna_act["comuna"]], "habitantes": [int(comuna_act["poblacion"])]})
    else:
        ratio = comuna_act["poblacion"] / comuna_nac["poblacion"]
        body = [
            f"Hoy vives en {comuna_act['comuna']} ({comuna_act['region']}), con {stats.fmt(comuna_act['poblacion'])} habitantes, "
            + (f"{stats.dec(ratio)} veces más que {comuna_nac['comuna']}. " if ratio >= 1 else f"un {stats.pct(100 * ratio)} de la población de {comuna_nac['comuna']}. ")
            + f"Sumando todas las edades, estimamos {stats.rango(*iv_act)} personas con tu nombre aquí, contra {stats.big_rango(*iv_nac)} en {comuna_nac['comuna']}.",
            cohort_line,
        ]
        comp = pl.DataFrame({"comuna": [comuna_nac["comuna"], comuna_act["comuna"]], "habitantes": [int(comuna_nac["poblacion"]), int(comuna_act["poblacion"])]})
    slides.append(
        slide(
            "ciudad-actual",
            "Donde vives",
            comuna_act["comuna"],
            body,
            big=stats.big_rango(*yc["alive_city_iv"]),
            big_label=f"{nombre} de tu edad en {comuna_act['comuna']} hoy, estimación",
            chart=charts.bars(comp, "habitantes", "comuna", highlight=comuna_act["comuna"], x_title="Habitantes, Censo 2024", height=160),
        )
    )

    # 9. generación
    body = [
        f"Entre {coh['lo']} y {coh['hi']} nacieron {stats.fmt(coh['inscritos'])} personas llamadas {nombre}, "
        + (
            f"el {stats.pct(100 * coh['share'], 2)} de todas las inscripciones de esa década. "
            f"Eso lo deja en el puesto {stats.fmt(coh['ranking'])} de {stats.fmt(coh['n_nombres'])} nombres de tu generación."
            if coh["inscritos"]
            else "ninguna en esa década."
        ),
        "En un curso de 30 personas de tu edad, "
        + (f"habría {stats.dec(30 * coh['share'])} con tu nombre." if coh["share"] else "probablemente eras la única persona con tu nombre."),
    ]
    slides.append(
        slide(
            "generacion",
            "Tu generación",
            f"Los nacidos entre {coh['lo']} y {coh['hi']}",
            body,
            big=f"1 de {stats.fmt(1 / coh['share'])}" if coh["share"] else "Único",
            big_label=f"Personas de tu generación se llaman {nombre}",
        )
    )

    # 10. colofón
    body = [
        "Los datos de nombres provienen del Registro Civil de Chile, 1920 a 2021. "
        "La corrección por mortalidad usa las tablas de vida del INE por sexo y edad, con base 2022.",
        "Las poblaciones comunales vienen de los Censos de Población y Vivienda 2017 y 2024 del INE: los nacidos en tu comuna usan el censo más cercano a tu año, los tocayos vivos hoy usan 2024. "
        "Los tocayos por comuna son una estimación: la proporción nacional de personas con tu nombre aplicada a la población de la comuna, o de tu grupo de edad. "
        "Los rangos son intervalos del 90% de un modelo binomial (cada tocayo cae en tu comuna con la probabilidad de su peso poblacional), con mínimo 1 porque tú existes.",
        "La familia de tu nombre agrupa ortografías con la misma clave fonética del castellano chileno, más las claves raras a una edición de una clave mucho más común "
        "(distancia de Damerau-Levenshtein igual a uno, mismo sexo registral dominante, misma inicial). Los vecinos a una letra usan la misma distancia sobre la ortografía. "
        "Los rankings tratan los empates con el mismo puesto. El percentil indica la proporción de nombres distintos que quedan por debajo del tuyo.",
    ]
    slides.append(slide("colofon", "Colofón", "Fuentes y método", body, closing=True))

    for i, s in enumerate(slides, 1):
        s["page"] = i
        s["pages"] = len(slides)

    resumen = {
        "nombre": nombre,
        "anio": anio,
        "ranking": year["ranking"] if year else None,
        "n_nombres": year["n_nombres"] if year else None,
        "vivos": total["vivos"],
        "share_f_pct": round(100 * total["share_f"]),
        "alive_city": yc["alive_city"],
        "comuna_actual": comuna_act["comuna"],
        "born_city": yc["born_city"],
        "comuna_nac": comuna_nac["comuna"],
        "vecinos": nb.height,
        "ranking_sexo": rs["ranking"] if rs else None,
        "sexo": rs["sexo"] if rs else None,
        "familia": fam.height,
    }
    return {"slides": slides, "resumen": resumen}
