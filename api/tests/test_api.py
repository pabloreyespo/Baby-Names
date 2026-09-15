import altair as alt
import polars as pl
import pytest
from fastapi.testclient import TestClient

from app import stats
from app.data import load
from app.main import app

BASE = dict(anio=2001, comuna_nac="Concepción", comuna_actual="Santiago")
SLIDE_IDS = ["portada", "tu-anio", "tiempo", "genero", "vecinos", "vivos", "ciudad-natal", "ciudad-actual", "generacion", "colofon"]


@pytest.fixture(scope="session")
def d():
    return load()


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def test_notebook_reference_numbers(d):
    # Notebook cell 3 printed 195837 distinct names; cell 17 printed 19818922 living.
    assert d.freq.height == 195837
    assert abs(d.names["vivos"].sum() - 19_818_922) < 2_000
    # Notebook cell 19: 7370 names with zero estimated living people.
    assert (d.freq["vivos"] == 0).sum() == 7370


def test_alltime_and_gender(d):
    t = stats.alltime(d, "María")
    assert t["ranking"] == 1 and t["ranking_vivos"] == 1
    assert t["share_f"] > 0.99 and stats.gender_balance(t["share_f"]) == "casi exclusivamente femenino"
    assert stats.alltime(d, "José")["share_f"] < 0.05
    rare = stats.alltime(d, "Teobalda")
    assert rare["ranking"] > 1000 and 0 < rare["vivos"] < rare["inscritos"]


def test_rank_in_year_counts_both_sexes(d):
    r = stats.rank_in_year(d, "María", 1960)
    assert r["ranking"] == 1 and r["mujeres"] > r["hombres"] and r["inscritos"] >= r["mujeres"] + r["hombres"]
    assert stats.rank_in_year(d, "Teobalda", 2021) is None
    assert stats.name_series(d, "María").height == 102


def test_year_in_city(d):
    series = stats.name_series(d, "María")
    stgo, arica = d.comuna("Santiago"), d.comuna("Arica")
    yc = stats.year_in_city(d, series, 1960, arica, stgo)
    assert yc["born_cl"] == int(series.filter(pl.col("anio") == 1960)["inscritos"][0])
    assert 0 < yc["born_city"] < yc["born_cl"]
    assert 0 < yc["alive_city"] <= yc["alive_cl"] <= yc["born_cl"]
    assert yc["band"] == "de 15 a 64 años" and stats.age_band(1950) == "pob_65_mas" and stats.age_band(2015) == "pob_0_14"
    assert yc["censo_nac"] == 2017 and yc["pob_nac"] == 221364 and yc["born_city_iv"][0] >= 1
    assert stats.year_in_city(d, series, 2021, arica, stgo)["censo_nac"] == 2024
    assert d.comunas["poblacion_2017"].sum() == 17_574_003
    assert abs(sum(stats.city_share(d, c) for c in d.comunas.iter_rows(named=True)) - 1) < 1e-9


def test_neighbors_and_family(d):
    nb = stats.neighbors(d, "Ximena")["nombre"].to_list()
    assert "Jimena" in nb and "Ximena" not in nb
    fam = stats.family(d, "Christopher")["nombre"].to_list()
    assert fam[0] in ("Cristopher", "Christopher") and {"Cristofer", "Khristopher", "Kristopher"} <= set(fam)
    assert "Cristobal" not in fam and "Cristóbal" not in fam
    fam_v = stats.family(d, "Valentina")["nombre"].to_list()
    assert "Valentín" not in fam_v and "Valentin" not in fam_v and "Valenthina" in fam_v
    assert "Marina" not in stats.family(d, "María")["nombre"].to_list()
    assert stats.family(d, "Alexander").filter(pl.col("nombre").is_in(["Aleksander", "Alexsander"])).height == 2


def test_compound_and_accent_variants_share_family(d):
    fam = stats.family(d, "Mariajose")
    names = set(fam["nombre"])
    assert {"María-José", "Maríajosé", "Maria-Jose", "Marijose"} <= names
    assert fam.filter(pl.col("nombre") == "María-José")["exacto"][0]
    assert fam.filter(pl.col("nombre") == "Mariajosse")["exacto"][0]  # double s collapses, same sound


def test_family_endpoint(client):
    r = client.get("/api/names/family", params={"nombre": "maria jose"})
    assert r.status_code == 404  # spaces do not exist in the registry; hyphen or joined forms do
    r = client.get("/api/names/family", params={"nombre": "Mariajose"})
    assert r.status_code == 200
    body = r.json()
    assert body["formas"][0]["inscritos"] >= body["formas"][-1]["inscritos"]
    assert any(f["nombre"] == "María-José" for f in body["formas"])
    assert client.get("/api/names/family", params={"nombre": "x<y"}).status_code == 422


def test_pairs_are_distance_one(d):
    from rapidfuzz.distance import DamerauLevenshtein

    p = d.pairs
    assert p.height > 10_000
    sample = p.sample(200, seed=1)
    assert all(DamerauLevenshtein.distance(a.lower(), b.lower()) == 1 for a, b in zip(sample["nombre"], sample["nombre_b"]))
    assert (p["nombre"] < p["nombre_b"]).all()
    assert p.filter((pl.col("nombre") == "Jimena") & (pl.col("nombre_b") == "Ximena")).height == 1


def test_name_normalization(d):
    assert d.canonical("  maría ") == "María"
    assert d.canonical("MARIA") == "María"
    assert d.canonical("xqzv") is None


def test_comuna_lookup(d):
    assert d.comuna("concepcion")["poblacion"] == 230375
    assert d.comunas["poblacion"].sum() == 18_480_432


