from __future__ import annotations

import re
from contextlib import asynccontextmanager

import polars as pl
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import discoveries, stats, story
from .data import YEAR_MAX, YEAR_MIN, load, norm_key

NAME_RE = re.compile(r"^[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ' -]{2,40}$")


@asynccontextmanager
async def lifespan(app: FastAPI):
    load()
    yield


app = FastAPI(title="nombres de chile", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["GET"])


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/comunas")
def comunas() -> list[dict]:
    d = load()
    return d.comunas.select("cut", "comuna", "region", "poblacion").to_dicts()


@app.get("/api/names/suggest")
def suggest(q: str = Query(min_length=1, max_length=40), limit: int = Query(8, ge=1, le=20)) -> list[str]:
    d = load()
    key = q.strip().lower()
    if not NAME_RE.match(key):
        return []
    k = norm_key(key)
    hits = [names for nk, names in d.name_index.items() if nk.startswith(k)]
    flat = [n for group in hits for n in group]
    return d.freq.filter(pl.col("nombre").is_in(flat)).head(limit)["nombre"].to_list()  # freq is sorted by inscritos


@app.get("/api/names/random")
def random_name() -> dict:
    """One of the 100 most common names of the century, to prefill the form."""
    return {"nombre": stats.random_top_name(load())}


@app.get("/api/names/family")
def family(nombre: str = Query(min_length=2, max_length=40)) -> dict:
    """All the ways a name is written in the registry, most common first."""
    if not NAME_RE.match(nombre):
        raise HTTPException(422, "el nombre solo puede tener letras, espacios, guiones o apóstrofes")
    d = load()
    canonical = d.canonical(nombre)
    if canonical is None:
        raise HTTPException(404, f"no encontramos el nombre {nombre.strip()} en el registro 1920-2021")
    fam = stats.family(d, canonical)
    return {"nombre": canonical, "total": int(fam["inscritos"].sum()), "formas": fam.select("nombre", "inscritos", "exacto").to_dicts()}


@app.get("/api/story")
def get_story(
    nombre: str = Query(min_length=2, max_length=40),
    anio: int = Query(ge=YEAR_MIN, le=YEAR_MAX),
    comuna_nac: str = Query(min_length=2, max_length=60),
    comuna_actual: str = Query(min_length=2, max_length=60),
) -> dict:
    if not NAME_RE.match(nombre):
        raise HTTPException(422, "el nombre solo puede tener letras, espacios, guiones o apóstrofes")
    d = load()
    canonical = d.canonical(nombre)
    if canonical is None:
        raise HTTPException(404, f"no encontramos el nombre {nombre.strip()} en el registro 1920-2021")
    c_nac, c_act = d.comuna(comuna_nac), d.comuna(comuna_actual)
    if c_nac is None or c_act is None:
        raise HTTPException(404, "comuna no encontrada en el censo 2024")
    return {"nombre": canonical, "anio": anio, **story.build(d, canonical, anio, c_nac, c_act)}


@app.get("/api/discoveries")
def list_discoveries() -> list[dict]:
    return discoveries.listing()


@app.get("/api/discoveries/{slug}")
def get_discovery(slug: str) -> dict:
    m = discoveries.get(slug)
    if m is None:
        raise HTTPException(404, "descubrimiento no encontrado")
    return {"slug": m.SLUG, "title": m.TITLE, "date": m.DATE, "summary": m.SUMMARY, "sections": m.build(load())}
