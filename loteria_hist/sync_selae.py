from __future__ import annotations

import time
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Any

from .db import upsert_sorteo
from .parse_selae import metadata_selae, numeros_rows_from_selae_record
from .repository import fecha_ultimo_sorteo

SELAE_URL = (
    "https://www.loteriasyapuestas.es/servicios/buscadorSorteos"
    "?game_id={game_id}&celebrados=true&fechaInicioInclusiva={ini}&fechaFinInclusiva={fin}"
)

GAME_SELAE_ID = {
    "euromillones": "EMIL",
    "bonoloto": "BONO",
    "primitiva": "LAPR",
}

# Inicio aproximado de cada juego en SELAE (ajustable con --desde).
FECHA_MINIMA_JUEGO = {
    "bonoloto": date(1988, 2, 28),
    "primitiva": date(1985, 10, 17),
    "euromillones": date(2004, 2, 13),
}

# SELAE devuelve como máximo ~80 sorteos por petición (LotoGen).
VENTANA_DIAS_JUEGO = {
    "bonoloto": 60,
    "primitiva": 100,
    "euromillones": 182,
}

MAX_SORTEOS_POR_PETICION = 78

# Días hacia atrás desde el último sorteo guardado (correcciones SELAE).
OVERLAP_DIAS_INCREMENTAL = 14


def _fetch_selae_json(url: str) -> list[dict[str, Any]]:
    """
    Akamai bloquea urllib/curl clásico (403). curl_cffi imita TLS de Chrome.
    """
    try:
        from curl_cffi import requests as cffi_requests
    except ImportError as e:
        raise ImportError(
            "Instala curl_cffi: py -3.14 -m pip install curl_cffi"
        ) from e

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-ES,es;q=0.9",
        "Referer": "https://www.loteriasyapuestas.es/es/resultados",
    }
    last_err: str | None = None
    for attempt in range(5):
        r = cffi_requests.get(
            url,
            impersonate="chrome131",
            timeout=90,
            headers=headers,
        )
        if r.status_code == 200:
            break
        last_err = f"HTTP {r.status_code}: {r.text[:200]}"
        if r.status_code in (429, 500, 502, 503, 504) and attempt < 4:
            time.sleep(2**attempt)
            continue
        raise RuntimeError(f"SELAE {last_err}")
    else:
        raise RuntimeError(f"SELAE {last_err}")

    data = r.json()
    if data is None:
        return []
    if not isinstance(data, list):
        return []
    return data


def _ingestar_registros(
    conn,
    juego: str,
    registros: list[dict[str, Any]],
    *,
    fuente: str,
) -> int:
    n = 0
    for rec in registros:
        fs = str(rec.get("fecha_sorteo", "")).strip()
        fecha_d = datetime.strptime(fs[:19], "%Y-%m-%d %H:%M:%S").date().isoformat()
        nums = numeros_rows_from_selae_record(rec, juego)
        upsert_sorteo(
            conn,
            juego=juego,
            fecha=fecha_d,
            dia_semana=rec.get("dia_semana"),
            numero_sorteo=int(rec["numero"]) if rec.get("numero") is not None else None,
            premio_bote=str(rec["premio_bote"]) if rec.get("premio_bote") is not None else None,
            id_externo=str(rec["id_sorteo"]) if rec.get("id_sorteo") else None,
            metadata=metadata_selae(rec, juego),
            fuente=fuente,
            numeros=nums,
        )
        n += 1
    return n


def _ventana_dias(juego: str, ventana_dias: int | None) -> int:
    return ventana_dias or VENTANA_DIAS_JUEGO.get(juego, 120)


