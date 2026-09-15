"""Build data/processed/*.parquet from data/raw and the INE Censo 2024 feature service.

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
# INE, Resultados Censo 2017, layer "Cifras Comunales" of the same ArcGIS org. Only totals are kept.
CENSO2017_URL = "https://services5.arcgis.com/hUyD8u3TeZLKPe4T/arcgis/rest/services/Resultados_Censo/FeatureServer/0/query"
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
    c17 = pl.DataFrame(fetch_layer(CENSO2017_URL, ["COMUNA", "TOTAL_PERSONAS"], RAW / "censo2017_comunas.json")).select(
        cut=pl.col("COMUNA").cast(pl.Int64), poblacion_2017=pl.col("TOTAL_PERSONAS").cast(pl.Int64)
    )
    c = c.join(c17, on="cut", how="left")
    missing = c.filter(pl.col("poblacion_2017").is_null())["comuna"].to_list()
    if missing:
        print(f"WARNING comunas without 2017 population: {missing}")
    print(f"comunas 2017: total pop {c['poblacion_2017'].sum():,}")
    c.write_parquet(OUT / "comunas.parquet")
    print(f"comunas: {c.height} rows, total pop {c['poblacion'].sum():,}")


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
    build_families()
