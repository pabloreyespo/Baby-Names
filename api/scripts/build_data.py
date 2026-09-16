"""Build data/processed/*.parquet from data/raw, the INE Censo 2024 feature service and the
annual comuna population series of Alamos (2024), https://zenodo.org/records/12807987.

Run from the api/ folder:  uv run python scripts/build_data.py
"""

import json
from pathlib import Path

import httpx
import polars as pl

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"

# INE, Resultados Censo de Poblacion y Vivienda 2024, layer COMUNA_DPA_INDICADORES.
# Found via the official dashboard at censo2024.ine.gob.cl/resultados.
CENSO_URL = "https://services5.arcgis.com/hUyD8u3TeZLKPe4T/arcgis/rest/services/CENSO2024_V2_gdb/FeatureServer/0/query"
CENSO_FIELDS = {
    "CUT": "cut",
    "REGION": "region",
    "PROVINCIA": "provincia",
    "COMUNA": "comuna",
    "Ind_005_TPob": "poblacion",
    "Ind_006_THom": "hombres",
    "Ind_007_TMuj": "mujeres",
    "Ind_0018_Pob_0_14": "pob_0_14",
    "Ind_0020_Pob_15_64": "pob_15_64",
    "Ind_0022_Pob_65_mas": "pob_65_mas",
    "Ind_0016_Pr_Ed": "edad_promedio",
}
# Comunas created after 1952: (creation year, comuna they were split from), both from Wikipedia (es).
# Years before the split with no own figure in the Zenodo series take the parent's population.
ORIGEN = {
    1107: (2004, 1101), 1402: (1970, 1404), 1403: (1970, 1404), 1405: (1957, 1401), 2202: (1979, 2201), 2203: (1979, 2201),
    3302: (1979, 3301), 5103: (1995, 5109), 5604: (1956, 5603), 5605: (1961, 5603), 5803: (1966, 5802), 6102: (1979, 6106),
    6304: (1979, 6310), 7110: (1995, 7106), 7203: (1979, 7202), 8103: (1996, 8101), 8108: (1995, 8101), 8112: (2004, 8110),
    8207: (1979, 8204), 8302: (1979, 8309), 8314: (2004, 8311), 9104: (1981, 9115), 9110: (1981, 9103), 9112: (1995, 9101),
    9117: (1981, 9116), 9121: (2004, 9111), 10106: (1962, 10108), 10107: (1968, 10109), 10304: (1972, 10301), 10306: (1979, 10301),
    10402: (1970, 10401), 10403: (1979, 10101), 10404: (1970, 10401), 11102: (1979, 11202), 11203: (1979, 10208), 11301: (1970, 11401),
    11302: (1979, 11301), 11303: (1979, 11301), 11402: (1979, 11401), 13102: (1981, 13119), 13103: (1981, 13124), 13105: (1981, 13109),
    13106: (1981, 13101), 13107: (1981, 13104), 13108: (1981, 13101), 13112: (1981, 13111), 13113: (1963, 13120), 13115: (1981, 13114),
    13116: (1981, 13109), 13117: (1981, 13124), 13118: (1981, 13120), 13121: (1981, 13130), 13122: (1981, 13120), 13127: (1981, 13101),
    13129: (1981, 13130), 13131: (1981, 13111), 13132: (1981, 13114), 13604: (1994, 13605), 14105: (1964, 14106), 16103: (1995, 16101),
    16207: (1973, 16205),
}
MINOR = {"de", "del", "la", "las", "los", "y", "el"}


def spanish_title(s: str) -> str:
    words = s.strip().lower().split()
    return " ".join(w if (i and w in MINOR) else w.capitalize() for i, w in enumerate(words))


def build_names() -> None:
    df = pl.read_csv(RAW / "nombres2.csv", new_columns=["anio", "nombre", "sexo", "inscritos", "proporcion"])
    df = df.with_columns(
        pl.col("nombre").cast(pl.String).str.strip_chars(),
        pl.col("anio").cast(pl.Int16),
        pl.col("inscritos").cast(pl.Int32),
        pl.col("proporcion").cast(pl.Float64),
    )
    df.write_parquet(OUT / "names.parquet")
    print(f"names: {df.height} rows, {df['anio'].min()}-{df['anio'].max()}")


def build_mortality() -> None:
    frames = []
    for sheet, sexo in (("Hombres", "M"), ("Mujeres", "F")):
        t = pl.read_excel(RAW / "Tabla Mortalidades.xlsx", sheet_name=sheet, engine="openpyxl")
        frames.append(t.select(edad=pl.col("Edad").cast(pl.Int64), vivos=pl.col("vivos").cast(pl.Float64), sexo=pl.lit(sexo), nacimiento=2022 - pl.col("Edad").cast(pl.Int64)))
    m = pl.concat(frames)
    m.write_parquet(OUT / "mortality.parquet")
    print(f"mortality: {m.height} rows")


