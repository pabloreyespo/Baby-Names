# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An interactive personal data story (Spotify Wrapped and Apple product page spirit, light cream theme) about Chilean first names. A visitor enters name, birth year, birth comuna and current comuna and gets a ten-chapter scrollable story covering both sexes plus a shareable summary card. A "descubrimientos" section publishes data analyses. The original homework notebook lives in the `homework` branch; its logic was ported into `api/app`.

Spanish UI, sentence case (never full uppercase), no emojis, no em dashes (see `DESIGN.md`).

## Layout

- `api/` FastAPI + polars + altair (spec generation only, altair reads polars frames directly) + rapidfuzz. Python 3.13 via uv.
  - `app/data.py` loads parquet once (`load()` is lru_cached) and applies the mortality correction; `Data` is hashable by identity so heavy helpers can be lru_cached on it. Sex `I` uses the male life table.
  - `app/stats.py` notebook statistics parameterized by name and year, with female/male splits. `family()` and `neighbors()` only filter precomputed tables. `GET /api/names/family?nombre=` exposes every spelling of a name (used by the home hint and by story chapter five, which lists all forms as chips).
  - `app/fonetica.py` Spanish phonetic key (ph/f, c/k/q, leading x as j, g/j, silent h, ll/y/i, v/b, collapsed doubles). `app/clusters.py` builds families: same key, plus rare keys one edit from a 20x more common head with the same initial and dominant sex (star attachment, never chained). Run by `scripts/build_data.py` into `clusters.parquet` and `pairs.parquet`.
  - `app/story.py` builds the ordered chapter list (rendered stacked, one scroll). Slide ids are asserted in tests. Both sexes are analyzed together with a female/male split; there is no sex input.
  - `app/charts.py` the single altair theme plus `line`, `multiline`, `bars`, `stacked_bars`, `diverging`, `cloud` builders. All charts go through here. `cloud` lays out a word cloud in Python (spiral on character-count boxes) and emits fixed x/y text marks.
  - `app/discoveries/` one module per published analysis (`vecinos` name families from the precomputed clusters and pairs, `unisex`, `kwy`), registered in `MODULES` in `__init__.py`. Each exposes `SLUG, TITLE, DATE, SUMMARY, build(data)`. A section may carry `charts` (grid of small titled specs) and `items` (a collapsible list, `{title, rows: [{label, value}]}`) besides `body` and `chart`; long enumerations go in `items`, never in prose.
  - `scripts/build_data.py` raw csv/xlsx plus the INE Censo 2024 feature service (cached as json in `data/raw`) and the Zenodo annual comuna population series 1952-2024 (https://zenodo.org/records/12807987, `data/raw/poblacion_comunal_1952-2024.xlsx`) -> `data/processed/*.parquet`. `comunas.parquet` carries `poblacion` (2024) plus `creada` and `origen` (creation year and parent cut for the 64 comunas split after 1952, from Wikipedia, in `ORIGEN`). `poblacion.parquet` is the annual series per cut 1920-2024 with `fuente`: before a split the parent's figure is used; before 1952 the earliest figure is repeated. `stats.poblacion_en` reads it and the story copy says when the birth comuna was still part of another one.
- `web/` Vite + React 19 + TypeScript, react-router, react-vega (`VegaEmbed`), html-to-image for the share card. No UI framework, styles in `src/index.css` using tokens from `DESIGN.md`.
- `data/raw/` inputs (names csv, mortality xlsx, Zenodo population xlsx, cached census json). `data/processed/` committed parquet, copied into the api image.
- `compose.yaml` runs `api` (uvicorn :8000, `--reload`) and `web` (vite dev :8080 proxying `/api`), both mounting the source so edits hot reload. `compose.prod.yaml` builds the static image behind Caddy.

## Commands

```bash
# api
cd api; uv run pytest -q --cov=app
cd api; uv run uvicorn app.main:app --reload --port 8000
cd api; uv run python scripts/build_data.py   # rebuild parquet, fetches census once and caches json

# web (dev server proxies /api to :8000)
cd web; npm run dev
cd web; npm run build; npm run lint

# everything
docker compose up --build   # http://localhost:8080
```

Run a single test: `cd api; uv run pytest tests/test_api.py::test_story_slides_are_valid`.

## Conventions

- Chart specs are validated in tests with `alt.Chart.from_dict`; keep new charts in `charts.py` so the theme applies.
- The api reads `NOMBRES_DATA` for the processed folder; unset it locally.
- Rankings use `method="min"` (ties share a rank). Percentiles are "share of distinct names ranked below".
- Namesakes per comuna are estimates (national living share times comuna population) and the copy must say so. They are shown as 90% binomial intervals via `stats.interval`, lower bound 1 (the visitor exists).
- Story chapter two ranks within each registry sex (`stats.by_sex`, `rank_by_sex`); the visitor's neighborhood is ranks N-2..N+2 in their dominant sex.
- Adding a discovery: one file in `api/app/discoveries/`, add to `MODULES`, extend `test_discoveries` if it has charts.
- Changing `fonetica.py` or `clusters.py` requires rerunning `scripts/build_data.py` and committing the new parquet; `tests/test_fonetica.py` pins the sound equivalences.
