"""Altair spec builders. Every chart goes through the single theme below (see DESIGN.md).

Altair reads polars frames directly (through narwhals); nothing is converted to pandas.
"""

from __future__ import annotations

import altair as alt
import polars as pl

CREAM = "#F5EFE3"
BURGUNDY = "#6B1F2B"
BURGUNDY_DEEP = "#4A121B"
BURGUNDY_SOFT = "#A8626C"
INK_SOFT = "#5C544D"
RULE = "#D9CDB9"
FONT = "Switzer, Helvetica Neue, Arial, sans-serif"
SERIES = [BURGUNDY, BURGUNDY_SOFT, INK_SOFT]


@alt.theme.register("nombres", enable=True)
def _theme() -> alt.theme.ThemeConfig:
    return {
        "config": {
            "background": CREAM,
            "font": FONT,
            "view": {"stroke": None, "continuousWidth": 600, "continuousHeight": 280},
            "axis": {
                "labelColor": INK_SOFT,
                "titleColor": INK_SOFT,
                "labelFont": FONT,
                "titleFont": FONT,
                "labelFontSize": 11,
                "titleFontSize": 12,
                "titleFontWeight": "normal",
                "gridColor": RULE,
                "gridOpacity": 0.5,
                "gridDash": [2, 4],
                "domainColor": RULE,
                "tickColor": RULE,
                "ticks": False,
                "labelPadding": 8,
            },
            "legend": {
                "labelColor": INK_SOFT,
                "titleColor": INK_SOFT,
                "labelFont": FONT,
                "titleFont": FONT,
                "orient": "top",
                "title": None,
                "symbolType": "stroke",
            },
            "range": {"category": SERIES},
            "line": {"color": BURGUNDY, "strokeWidth": 2},
            "bar": {"color": BURGUNDY, "cornerRadiusEnd": 3},
            "rule": {"color": BURGUNDY_DEEP},
            "text": {"font": FONT, "color": INK_SOFT},
        }
    }


def _finish(chart: alt.Chart | alt.LayerChart, height: int) -> dict:
    return chart.properties(width="container", height=height).to_dict()


def year_mark(anio: int, label: str) -> alt.LayerChart:
    d = pl.DataFrame({"anio": [anio], "label": [label]})
    rule = alt.Chart(d).mark_rule(strokeDash=[4, 4], strokeWidth=1.5).encode(x="anio:Q")
    text = alt.Chart(d).mark_text(align="left", dx=6, dy=-6, baseline="top", fontSize=11).encode(x="anio:Q", y=alt.value(0), text="label:N")
    return rule + text


def line(df: pl.DataFrame, y: str, y_title: str, anio: int | None = None, label: str = "", height: int = 280) -> dict:
    base = (
        alt.Chart(df)
        .mark_line(interpolate="monotone")
        .encode(
            x=alt.X("anio:Q", title=None, axis=alt.Axis(format="d", tickCount=6)),
            y=alt.Y(f"{y}:Q", title=y_title, axis=alt.Axis(format="~s")),
            tooltip=[alt.Tooltip("anio:Q", title="Año", format="d"), alt.Tooltip(f"{y}:Q", title=y_title, format=",.0f")],
        )
    )
    chart = base + year_mark(anio, label) if anio else base
    return _finish(chart, height)


def multiline(
    df: pl.DataFrame,
    y: str,
    color: str,
    y_title: str,
    y_format: str = "~s",
    anio: int | None = None,
    label: str = "",
    height: int = 280,
    domain: list[str] | None = None,
) -> dict:
    base = (
        alt.Chart(df)
        .mark_line(interpolate="monotone")
        .encode(
            x=alt.X("anio:Q", title=None, axis=alt.Axis(format="d", tickCount=6)),
            y=alt.Y(f"{y}:Q", title=y_title, axis=alt.Axis(format=y_format)),
            color=alt.Color(f"{color}:N", scale=alt.Scale(domain=domain) if domain else alt.Undefined),
            tooltip=[
                alt.Tooltip("anio:Q", title="Año", format="d"),
                alt.Tooltip(f"{color}:N", title=""),
                alt.Tooltip(f"{y}:Q", title=y_title, format=",.4f" if y_format.endswith("%") else ",.0f"),
            ],
        )
    )
    chart = base + year_mark(anio, label) if anio else base
    return _finish(chart, height)


def stacked_bars(df: pl.DataFrame, x: str, y: str, color: str, highlight: str | None = None, x_title: str = "", height: int = 320) -> dict:
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            y=alt.Y(f"{y}:N", sort=alt.EncodingSortField(field=x, op="sum", order="descending"), title=None, axis=alt.Axis(labelLimit=160)),
            x=alt.X(f"{x}:Q", title=x_title, axis=alt.Axis(format="~s")),
            color=alt.Color(f"{color}:N", scale=alt.Scale(domain=["mujeres", "hombres"], range=[BURGUNDY, INK_SOFT])),
            opacity=alt.condition(alt.datum[y] == highlight, alt.value(1), alt.value(0.55)),
            tooltip=[alt.Tooltip(f"{y}:N", title=""), alt.Tooltip(f"{color}:N", title=""), alt.Tooltip(f"{x}:Q", title=x_title, format=",.0f")],
        )
    )
    return _finish(chart, height)


