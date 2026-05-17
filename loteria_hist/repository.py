from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ResumenJuego:
    juego: str
    total: int
    fecha_min: str | None
    fecha_max: str | None
    fuente: str | None


@dataclass(frozen=True)
class SorteoVista:
    id: int
    fecha: str
    dia_semana: str | None
    premio_bote: str | None
    numeros: dict[str, list[int]]


def fecha_ultimo_sorteo(conn: sqlite3.Connection, juego: str) -> str | None:
    """Fecha ISO del sorteo más reciente del juego, o None si no hay datos."""
    row = conn.execute(
        "SELECT MAX(fecha) FROM sorteos WHERE juego = ?",
        (juego,),
    ).fetchone()
    if not row or row[0] is None:
        return None
    return str(row[0])


def resumen_juego(conn: sqlite3.Connection, juego: str) -> ResumenJuego:
    row = conn.execute(
        """
        SELECT COUNT(*), MIN(fecha), MAX(fecha),
               (SELECT fuente FROM sorteos s2 WHERE s2.juego = ? LIMIT 1)
        FROM sorteos WHERE juego = ?
        """,
        (juego, juego),
    ).fetchone()
    return ResumenJuego(
        juego=juego,
        total=int(row[0]),
        fecha_min=row[1],
        fecha_max=row[2],
        fuente=row[3],
    )


def frecuencias(
    conn: sqlite3.Connection,
    juego: str,
    tipo: str,
) -> list[tuple[int, int]]:
    rows = conn.execute(
        """
        SELECT ns.valor, COUNT(*) AS n
        FROM numeros_sorteo ns
        INNER JOIN sorteos s ON s.id = ns.sorteo_id
        WHERE s.juego = ? AND ns.tipo = ?
        GROUP BY ns.valor
        ORDER BY n DESC, ns.valor ASC
        """,
        (juego, tipo),
    ).fetchall()
    return [(int(r[0]), int(r[1])) for r in rows]


def _sorteos_por_ids(
    conn: sqlite3.Connection,
    ids: list[tuple],
) -> list[SorteoVista]:
    if not ids:
        return []

    id_list = [int(r[0]) for r in ids]
    placeholders = ",".join("?" * len(id_list))
    num_rows = conn.execute(
        f"""
        SELECT sorteo_id, tipo, orden, valor
        FROM numeros_sorteo
        WHERE sorteo_id IN ({placeholders})
        ORDER BY sorteo_id, tipo, orden
        """,
        id_list,
    ).fetchall()

    nums_by_id: dict[int, dict[str, list[int]]] = {int(r[0]): {} for r in ids}
    for sid, tipo, _orden, valor in num_rows:
        bucket = nums_by_id[int(sid)].setdefault(str(tipo), [])
        bucket.append(int(valor))

    out: list[SorteoVista] = []
    for sid, fecha, dia, bote in ids:
        sid_i = int(sid)
        out.append(
            SorteoVista(
                id=sid_i,
                fecha=str(fecha),
                dia_semana=str(dia) if dia else None,
                premio_bote=str(bote) if bote else None,
                numeros=nums_by_id[sid_i],
            )
        )
    return out


def ultimo_sorteo(conn: sqlite3.Connection, juego: str) -> SorteoVista | None:
    rows = ultimos_sorteos(conn, juego, limit=1)
    return rows[0] if rows else None


def sorteos_en_rango(
    conn: sqlite3.Connection,
    juego: str,
    fecha_desde: str,
    fecha_hasta: str | None = None,
) -> list[SorteoVista]:
    """Sorteos entre fechas (inclusive), del más reciente al más antiguo."""
    if fecha_hasta:
        ids = conn.execute(
            """
            SELECT id, fecha, dia_semana, premio_bote
            FROM sorteos
            WHERE juego = ? AND fecha >= ? AND fecha <= ?
            ORDER BY fecha DESC, id DESC
            """,
            (juego, fecha_desde, fecha_hasta),
        ).fetchall()
    else:
        ids = conn.execute(
            """
            SELECT id, fecha, dia_semana, premio_bote
            FROM sorteos
            WHERE juego = ? AND fecha >= ?
            ORDER BY fecha DESC, id DESC
            """,
            (juego, fecha_desde),
        ).fetchall()
    return _sorteos_por_ids(conn, ids)


