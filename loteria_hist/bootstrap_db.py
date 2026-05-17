"""Inicialización de la base de datos del usuario (esquema + copia semilla)."""

from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

from .db import connect, ensure_performance_indexes, init_schema
from .paths import bundled_seed_db_path, seed_info_path


def _sorteo_count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) FROM sorteos").fetchone()
    return int(row[0]) if row else 0


def read_seed_info() -> dict | None:
    path = seed_info_path()
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _fmt_fecha_iso(iso: str) -> str:
    """YYYY-MM-DD → DD/MM/YYYY."""
    parts = iso.strip()[:10].split("-")
    if len(parts) == 3:
        return f"{parts[2]}/{parts[1]}/{parts[0]}"
    return iso


def _fmt_built_at(raw: str) -> str:
    """ISO datetime → DD/MM/YYYY HH:MM."""
    s = raw.strip().replace("T", " ")[:16]
    if len(s) >= 10 and s[4] == "-":
        date_part, _, time_part = s.partition(" ")
        return f"{_fmt_fecha_iso(date_part)} {time_part}".strip()
    return raw


def texto_historico_embebido() -> str | None:
    """Texto para Acerca de: rango de la base semilla empaquetada."""
    info = read_seed_info()
    if not info:
        if bundled_seed_db_path().is_file():
            return "Incluida en la instalación (sin metadatos de fecha)"
        return None
    partes: list[str] = []
    if info.get("fecha_max"):
        partes.append(f"sorteos hasta {_fmt_fecha_iso(str(info['fecha_max']))}")
    if info.get("built_at"):
        partes.append(f"generada el {_fmt_built_at(str(info['built_at']))}")
    return " · ".join(partes) if partes else None


def texto_bd_local(db_path: Path | str) -> str | None:
    """Último sorteo registrado en la base del usuario."""
    db_path = Path(db_path)
    if not db_path.is_file():
        return "Sin base de datos local"
    conn = connect(db_path)
    try:
        try:
            row = conn.execute("SELECT MAX(fecha), COUNT(*) FROM sorteos").fetchone()
        except sqlite3.OperationalError:
            return "Base vacía (sincroniza con SELAE)"
        if not row or row[0] is None or int(row[1] or 0) == 0:
            return "Sin sorteos (sincroniza con SELAE)"
        return f"sorteos hasta {_fmt_fecha_iso(str(row[0]))} ({int(row[1])} registros)"
    finally:
        conn.close()


def ensure_user_database(db_path: Path | str) -> tuple[bool, str | None]:
    """
    Crea el esquema si hace falta y copia la base semilla si la BD está vacía.

    Returns:
        (semilla_aplicada, mensaje_para_el_usuario)
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    seed_path = bundled_seed_db_path()
    created_new = not db_path.exists()

    if created_new:
        if seed_path.is_file():
            shutil.copy2(seed_path, db_path)
            info = read_seed_info()
            hasta = info.get("fecha_max") if info else None
            msg = (
                f"Base histórica instalada"
                + (f" (sorteos hasta {hasta})" if hasta else "")
                + ". Completando novedades con SELAE…"
            )
            return True, msg
        conn = connect(db_path)
        try:
            init_schema(conn)
            ensure_performance_indexes(conn)
            conn.commit()
        finally:
            conn.close()
        return False, None

    conn = connect(db_path)
    try:
        try:
            n = _sorteo_count(conn)
        except sqlite3.OperationalError:
            init_schema(conn)
            ensure_performance_indexes(conn)
            conn.commit()
            n = _sorteo_count(conn)

        if n == 0 and seed_path.is_file():
            conn.close()
            shutil.copy2(seed_path, db_path)
            info = read_seed_info()
            hasta = info.get("fecha_max") if info else None
            msg = (
                f"Base histórica restaurada"
                + (f" (hasta {hasta})" if hasta else "")
                + ". Completando novedades con SELAE…"
            )
            return True, msg
    finally:
        conn.close()

    return False, None
