"""
Backtesting walk-forward: ¿la heurística frecuencia+probabilidad acierta más que el azar?
Solo usa datos anteriores a cada sorteo (sin mirar el futuro).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from . import analytics, repository


@dataclass(frozen=True)
class TipoValidacion:
    nombre: str
    pool: tuple[int, ...]
    bolas_sorteo: int
    tamano_bloque: int


@dataclass(frozen=True)
class FilaValidacionSorteo:
    fecha: str
    sorteo_id: int
    aciertos: dict[str, int]
    bolas_sorteo: dict[str, int]
    pct_por_tipo: dict[str, float]
    pct_medio: float
    predicho: dict[str, list[int]]
    real: dict[str, list[int]]


@dataclass
class InformeValidacion:
    juego: str
    numeros_marcados: int
    estrellas_marcadas: int | None
    sorteos_evaluados: int
    warmup_omitidos: int
    resumen: dict[str, float] = field(default_factory=dict)
    esperado_azar: dict[str, float] = field(default_factory=dict)
    diferencia_vs_azar: dict[str, float] = field(default_factory=dict)
    media_primer_tercio: float = 0.0
    media_ultimo_tercio: float = 0.0
    media_pct_global: float = 0.0
    esperado_pct_global: float = 0.0
    conclusion: str = ""
    mejores: list[FilaValidacionSorteo] = field(default_factory=list)
    peores: list[FilaValidacionSorteo] = field(default_factory=list)
    ultimos: list[FilaValidacionSorteo] = field(default_factory=list)


def _esperado_aciertos(pool_size: int, bloque: int, bolas_sorteo: int) -> float:
    """Media de aciertos si el sorteo fuera aleatorio (aprox. hipergeométrica)."""
    if pool_size <= 0:
        return 0.0
    return bolas_sorteo * bloque / pool_size


def _esperado_pct(pool_size: int, bloque: int) -> float:
    return 100.0 * bloque / pool_size if pool_size else 0.0


def _tipos_para_juego(
    juego: str,
    numeros_marcados: int,
    estrellas_marcadas: int | None,
) -> list[TipoValidacion]:
    if juego == "euromillones":
        est = estrellas_marcadas if estrellas_marcadas is not None else 2
        return [
            TipoValidacion(
                "principal",
                tuple(range(1, 51)),
                5,
                numeros_marcados,
            ),
            TipoValidacion(
                "estrella",
                tuple(range(1, 13)),
                2,
                est,
            ),
        ]
    return [
        TipoValidacion(
            "principal",
            tuple(range(1, 50)),
            6,
            numeros_marcados,
        ),
        TipoValidacion(
            "complementario",
            tuple(range(1, 50)),
            1,
            1,
        ),
        TipoValidacion(
            "reintegro",
            tuple(range(0, 10)),
            1,
            1,
        ),
    ]


def _actualizar_contadores(
    counts: dict[int, int],
    last_seen: dict[int, int],
    valores: list[int],
    indice: int,
) -> None:
    for v in valores:
        counts[v] = counts.get(v, 0) + 1
        last_seen[v] = indice


def ejecutar_backtest(
    conn: sqlite3.Connection,
    juego: str,
    *,
    numeros_marcados: int,
    estrellas_marcadas: int | None = None,
    warmup: int | None = None,
) -> InformeValidacion:
    """
    Por cada sorteo (tras un periodo inicial), predice el bloque top-N con la
    heurística y mide cuántas bolas ganadoras caían en ese bloque.
    """
    sorteos = repository.sorteos_ordenados_asc(conn, juego)
    tipos = _tipos_para_juego(juego, numeros_marcados, estrellas_marcadas)

    if warmup is None:
        warmup = max(80, numeros_marcados * 15)

    counts: dict[str, dict[int, int]] = {t.nombre: {} for t in tipos}
    last_seen: dict[str, dict[int, int]] = {t.nombre: {} for t in tipos}

    filas: list[FilaValidacionSorteo] = []

    for idx, sorteo in enumerate(sorteos):
        if idx < warmup:
            for t in tipos:
                vals = sorteo.numeros.get(t.nombre, [])
                if vals:
                    _actualizar_contadores(
                        counts[t.nombre],
                        last_seen[t.nombre],
                        vals,
                        idx,
                    )
            continue

        predicho: dict[str, list[int]] = {}
        real: dict[str, list[int]] = {}
        aciertos: dict[str, int] = {}
        bolas_s: dict[str, int] = {}
        pct_tipo: dict[str, float] = {}

        for t in tipos:
            pred = analytics.top_n_desde_contadores(
                counts[t.nombre],
                last_seen[t.nombre],
                idx,
                range(t.pool[0], t.pool[-1] + 1),
                bolas_por_sorteo=t.bolas_sorteo,
                cantidad=t.tamano_bloque,
            )
            drawn = sorteo.numeros.get(t.nombre, [])
            hit = len(set(pred) & set(drawn))
            predicho[t.nombre] = pred
            real[t.nombre] = drawn
            aciertos[t.nombre] = hit
            bolas_s[t.nombre] = len(drawn) if drawn else t.bolas_sorteo
            pct_tipo[t.nombre] = (
                100.0 * hit / len(drawn) if drawn else 0.0
            )

        pcts = list(pct_tipo.values())
        pct_medio = sum(pcts) / len(pcts) if pcts else 0.0

        filas.append(
            FilaValidacionSorteo(
                fecha=sorteo.fecha,
                sorteo_id=sorteo.id,
                aciertos=aciertos,
                bolas_sorteo=bolas_s,
                pct_por_tipo=pct_tipo,
                pct_medio=pct_medio,
                predicho=predicho,
                real=real,
            )
        )

        for t in tipos:
            vals = sorteo.numeros.get(t.nombre, [])
            if vals:
                _actualizar_contadores(
                    counts[t.nombre],
                    last_seen[t.nombre],
                    vals,
                    idx,
                )

    informe = InformeValidacion(
        juego=juego,
        numeros_marcados=numeros_marcados,
        estrellas_marcadas=estrellas_marcadas,
        sorteos_evaluados=len(filas),
        warmup_omitidos=warmup,
    )

    if not filas:
        informe.conclusion = "No hay suficientes sorteos en la base para evaluar."
        return informe

    for t in tipos:
        pool_size = len(t.pool)
        media_hit = sum(f.aciertos[t.nombre] for f in filas) / len(filas)
        media_pct = sum(f.pct_por_tipo[t.nombre] for f in filas) / len(filas)
        esp_hit = _esperado_aciertos(pool_size, t.tamano_bloque, t.bolas_sorteo)
        esp_pct = _esperado_pct(pool_size, t.tamano_bloque)
        informe.resumen[t.nombre] = media_pct
        informe.esperado_azar[t.nombre] = esp_pct
        informe.diferencia_vs_azar[t.nombre] = media_pct - esp_pct
        informe.resumen[f"{t.nombre}_aciertos"] = media_hit
        informe.esperado_azar[f"{t.nombre}_aciertos"] = esp_hit

    informe.media_pct_global = sum(f.pct_medio for f in filas) / len(filas)

    esp_g = []
    for t in tipos:
        esp_g.append(_esperado_pct(len(t.pool), t.tamano_bloque))
    informe.esperado_pct_global = sum(esp_g) / len(esp_g) if esp_g else 0.0

    tercio = max(len(filas) // 3, 1)
    informe.media_primer_tercio = sum(
        f.pct_medio for f in filas[:tercio]
    ) / tercio
    informe.media_ultimo_tercio = sum(
        f.pct_medio for f in filas[-tercio:]
    ) / tercio

    ordenados = sorted(filas, key=lambda f: f.pct_medio, reverse=True)
    informe.mejores = ordenados[:12]
    informe.peores = sorted(filas, key=lambda f: f.pct_medio)[:8]
    informe.ultimos = filas[-15:]

    diff_global = informe.media_pct_global - informe.esperado_pct_global
    diff_tend = informe.media_ultimo_tercio - informe.media_primer_tercio

    if abs(diff_global) < 0.4:
        base = "La heurística ronda el azar teórico (diferencia global < 0,4 p.p.). "
    elif diff_global > 0.4:
        base = (
            f"Ligeramente por encima del azar (+{diff_global:.2f} p.p. de media). "
        )
    else:
        base = (
            f"Ligeramente por debajo del azar ({diff_global:.2f} p.p. de media). "
        )

    if abs(diff_tend) < 0.5:
        tend = "No hay mejora clara entre el primer y el último tercio del histórico."
    elif diff_tend > 0.5:
        tend = (
            f"El último tercio del histórico puntúa algo mejor (+{diff_tend:.2f} p.p.), "
            "pero puede ser variación aleatoria."
        )
    else:
        tend = (
            f"El último tercio puntúa peor ({diff_tend:.2f} p.p.); no gana fiabilidad con el tiempo."
        )

    informe.conclusion = base + tend
    return informe