def sincronizar_selae_rango(
    conn,
    juego: str,
    fecha_inicio: date,
    fecha_fin: date,
    *,
    ventana_dias: int | None = None,
    fuente: str = "selae/buscadorSorteos",
    on_progress: Callable[[str], None] | None = None,
) -> int:
    """Descarga sorteos entre fechas (inclusive) avanzando ventanas hacia delante."""
    if juego not in GAME_SELAE_ID:
        raise ValueError(juego)
    if fecha_inicio > fecha_fin:
        return 0

    gid = GAME_SELAE_ID[juego]
    ventana = _ventana_dias(juego, ventana_dias)
    total = 0
    start = fecha_inicio

    while start <= fecha_fin:
        end = min(fecha_fin, start + timedelta(days=ventana))
        url = SELAE_URL.format(
            game_id=gid,
            ini=start.strftime("%Y%m%d"),
            fin=end.strftime("%Y%m%d"),
        )
        msg = f"  {juego}: {start.isoformat()} → {end.isoformat()} …"
        if on_progress:
            on_progress(msg.strip())
        else:
            print(msg, flush=True)

        registros = _fetch_selae_json(url)
        if len(registros) >= MAX_SORTEOS_POR_PETICION:
            mitad = max(1, (end - start).days // 2)
            aviso = (
                f"aviso: {len(registros)} sorteos (límite ~80); "
                f"ventana {mitad} días"
            )
            if on_progress:
                on_progress(aviso)
            else:
                print(f"    {aviso}", flush=True)

        total += _ingestar_registros(conn, juego, registros, fuente=fuente)
        conn.commit()
        start = end + timedelta(days=1)

    return total


def sincronizar_selae_incremental(
    conn,
    juego: str,
    *,
    fecha_fin: date | None = None,
    overlap_dias: int = OVERLAP_DIAS_INCREMENTAL,
    ventana_dias: int | None = None,
    fuente: str = "selae/buscadorSorteos",
    on_progress: Callable[[str], None] | None = None,
) -> int:
    """
    Solo descarga desde el último sorteo en BD (menos solapamiento) hasta hoy.
    Si no hay datos, hace histórico completo hacia atrás.
    """
    fecha_fin = fecha_fin or date.today()
    ult_iso = fecha_ultimo_sorteo(conn, juego)
    if ult_iso is None:
        if on_progress:
            on_progress(f"{juego}: sin datos locales; descarga histórica completa…")
        return sincronizar_selae_retraso(
            conn,
            juego,
            fecha_fin=fecha_fin,
            fecha_min=None,
            ventana_dias=ventana_dias,
            fuente=fuente,
            on_progress=on_progress,
        )

    ult = date.fromisoformat(ult_iso)
    fecha_inicio = max(
        FECHA_MINIMA_JUEGO.get(juego, date(1970, 1, 1)),
        ult - timedelta(days=overlap_dias),
    )
    if fecha_inicio > fecha_fin:
        return 0

    if on_progress:
        on_progress(
            f"{juego}: actualizando {fecha_inicio.isoformat()} → {fecha_fin.isoformat()}"
        )
    return sincronizar_selae_rango(
        conn,
        juego,
        fecha_inicio,
        fecha_fin,
        ventana_dias=ventana_dias,
        fuente=fuente,
        on_progress=on_progress,
    )


def sincronizar_selae_retraso(
    conn,
    juego: str,
    *,
    fecha_fin: date | None = None,
    fecha_min: date | None = None,
    ventana_dias: int | None = None,
    fuente: str = "selae/buscadorSorteos",
    on_progress: Callable[[str], None] | None = None,
) -> int:
    """
    Descarga histórico hacia atrás en ventanas (máx. ~80 sorteos/respuesta).
    Usar para generar la base semilla o sincronización completa manual.
    """
    if juego not in GAME_SELAE_ID:
        raise ValueError(juego)
    gid = GAME_SELAE_ID[juego]
    fecha_fin = fecha_fin or date.today()
    fecha_min = fecha_min or FECHA_MINIMA_JUEGO.get(juego, date(1970, 1, 1))
    ventana = _ventana_dias(juego, ventana_dias)

    total = 0
    end = fecha_fin
    while end >= fecha_min:
        start = max(fecha_min, end - timedelta(days=ventana))
        if start > end:
            break
        url = SELAE_URL.format(
            game_id=gid,
            ini=start.strftime("%Y%m%d"),
            fin=end.strftime("%Y%m%d"),
        )
        msg = f"  {juego}: {start.isoformat()} → {end.isoformat()} …"
        if on_progress:
            on_progress(msg.strip())
        else:
            print(msg, flush=True)

        registros = _fetch_selae_json(url)
        if len(registros) >= MAX_SORTEOS_POR_PETICION:
            mitad = max(1, (end - start).days // 2)
            aviso = (
                f"aviso: {len(registros)} sorteos (límite ~80); "
                f"repite con ventana {mitad}"
            )
            if on_progress:
                on_progress(aviso)
            else:
                print(f"    {aviso}", flush=True)

        total += _ingestar_registros(conn, juego, registros, fuente=fuente)
        conn.commit()
        end = start - timedelta(days=1)
    return total
