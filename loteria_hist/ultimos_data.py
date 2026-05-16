"""Carga de datos para la vista «Últimos sorteos» (escritorio y móvil)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date

from . import repository
from .periodos import RangoPeriodo, rango_periodo
from .repository import SorteoVista


@dataclass(frozen=True)
class DatosUltimosSorteos:
    ultimo: SorteoVista | None
    periodo: RangoPeriodo
    sorteos_periodo: list[SorteoVista]
    frecuencias: dict[str, list[tuple[int, int]]]


def cargar_datos(
    conn: sqlite3.Connection,
    juego: str,
    grupos: list[tuple[str, str]],
    modo_periodo: str,
) -> DatosUltimosSorteos:
    if modo_periodo == "completo":
        resumen = repository.resumen_juego(conn, juego)
        if resumen.fecha_min:
            dmin = date.fromisoformat(resumen.fecha_min)
            dmax = (
                date.fromisoformat(resumen.fecha_max)
                if resumen.fecha_max
                else date.today()
            )
            periodo = rango_periodo("completo", fecha_min=dmin, fecha_max=dmax)
        else:
            periodo = rango_periodo("trimestre")
    else:
        periodo = rango_periodo(modo_periodo)
    ultimo = repository.ultimo_sorteo(conn, juego)
    sorteos = repository.sorteos_en_rango(
        conn, juego, periodo.inicio_iso, periodo.fin_iso
    )
    freq: dict[str, list[tuple[int, int]]] = {}
    for tipo, _kind in grupos:
        freq[tipo] = repository.frecuencias_en_rango(
            conn,
            juego,
            tipo,
            periodo.inicio_iso,
            periodo.fin_iso,
        )
    return DatosUltimosSorteos(
        ultimo=ultimo,
        periodo=periodo,
        sorteos_periodo=sorteos,
        frecuencias=freq,
    )
