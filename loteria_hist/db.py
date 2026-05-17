from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from .paths import schema_sql_path

_SCHEMA_PATH = schema_sql_path()


def connect(db_path: Path | str, *, timeout: float = 30.0) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=timeout)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA cache_size=-80000")
    conn.execute("PRAGMA temp_store=MEMORY")
    try:
        conn.execute("PRAGMA mmap_size=268435456")
    except sqlite3.OperationalError:
        pass
    return conn


def ensure_performance_indexes(conn: sqlite3.Connection) -> None:
    """Índices extra para consultas de frecuencia (BD ya inicializada)."""
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_numeros_tipo_valor "
        "ON numeros_sorteo (tipo, valor)"
    )


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def upsert_sorteo(
    conn: sqlite3.Connection,
    *,
    juego: str,
    fecha: str,
    dia_semana: str | None,
    numero_sorteo: int | None,
    premio_bote: str | None,
    id_externo: str | None,
    metadata: dict[str, Any] | None,
    fuente: str,
    numeros: Iterable[tuple[str, int, int]],
) -> int:
    """Inserta o sustituye un sorteo y sus números. numeros: (tipo, orden, valor)."""
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM sorteos WHERE juego = ? AND fecha = ?",
        (juego, fecha),
    )
    row = cur.fetchone()
    meta_json = json.dumps(metadata, ensure_ascii=False) if metadata else None
    if row:
        sid = int(row[0])
        cur.execute("DELETE FROM numeros_sorteo WHERE sorteo_id = ?", (sid,))
        cur.execute(
            """UPDATE sorteos SET dia_semana = ?, numero_sorteo = ?, premio_bote = ?,
               id_externo = ?, metadata_json = ?, fuente = ?
               WHERE id = ?""",
            (dia_semana, numero_sorteo, premio_bote, id_externo, meta_json, fuente, sid),
        )
    else:
        cur.execute(
            """INSERT INTO sorteos (
                juego, fecha, dia_semana, numero_sorteo, premio_bote,
                id_externo, metadata_json, fuente
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                juego,
                fecha,
                dia_semana,
                numero_sorteo,
                premio_bote,
                id_externo,
                meta_json,
                fuente,
            ),
        )
        sid = int(cur.lastrowid)

    cur.executemany(
        """INSERT INTO numeros_sorteo (sorteo_id, tipo, orden, valor)
           VALUES (?, ?, ?, ?)""",
        [(sid, t, o, v) for t, o, v in numeros],
    )
    return sid


def conteo_por_juego(conn: sqlite3.Connection) -> list[tuple[str, int]]:
    cur = conn.cursor()
    cur.execute(
        "SELECT juego, COUNT(*) FROM sorteos GROUP BY juego ORDER BY juego"
    )
    return [(str(r[0]), int(r[1])) for r in cur.fetchall()]
