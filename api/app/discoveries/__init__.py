"""Discovery registry. Each module exposes SLUG, TITLE, DATE, SUMMARY and build(data) -> list[section].

A section is {"heading": str | None, "body": [str], "chart": spec | None} plus optional
"charts": [{"title", "spec"}] (a grid of small charts) and "items": {"title", "rows": [{"label", "value"}]}
(a collapsible list, rendered by the web as <details>).
Add a new discovery by writing one module and listing it in MODULES.
"""

from __future__ import annotations

from types import ModuleType

from . import kwy, letras, unisex, vecinos

MODULES: list[ModuleType] = [vecinos, unisex, kwy, letras]


def listing() -> list[dict]:
    return [{"slug": m.SLUG, "title": m.TITLE, "date": m.DATE, "summary": m.SUMMARY} for m in MODULES]


def get(slug: str) -> ModuleType | None:
    return next((m for m in MODULES if m.SLUG == slug), None)