def bars(df: pl.DataFrame, x: str, y: str, highlight: str | None = None, x_title: str = "", height: int = 320) -> dict:
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            y=alt.Y(f"{y}:N", sort=None, title=None, axis=alt.Axis(labelLimit=160)),
            x=alt.X(f"{x}:Q", title=x_title, axis=alt.Axis(format="~s")),
            color=alt.condition(alt.datum[y] == highlight, alt.value(BURGUNDY_DEEP), alt.value(BURGUNDY_SOFT)),
            tooltip=[alt.Tooltip(f"{y}:N", title=""), alt.Tooltip(f"{x}:Q", title=x_title, format=",.0f")],
        )
    )
    return _finish(chart, height)


def diverging(df: pl.DataFrame, y: str, x: str, x_title: str = "", height: int = 400) -> dict:
    """Horizontal bars of a 0-100 share with a center line at 50."""
    base = alt.Chart(df).encode(y=alt.Y(f"{y}:N", sort=None, title=None, axis=alt.Axis(labelLimit=160)))
    bar = base.mark_bar().encode(
        x=alt.X(f"{x}:Q", title=x_title, scale=alt.Scale(domain=[0, 100])),
        color=alt.condition(alt.datum[x] >= 50, alt.value(BURGUNDY), alt.value(INK_SOFT)),
        tooltip=[alt.Tooltip(f"{y}:N", title=""), alt.Tooltip(f"{x}:Q", title=x_title, format=".1f")],
    )
    mid = alt.Chart(pl.DataFrame({"x": [50]})).mark_rule(strokeDash=[4, 4]).encode(x="x:Q")
    return _finish(bar + mid, height)


def _cloud_layout(words: list[tuple[str, float]], width: int, height: int) -> list[dict]:
    """Greedy spiral placement of word boxes, biggest first. Boxes are approximated from
    character count, so no font metrics are needed; overlaps are avoided on the boxes."""
    import math

    placed: list[dict] = []
    cx, cy = width / 2, height / 2
    for text, size in words:
        w, h = 0.58 * size * len(text), 1.05 * size
        t = 0.0
        while True:
            x, y = cx + 3.5 * t * math.cos(t), cy + 2.2 * t * math.sin(t)
            box = (x - w / 2, y - h / 2, x + w / 2, y + h / 2)
            inside = box[0] >= 0 and box[1] >= 0 and box[2] <= width and box[3] <= height
            clash = any(b["x0"] < box[2] and box[0] < b["x1"] and b["y0"] < box[3] and box[1] < b["y1"] for b in placed)
            if inside and not clash:
                placed.append({"text": text, "size": size, "x": x, "y": y, "x0": box[0], "y0": box[1], "x1": box[2], "y1": box[3]})
                break
            t += 0.35
            if t > 400:  # ponytail: give up on words that do not fit, they are the smallest anyway
                break
    return placed


def cloud(df: pl.DataFrame, text: str, value: str, highlight: str | None = None, width: int = 600, height: int = 320, max_words: int = 60) -> dict:
    """Word cloud: text sized by sqrt of value, positions computed here and drawn as fixed x/y text marks."""
    import math

    rows = df.sort(value, descending=True).head(max_words)
    top = float(rows[value].max()) if rows.height else 1.0
    words = [(str(r[text]), 12 + 44 * math.sqrt(r[value] / top)) for r in rows.iter_rows(named=True)]
    laid = _cloud_layout(words, width, height)
    values = {str(r[text]): int(r[value]) for r in rows.iter_rows(named=True)}
    pts = pl.DataFrame(
        {
            "texto": [p["text"] for p in laid],
            "tamano": [p["size"] for p in laid],
            "x": [p["x"] for p in laid],
            "y": [p["y"] for p in laid],
            "inscritos": [values[p["text"]] for p in laid],
        }
    )
    chart = (
        alt.Chart(pts)
        .mark_text(baseline="middle", align="center", fontWeight="bold")
        .encode(
            x=alt.X("x:Q", axis=None, scale=alt.Scale(domain=[0, width])),
            y=alt.Y("y:Q", axis=None, scale=alt.Scale(domain=[height, 0])),
            text="texto:N",
            size=alt.Size("tamano:Q", scale=None),
            color=alt.condition(alt.datum.texto == highlight, alt.value(BURGUNDY_DEEP), alt.value(BURGUNDY_SOFT)) if highlight else alt.value(BURGUNDY),
            tooltip=[alt.Tooltip("texto:N", title=""), alt.Tooltip("inscritos:Q", title="Inscripciones", format=",.0f")],
        )
    )
    return _finish(chart, height)  # container width; x/y keep the layout domain so the cloud stretches with the card