def fetch_layer(url: str, fields: list[str], cache: Path) -> list[dict]:
    """Every row of an ArcGIS layer, cached as json in data/raw. Paginates past the transfer limit."""
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    rows, offset = [], 0
    while True:
        params = {"where": "1=1", "outFields": ",".join(fields), "returnGeometry": "false", "f": "json", "resultOffset": offset, "resultRecordCount": 1000}
        r = httpx.get(url, params=params, timeout=60)
        r.raise_for_status()
        payload = r.json()
        rows += [f["attributes"] for f in payload["features"]]
        if not payload.get("exceededTransferLimit"):
            break
        offset = len(rows)
    cache.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return rows


def build_comunas() -> None:
    cache = RAW / "censo2024_comunas.json"
    if cache.exists():  # legacy cache holds the raw ArcGIS payload
        payload = json.loads(cache.read_text(encoding="utf-8"))
        rows = [f["attributes"] for f in payload["features"]] if isinstance(payload, dict) else payload
    else:
        rows = fetch_layer(CENSO_URL, list(CENSO_FIELDS), cache)
    c = pl.DataFrame(rows).rename(CENSO_FIELDS).select(list(CENSO_FIELDS.values()))
    c = c.with_columns(pl.col(col).map_elements(spanish_title, return_dtype=pl.String) for col in ("region", "provincia", "comuna")).sort("comuna")
    origen = pl.DataFrame({"cut": list(ORIGEN), "creada": [v[0] for v in ORIGEN.values()], "origen": [v[1] for v in ORIGEN.values()]})
    c = c.join(origen, on="cut", how="left")
    c.write_parquet(OUT / "comunas.parquet")
    print(f"comunas: {c.height} rows, total pop {c['poblacion'].sum():,}")


def build_poblacion() -> None:
    """Annual population per comuna 1920-2024 from the Zenodo series (censuses interpolated, INE
    projections after 2017). Missing years take the parent comuna, then the earliest own figure."""
    p = pl.read_excel(RAW / "poblacion_comunal_1952-2024.xlsx", engine="openpyxl").select(
        cut=pl.col("Comuna").cast(pl.Int64), anio=pl.col("year").cast(pl.Int32), poblacion=pl.col("poblacion").cast(pl.Float64, strict=False)
    )
    wide = pl.DataFrame({"anio": pl.int_range(1920, p["anio"].max() + 1, eager=True, dtype=pl.Int32)}).join(
        p.pivot(on="cut", index="anio", values="poblacion"), on="anio", how="left"
    )
    cuts = wide.columns[1:]
    fuente = pl.DataFrame({c: pl.repeat(int(c), wide.height, eager=True) for c in cuts})
    for cut, (_, parent) in sorted(ORIGEN.items(), key=lambda kv: kv[1][0]):  # parents before children (O'Higgins -> Cochrane -> Chile Chico)
        c, par = str(cut), str(parent)
        fuente = fuente.with_columns(pl.when(wide[c].is_null()).then(fuente[par]).otherwise(fuente[c]).alias(c))
        wide = wide.with_columns(pl.col(c).fill_null(pl.col(par)))
    frames = [
        wide.select(anio="anio", cut=pl.lit(int(c)), poblacion=pl.col(c).fill_null(strategy="backward").round(0).cast(pl.Int64)).with_columns(fuente=fuente[c])
        for c in cuts
    ]
    out = pl.concat(frames)
    assert out["poblacion"].null_count() == 0
    out.write_parquet(OUT / "poblacion.parquet")
    own = out.filter(pl.col("cut") == pl.col("fuente"))
    print(f"poblacion: {out.height} rows, own-series totals 1952 {own.filter(pl.col('anio') == 1952)['poblacion'].sum():,} / 2024 {own.filter(pl.col('anio') == 2024)['poblacion'].sum():,}")


def build_families() -> None:
    """Phonetic clusters and one-edit spelling pairs, precomputed so requests only filter."""
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app.clusters import phonetic_clusters, spelling_pairs

    names = (
        pl.read_parquet(OUT / "names.parquet")
        .group_by("nombre")
        .agg(
            inscritos=pl.col("inscritos").cast(pl.Int64).sum(),
            mujeres=pl.col("inscritos").filter(pl.col("sexo") == "F").cast(pl.Int64).sum(),
            hombres=pl.col("inscritos").filter(pl.col("sexo") == "M").cast(pl.Int64).sum(),
        )
    )
    clusters = phonetic_clusters(names)
    clusters.write_parquet(OUT / "clusters.parquet")
    pairs = spelling_pairs(names)
    pairs.write_parquet(OUT / "pairs.parquet")
    print(f"clusters: {clusters['cluster'].n_unique()} families over {clusters.height} names; pairs: {pairs.height}")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    build_names()
    build_mortality()
    build_comunas()
    build_poblacion()
    build_families()