def test_story_slides_are_valid(client):
    r = client.get("/api/story", params=dict(nombre="martina", **BASE))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["nombre"] == "Martina"
    r_ = body["resumen"]
    assert r_["nombre"] == "Martina" and r_["ranking"] > 0 and r_["vivos"] > 0 and 0 <= r_["share_f_pct"] <= 100
    assert r_["comuna_actual"] == "Santiago" and r_["alive_city"] >= 0 and r_["vecinos"] >= 1 and r_["familia"] >= 2
    slides = body["slides"]
    assert [s["id"] for s in slides] == SLIDE_IDS
    for s in slides:
        assert s["title"][0].isupper() or s["title"][0].isdigit()
        assert not any(w.isupper() and len(w) > 3 for w in s["title"].split())  # no full uppercase words
        if "chart" in s:
            alt.Chart.from_dict(s["chart"])  # raises on invalid vega-lite
        for c in s.get("charts", []):
            alt.Chart.from_dict(c["spec"])
    year = next(s for s in slides if s["id"] == "tu-anio")
    assert [c["title"] for c in year["charts"]][:2] == ["Top diez mujeres", "Top diez hombres"]
    natal = next(s for s in slides if s["id"] == "ciudad-natal")
    assert "contándote a ti" in natal["body"][0] and natal["big"][0].isdigit()
    fam = next(s for s in slides if s["id"] == "vecinos")
    assert fam["formas"][0]["nombre"] == "Martina" and len(fam["formas"]) == int(fam["big"].replace(".", ""))


def test_story_unknown_name_and_bad_inputs(client):
    assert client.get("/api/story", params=dict(nombre="xqzv", **BASE)).status_code == 404
    assert client.get("/api/story", params=dict(BASE, nombre="Ana", anio=1800)).status_code == 422
    assert client.get("/api/story", params=dict(nombre="Ana<script>", **BASE)).status_code == 422
    assert client.get("/api/story", params=dict(BASE, nombre="Ana", comuna_nac="Narnia")).status_code == 404


def test_story_name_missing_in_year(client):
    r = client.get("/api/story", params=dict(nombre="Teobalda", anio=2021, comuna_nac="Arica", comuna_actual="Arica"))
    assert r.status_code == 200
    assert r.json()["slides"][0]["big"] == "0"


def test_suggest_and_random(client, d):
    r = client.get("/api/names/suggest", params={"q": "mart"})
    assert "Martina" in r.json()
    assert client.get("/api/names/suggest", params={"q": "<b>"}).json() == []
    top100 = set(d.freq.head(100)["nombre"])
    for _ in range(5):
        assert client.get("/api/names/random").json()["nombre"] in top100


@pytest.mark.parametrize("slug,n_charts,n_small", [("k-w-y", 3, 6), ("vecinos", 3, 12), ("unisex", 5, 0)])
def test_discoveries(client, slug, n_charts, n_small):
    assert {x["slug"] for x in client.get("/api/discoveries").json()} == {"k-w-y", "vecinos", "unisex"}
    r = client.get(f"/api/discoveries/{slug}")
    assert r.status_code == 200, r.text
    secs = r.json()["sections"]
    charts = [s["chart"] for s in secs if s["chart"]]
    small = [c for s in secs for c in s.get("charts", [])]
    assert len(charts) == n_charts and len(small) == n_small
    for c in charts + [c["spec"] for c in small]:
        alt.Chart.from_dict(c)
    assert any(s.get("items") for s in secs)
    for s in secs:
        assert all(p and p[0].isupper() for p in s["body"])
        for it in s.get("items", {}).get("rows", []):
            assert it["label"] and it["value"]
        assert "bando" not in " ".join(s["body"]).lower()
    assert client.get("/api/discoveries/nope").status_code == 404


def test_interval_and_cloud():
    from app import charts

    lo, hi = stats.interval(1000, 0.05)
    assert lo <= 50 <= hi and lo >= 1 and hi - lo < 40
    assert stats.interval(3, 0.001) == (1, 1) and stats.rango(1, 1) == "1" and stats.rango(1, 7) == "entre 1 y 7"
    df = pl.DataFrame({"nombre": ["Pamela", "Pamelah", "Pámela"], "inscritos": [50000, 30, 10]})
    spec = charts.cloud(df, "nombre", "inscritos", highlight="Pamela")
    alt.Chart.from_dict(spec)
    pts = spec["datasets"][spec["data"]["name"]]
    assert len(pts) == 3 and pts[0]["tamano"] > pts[1]["tamano"]
    boxes = charts._cloud_layout([("aaaa", 40), ("bbbb", 40), ("cc", 20)], 600, 300)
    for i, a in enumerate(boxes):
        for b in boxes[i + 1 :]:
            assert not (a["x0"] < b["x1"] and b["x0"] < a["x1"] and a["y0"] < b["y1"] and b["y0"] < a["y1"])


def test_rank_by_sex(d):
    r = stats.rank_by_sex(d, "María", 1960)
    assert r["sexo"] == "F" and r["ranking"] == 1 and r["window"].height == 3 and r["window"]["nombre"][0] == "María"
    r = stats.rank_by_sex(d, "Pamela", 1985)
    assert r["window"].height == 5 and r["window"]["nombre"][2] == "Pamela"
    rk = r["window"]["ranking"].to_list()
    assert rk == sorted(rk) and rk[0] < r["ranking"] < rk[-1]
    assert stats.top_by_sex(d, 2001, "M").height == 10 and stats.rank_by_sex(d, "Teobalda", 2021) is None