def frecuencias_en_rango(
    conn: sqlite3.Connection,
    juego: str,
    tipo: str,
    fecha_desde: str,
    fecha_hasta: str | None = None,
) -> list[tuple[int, int]]:
    if fecha_hasta:
        rows = conn.execute(
            """
            SELECT ns.valor, COUNT(*) AS n
            FROM numeros_sorteo ns
            INNER JOIN sorteos s ON s.id = ns.sorteo_id
            WHERE s.juego = ? AND ns.tipo = ?
              AND s.fecha >= ? AND s.fecha <= ?
            GROUP BY ns.valor
            ORDER BY n DESC, ns.valor ASC
            """,
            (juego, tipo, fecha_desde, fecha_hasta),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT ns.valor, COUNT(*) AS n
            FROM numeros_sorteo ns
            INNER JOIN sorteos s ON s.id = ns.sorteo_id
            WHERE s.juego = ? AND ns.tipo = ?
              AND s.fecha >= ?
            GROUP BY ns.valor
            ORDER BY n DESC, ns.valor ASC
            """,
            (juego, tipo, fecha_desde),
        ).fetchall()
    return [(int(r[0]), int(r[1])) for r in rows]


def ultimos_sorteos(
    conn: sqlite3.Connection,
    juego: str,
    limit: int = 25,
) -> list[SorteoVista]:
    ids = conn.execute(
        """
        SELECT id, fecha, dia_semana, premio_bote
        FROM sorteos
        WHERE juego = ?
        ORDER BY fecha DESC
        LIMIT ?
        """,
        (juego, limit),
    ).fetchall()
    return _sorteos_por_ids(conn, ids)


def sorteos_ordenados_asc(
    conn: sqlite3.Connection,
    juego: str,
) -> list[SorteoVista]:
    """Todos los sorteos del juego, del más antiguo al más reciente."""
    ids = conn.execute(
        """
        SELECT id, fecha, dia_semana, premio_bote
        FROM sorteos
        WHERE juego = ?
        ORDER BY fecha ASC, id ASC
        """,
        (juego,),
    ).fetchall()
    return _sorteos_por_ids(conn, ids)


def fechas_indice(conn: sqlite3.Connection, juego: str) -> tuple[int, dict[str, int]]:
    """Número de sorteos e índice 0..n-1 por fecha (orden ascendente)."""
    rows = conn.execute(
        "SELECT fecha FROM sorteos WHERE juego = ? ORDER BY fecha ASC",
        (juego,),
    ).fetchall()
    fechas = [str(r[0]) for r in rows]
    return len(fechas), {f: i for i, f in enumerate(fechas)}


def frecuencias_por_juego(
    conn: sqlite3.Connection,
    juego: str,
) -> dict[str, list[tuple[int, int]]]:
    """Todas las frecuencias del juego en una sola consulta."""
    rows = conn.execute(
        """
        SELECT ns.tipo, ns.valor, COUNT(*) AS n
        FROM numeros_sorteo ns
        INNER JOIN sorteos s ON s.id = ns.sorteo_id
        WHERE s.juego = ?
        GROUP BY ns.tipo, ns.valor
        ORDER BY ns.tipo, n DESC, ns.valor ASC
        """,
        (juego,),
    ).fetchall()
    out: dict[str, list[tuple[int, int]]] = {}
    for tipo, valor, n in rows:
        out.setdefault(str(tipo), []).append((int(valor), int(n)))
    return out


def ultima_fecha_por_valor(
    conn: sqlite3.Connection,
    juego: str,
) -> dict[str, dict[int, str]]:
    rows = conn.execute(
        """
        SELECT ns.tipo, ns.valor, MAX(s.fecha) AS ultima
        FROM numeros_sorteo ns
        INNER JOIN sorteos s ON s.id = ns.sorteo_id
        WHERE s.juego = ?
        GROUP BY ns.tipo, ns.valor
        """,
        (juego,),
    ).fetchall()
    out: dict[str, dict[int, str]] = {}
    for tipo, valor, ultima in rows:
        out.setdefault(str(tipo), {})[int(valor)] = str(ultima)
    return out


def retrasos_desde_ultimas(
    ultima_por_valor: dict[int, str],
    rango: range,
    total: int,
    fecha_idx: dict[str, int],
) -> list[tuple[int, int]]:
    if total == 0:
        return [(n, 0) for n in rango]
    out: list[tuple[int, int]] = []
    for n in rango:
        ultima = ultima_por_valor.get(n)
        if ultima is None:
            out.append((n, total))
        else:
            out.append((n, total - 1 - fecha_idx[ultima]))
    out.sort(key=lambda x: (-x[1], x[0]))
    return out


def retrasos_por_tipo(
    conn: sqlite3.Connection,
    juego: str,
    tipo: str,
    rango: range,
    *,
    fecha_idx: dict[str, int] | None = None,
    total: int | None = None,
) -> list[tuple[int, int]]:
    """(número, sorteos sin salir). Mucho más rápido que cargar todo el historial."""
    if fecha_idx is None or total is None:
        total, fecha_idx = fechas_indice(conn, juego)
    if total == 0:
        return [(n, 0) for n in rango]
    ultimas = ultima_fecha_por_valor(conn, juego).get(tipo, {})
    return retrasos_desde_ultimas(ultimas, rango, total, fecha_idx)


def valores_por_tipo(
    conn: sqlite3.Connection,
    juego: str,
    tipo: str,
) -> list[list[int]]:
    """Historial ordenado por fecha ascendente: lista de sorteos con valores."""
    rows = conn.execute(
        """
        SELECT s.fecha, ns.valor
        FROM sorteos s
        INNER JOIN numeros_sorteo ns ON ns.sorteo_id = s.id
        WHERE s.juego = ? AND ns.tipo = ?
        ORDER BY s.fecha ASC, ns.orden ASC
        """,
        (juego, tipo),
    ).fetchall()
    by_date: dict[str, list[int]] = {}
    for fecha, valor in rows:
        by_date.setdefault(str(fecha), []).append(int(valor))
    return list(by_date.values())
