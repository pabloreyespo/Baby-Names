# Nombres de Chile

Tu nombre en cifras. Ingresas tu primer nombre, año de nacimiento, comuna donde naciste y comuna donde vives, y el sitio arma una historia de diez capítulos con estadísticas del Registro Civil (1920-2021) y de los Censos 2017 y 2024, más una tarjeta para compartir. Una sección de descubrimientos publica análisis sobre el conjunto completo de nombres.

## Correr

```bash
docker compose up --build
```

Abre http://localhost:8080.

Sin Docker: `cd api && uv run uvicorn app.main:app --reload` y en otra terminal `cd web && npm install && npm run dev`, luego http://localhost:5173.

## Datos

- Nombres: Registro Civil de Chile, inscripciones por nombre, sexo y año, 1920-2021 (`data/raw/nombres2.csv`).
- Mortalidad: tablas de vida INE por sexo y edad, base 2022 (`data/raw/Tabla Mortalidades.xlsx`).
- Comunas: Censo de Población y Vivienda 2024, INE, capa `COMUNA_DPA_INDICADORES` del servicio oficial de resultados (https://censo2024.ine.gob.cl/resultados). Se descarga una vez con `api/scripts/build_data.py` y queda cacheada en `data/raw/censo2024_comunas.json`.

Los parquet en `data/processed/` están versionados para que la imagen Docker no necesite red.

## Estructura

`api/` FastAPI + polars + altair + rapidfuzz, `web/` React + Vite + Vega, `DESIGN.md` paleta, tipografía y reglas editoriales, `AGENTS.md` guía para agentes.

## CI/CD

`.github/workflows/ci-cd.yml` runs api tests (80% coverage gate) and web lint + build on every push and PR. Pushes to `master` that pass then deploy over SSH to the GCE VM `baby-names`: the VM pulls `master` into `~/app` and runs `docker compose -f compose.prod.yaml up -d --build`. Configuration lives in the repo settings: variables `VM_HOST` and `SITE_HOST`, secret `VM_SSH_KEY` (private key whose public half is the `github` user in the instance ssh-keys metadata).
