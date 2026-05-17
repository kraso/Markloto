"""Caché en disco del análisis por juego (evita recalcular ~10–30 s por pestaña)."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .analytics import AnalisisJuego
from .paths import default_data_dir
from .repository import ResumenJuego


def _cache_dir() -> Path:
    d = default_data_dir().parent / "cache" / "analisis"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_file(db_path: Path, juego: str) -> Path | None:
    if not db_path.is_file():
        return None
    st = db_path.stat()
    name = f"{juego}_{st.st_mtime_ns}_{st.st_size}.json"
    return _cache_dir() / name


def load(db_path: Path | str, juego: str) -> AnalisisJuego | None:
    path = _cache_file(Path(db_path), juego)
    if path is None or not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        resumen = ResumenJuego(**raw["resumen"])
        frecuencias = {
            k: [(int(a), int(b)) for a, b in v]
            for k, v in raw["frecuencias"].items()
        }
        retrasos = {
            k: [(int(a), int(b)) for a, b in v]
            for k, v in raw["retrasos"].items()
        }
        sugerencia = {k: [int(x) for x in v] for k, v in raw["sugerencia"].items()}
        return AnalisisJuego(
            frecuencias=frecuencias,
            retrasos=retrasos,
            sugerencia=sugerencia,
            resumen=resumen,
        )
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


def save(db_path: Path | str, juego: str, analisis: AnalisisJuego) -> None:
    path = _cache_file(Path(db_path), juego)
    if path is None:
        return
    payload = {
        "frecuencias": analisis.frecuencias,
        "retrasos": analisis.retrasos,
        "sugerencia": analisis.sugerencia,
        "resumen": asdict(analisis.resumen),
    }
    try:
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def invalidate(db_path: Path | str) -> None:
    """Tras sincronizar SELAE o cambiar la base (db_path reservado para uso futuro)."""
    del db_path
    base = _cache_dir()
    if not base.is_dir():
        return
    for p in base.glob("*.json"):
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass
