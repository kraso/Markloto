from __future__ import annotations

import random
import sqlite3
from dataclasses import dataclass, field

from . import repository


@dataclass(frozen=True)
class AnalisisJuego:
    frecuencias: dict[str, list[tuple[int, int]]]
    retrasos: dict[str, list[tuple[int, int]]]
    sugerencia: dict[str, list[int]]
    resumen: repository.ResumenJuego


def _retrasos_desde_historial(
    historial: list[list[int]],
    rango: range,
) -> list[tuple[int, int]]:
    """(número, sorteos sin salir). 0 = salió en el último sorteo."""
    ultima: dict[int, int] = {}
    for idx, vals in enumerate(historial):
        for v in vals:
            ultima[v] = idx
    total = len(historial)
    out: list[tuple[int, int]] = []
    for n in rango:
        if n in ultima:
            out.append((n, total - 1 - ultima[n]))
        else:
            out.append((n, total))
    out.sort(key=lambda x: (-x[1], x[0]))
    return out


def _sugerir_desde_frecuencia(
    freq: list[tuple[int, int]],
    cantidad: int,
    pool_max: int,
    *,
    semilla: int | None = None,
) -> list[int]:
    """
    Mezcla números más frecuentes con ligera aleatoriedad para no repetir siempre la misma línea.
  Heurística descriptiva, no predicción.
    """
    if not freq:
        rng = random.Random(semilla)
        return sorted(rng.sample(list(range(1, pool_max + 1)), cantidad))

    top = [n for n, _ in freq[: max(cantidad * 3, cantidad + 5)]]
    pesos = [max(1, c) for _, c in freq[: len(top)]]
    rng = random.Random(semilla)
    elegidos: list[int] = []
    pool = top.copy()
    w = pesos[: len(pool)]
    while len(elegidos) < cantidad and pool:
        total_w = sum(w)
        pick = rng.choices(pool, weights=w, k=1)[0]
        elegidos.append(pick)
        i = pool.index(pick)
        pool.pop(i)
        w.pop(i)
    if len(elegidos) < cantidad:
        restantes = [n for n in range(1, pool_max + 1) if n not in elegidos]
        rng.shuffle(restantes)
        elegidos.extend(restantes[: cantidad - len(elegidos)])
    return sorted(elegidos)


def analizar_euromillones(conn: sqlite3.Connection) -> AnalisisJuego:
    juego = "euromillones"
    resumen = repository.resumen_juego(conn, juego)
    total, fecha_idx = repository.fechas_indice(conn, juego)
    freq_p = repository.frecuencias(conn, juego, "principal")
    freq_e = repository.frecuencias(conn, juego, "estrella")
    kw = {"fecha_idx": fecha_idx, "total": total}
    return AnalisisJuego(
        frecuencias={"principal": freq_p, "estrella": freq_e},
        retrasos={
            "principal": repository.retrasos_por_tipo(
                conn, juego, "principal", range(1, 51), **kw
            ),
            "estrella": repository.retrasos_por_tipo(
                conn, juego, "estrella", range(1, 13), **kw
            ),
        },
        sugerencia={
            "principal": _sugerir_desde_frecuencia(freq_p, 5, 50),
            "estrella": _sugerir_desde_frecuencia(freq_e, 2, 12),
        },
        resumen=resumen,
    )


def analizar_bonoloto(conn: sqlite3.Connection) -> AnalisisJuego:
    juego = "bonoloto"
    resumen = repository.resumen_juego(conn, juego)
    total, fecha_idx = repository.fechas_indice(conn, juego)
    freq_p = repository.frecuencias(conn, juego, "principal")
    freq_c = repository.frecuencias(conn, juego, "complementario")
    freq_r = repository.frecuencias(conn, juego, "reintegro")
    kw = {"fecha_idx": fecha_idx, "total": total}
    return AnalisisJuego(
        frecuencias={
            "principal": freq_p,
            "complementario": freq_c,
            "reintegro": freq_r,
        },
        retrasos={
            "principal": repository.retrasos_por_tipo(
                conn, juego, "principal", range(1, 50), **kw
            ),
            "complementario": repository.retrasos_por_tipo(
                conn, juego, "complementario", range(1, 50), **kw
            ),
            "reintegro": repository.retrasos_por_tipo(
                conn, juego, "reintegro", range(0, 10), **kw
            ),
        },
        sugerencia={
            "principal": _sugerir_desde_frecuencia(freq_p, 6, 49),
            "complementario": _sugerir_desde_frecuencia(freq_c, 1, 49),
            "reintegro": _sugerir_desde_frecuencia(freq_r, 1, 9),
        },
        resumen=resumen,
    )


def analizar_primitiva(conn: sqlite3.Connection) -> AnalisisJuego:
    juego = "primitiva"
    resumen = repository.resumen_juego(conn, juego)
    total, fecha_idx = repository.fechas_indice(conn, juego)
    freq_p = repository.frecuencias(conn, juego, "principal")
    freq_c = repository.frecuencias(conn, juego, "complementario")
    freq_r = repository.frecuencias(conn, juego, "reintegro")
    kw = {"fecha_idx": fecha_idx, "total": total}
    return AnalisisJuego(
        frecuencias={
            "principal": freq_p,
            "complementario": freq_c,
            "reintegro": freq_r,
        },
        retrasos={
            "principal": repository.retrasos_por_tipo(
                conn, juego, "principal", range(1, 50), **kw
            ),
            "complementario": repository.retrasos_por_tipo(
                conn, juego, "complementario", range(1, 50), **kw
            ),
            "reintegro": repository.retrasos_por_tipo(
                conn, juego, "reintegro", range(0, 10), **kw
            ),
        },
        sugerencia={
            "principal": _sugerir_desde_frecuencia(freq_p, 6, 49),
            "complementario": _sugerir_desde_frecuencia(freq_c, 1, 49),
            "reintegro": _sugerir_desde_frecuencia(freq_r, 1, 9),
        },
        resumen=resumen,
    )


ANALIZADORES = {
    "euromillones": analizar_euromillones,
    "bonoloto": analizar_bonoloto,
    "primitiva": analizar_primitiva,
}

_POOLS: dict[str, dict[str, tuple[int, int]]] = {
    "euromillones": {
        "principal": (5, 50),
        "estrella": (2, 12),
    },
    "bonoloto": {
        "principal": (6, 49),
        "complementario": (1, 49),
        "reintegro": (1, 9),
    },
    "primitiva": {
        "principal": (6, 49),
        "complementario": (1, 49),
        "reintegro": (1, 9),
    },
}


@dataclass(frozen=True)
class DetalleNumero:
    valor: int
    frecuencia: int
    prob_empirica: float
    prob_teorica: float
    score: float


@dataclass(frozen=True)
class CombinacionMultiple:
    """Números con mayor puntuación histórica para un tamaño de apuesta múltiple."""

    numeros: dict[str, list[int]]
    detalle: dict[str, list[DetalleNumero]] = field(default_factory=dict)
    numeros_marcados: int = 0
    estrellas_marcadas: int | None = None


def _mapa_frecuencias(freq: list[tuple[int, int]], pool: range) -> dict[int, int]:
    m = {n: 0 for n in pool}
    for n, c in freq:
        if n in m:
            m[n] = c
    return m


def _scores_para_tipo(
    freq: list[tuple[int, int]],
    retrasos: list[tuple[int, int]],
    pool: range,
    *,
    bolas_por_sorteo: int,
    total_sorteos: int = 0,
    peso_freq: float = 0.75,
    peso_teorica: float = 0.15,
    peso_retraso: float = 0.10,
) -> list[tuple[int, float, DetalleNumero]]:
    """
    Puntuación por número: frecuencia histórica (empírica), probabilidad teórica
    uniforme en el bombo y ligero peso por retraso (números más «presentes»).
    """
    counts = _mapa_frecuencias(freq, pool)
    retraso_map = {n: d for n, d in retrasos}
    max_retraso = max(retraso_map.values()) if retraso_map else 1
    p_teorica = bolas_por_sorteo / len(pool) if len(pool) else 0.0
    n_sorteos = total_sorteos or 1

    scored: list[tuple[int, float, DetalleNumero]] = []
    max_count = max(counts.values()) if counts else 1

    for n in pool:
        c = counts[n]
        p_emp = c / n_sorteos
        freq_norm = c / max_count if max_count else 0.0
        teor_norm = p_teorica / p_teorica if p_teorica else 1.0  # constante → 1.0
        delay = retraso_map.get(n, max_retraso)
        # Menor retraso = salió hace poco → refuerzo suave (número «caliente»)
        retraso_norm = 1.0 - (delay / max_retraso) if max_retraso else 0.0
        score = peso_freq * freq_norm + peso_teorica * teor_norm + peso_retraso * retraso_norm
        scored.append(
            (
                n,
                score,
                DetalleNumero(
                    valor=n,
                    frecuencia=c,
                    prob_empirica=p_emp,
                    prob_teorica=p_teorica,
                    score=score,
                ),
            )
        )

    scored.sort(key=lambda x: (-x[1], x[0]))
    return scored


def _elegir_top(
    scored: list[tuple[int, float, DetalleNumero]],
    cantidad: int,
) -> tuple[list[int], list[DetalleNumero]]:
    top = scored[:cantidad]
    nums = sorted(t[0] for t in top)
    det = sorted((t[2] for t in top), key=lambda d: d.valor)
    return nums, det


def top_n_desde_contadores(
    counts: dict[int, int],
    last_seen: dict[int, int],
    indice_sorteo: int,
    pool: range,
    *,
    bolas_por_sorteo: int,
    cantidad: int,
) -> list[int]:
    """Top N por score usando solo historial previo (índice = sorteos ya vistos)."""
    freq = [(n, counts.get(n, 0)) for n in pool]
    retrasos = [
        (n, indice_sorteo - last_seen[n] if n in last_seen else indice_sorteo)
        for n in pool
    ]
    scored = _scores_para_tipo(
        freq,
        retrasos,
        pool,
        bolas_por_sorteo=bolas_por_sorteo,
        total_sorteos=max(indice_sorteo, 1),
    )
    nums, _ = _elegir_top(scored, cantidad)
    return nums


def combinacion_para_apuesta_multiple(
    analisis: AnalisisJuego,
    juego: str,
    *,
    numeros_marcados: int,
    estrellas_marcadas: int | None = None,
) -> CombinacionMultiple:
    """
    Devuelve los N números (y estrellas) con mayor score histórico para marcar
    en una apuesta múltiple del tamaño indicado.
    """
    numeros: dict[str, list[int]] = {}
    detalle: dict[str, list[DetalleNumero]] = {}

    total = analisis.resumen.total or 1

    if juego == "euromillones":
        scored_p = _scores_para_tipo(
            analisis.frecuencias.get("principal", []),
            analisis.retrasos.get("principal", []),
            range(1, 51),
            bolas_por_sorteo=5,
            total_sorteos=total,
        )
        nums, det = _elegir_top(scored_p, numeros_marcados)
        numeros["principal"] = nums
        detalle["principal"] = det

        est = estrellas_marcadas if estrellas_marcadas is not None else 2
        scored_e = _scores_para_tipo(
            analisis.frecuencias.get("estrella", []),
            analisis.retrasos.get("estrella", []),
            range(1, 13),
            bolas_por_sorteo=2,
            total_sorteos=total,
        )
        nums_e, det_e = _elegir_top(scored_e, est)
        numeros["estrella"] = nums_e
        detalle["estrella"] = det_e

        return CombinacionMultiple(
            numeros=numeros,
            detalle=detalle,
            numeros_marcados=numeros_marcados,
            estrellas_marcadas=est,
        )

    # Bonoloto / Primitiva
    scored_p = _scores_para_tipo(
        analisis.frecuencias.get("principal", []),
        analisis.retrasos.get("principal", []),
        range(1, 50),
        bolas_por_sorteo=6,
        total_sorteos=total,
    )
    nums, det = _elegir_top(scored_p, numeros_marcados)
    numeros["principal"] = nums
    detalle["principal"] = det

    for tipo, pool, bolas in (
        ("complementario", range(1, 50), 1),
        ("reintegro", range(0, 10), 1),
    ):
        if tipo not in analisis.frecuencias:
            continue
        scored = _scores_para_tipo(
            analisis.frecuencias[tipo],
            analisis.retrasos.get(tipo, []),
            pool,
            bolas_por_sorteo=bolas,
            total_sorteos=total,
        )
        n_list, d_list = _elegir_top(scored, 1)
        numeros[tipo] = n_list
        detalle[tipo] = d_list

    return CombinacionMultiple(
        numeros=numeros,
        detalle=detalle,
        numeros_marcados=numeros_marcados,
        estrellas_marcadas=estrellas_marcadas,
    )


@dataclass(frozen=True)
class EvaluacionTipo:
    numeros: list[int]
    detalles: list[DetalleNumero]
    score_medio: float
    prob_empirica_media: float
    prob_teorica: float


@dataclass(frozen=True)
class ComparacionApuesta:
    """Tu selección frente a la sugerencia heurística (mismo tamaño de bloque)."""

    usuario: dict[str, EvaluacionTipo]
    sugerencia: dict[str, EvaluacionTipo]
    combinaciones: int
    coste_eur: float
    prob_jackpot_usuario: float
    prob_jackpot_sugerencia: float
    numeros_marcados: int
    estrellas_marcadas: int | None


def _detalle_numeros(
    analisis: AnalisisJuego,
    tipo: str,
    numeros: list[int],
    pool: range,
    bolas_por_sorteo: int,
) -> list[DetalleNumero]:
    total = analisis.resumen.total or 1
    scored = _scores_para_tipo(
        analisis.frecuencias.get(tipo, []),
        analisis.retrasos.get(tipo, []),
        pool,
        bolas_por_sorteo=bolas_por_sorteo,
        total_sorteos=total,
    )
    por_valor = {d.valor: d for _, _, d in scored}
    return [por_valor[n] for n in sorted(numeros) if n in por_valor]


def _evaluar_tipo(
    analisis: AnalisisJuego,
    tipo: str,
    numeros: list[int],
    pool: range,
    bolas_por_sorteo: int,
) -> EvaluacionTipo:
    detalles = _detalle_numeros(analisis, tipo, numeros, pool, bolas_por_sorteo)
    if not detalles:
        return EvaluacionTipo(
            numeros=sorted(numeros),
            detalles=[],
            score_medio=0.0,
            prob_empirica_media=0.0,
            prob_teorica=bolas_por_sorteo / len(pool) if len(pool) else 0.0,
        )
    return EvaluacionTipo(
        numeros=sorted(numeros),
        detalles=detalles,
        score_medio=sum(d.score for d in detalles) / len(detalles),
        prob_empirica_media=sum(d.prob_empirica for d in detalles) / len(detalles),
        prob_teorica=detalles[0].prob_teorica,
    )


def comparar_seleccion_con_sugerencia(
    analisis: AnalisisJuego,
    juego: str,
    seleccion: dict[str, list[int]],
    *,
    numeros_marcados: int | None = None,
    estrellas_marcadas: int | None = None,
) -> ComparacionApuesta | None:
    """
    Evalúa los números elegidos por el usuario y los compara con la sugerencia
    heurística del mismo tamaño (scores, probabilidades empíricas, P(jackpot)).
    """
    from . import apuestas as ap

    reglas = ap.REGLAS.get(juego)
    if not reglas:
        return None

    n_prin = seleccion.get("principal", [])
    n_marc = numeros_marcados if numeros_marcados is not None else len(n_prin)
    if len(n_prin) != n_marc or n_marc < 1:
        return None

    est = estrellas_marcadas
    if juego == "euromillones":
        est_list = seleccion.get("estrella", [])
        est = est if est is not None else len(est_list)
        if len(est_list) != est or est < reglas.min_estrellas:
            return None
    else:
        if seleccion.get("complementario") and len(seleccion["complementario"]) != 1:
            return None
        if seleccion.get("reintegro") and len(seleccion["reintegro"]) != 1:
            return None

    sug = combinacion_para_apuesta_multiple(
        analisis, juego, numeros_marcados=n_marc, estrellas_marcadas=est
    )

    usuario_ev: dict[str, EvaluacionTipo] = {}
    sugerencia_ev: dict[str, EvaluacionTipo] = {}

    if juego == "euromillones":
        usuario_ev["principal"] = _evaluar_tipo(
            analisis, "principal", n_prin, range(1, 51), 5
        )
        usuario_ev["estrella"] = _evaluar_tipo(
            analisis, "estrella", seleccion.get("estrella", []), range(1, 13), 2
        )
        sugerencia_ev["principal"] = _evaluar_tipo(
            analisis, "principal", sug.numeros["principal"], range(1, 51), 5
        )
        sugerencia_ev["estrella"] = _evaluar_tipo(
            analisis, "estrella", sug.numeros.get("estrella", []), range(1, 13), 2
        )
    else:
        usuario_ev["principal"] = _evaluar_tipo(
            analisis, "principal", n_prin, range(1, 50), 6
        )
        sugerencia_ev["principal"] = _evaluar_tipo(
            analisis, "principal", sug.numeros["principal"], range(1, 50), 6
        )
        if seleccion.get("complementario"):
            usuario_ev["complementario"] = _evaluar_tipo(
                analisis,
                "complementario",
                seleccion["complementario"],
                range(1, 50),
                1,
            )
            sugerencia_ev["complementario"] = _evaluar_tipo(
                analisis,
                "complementario",
                sug.numeros.get("complementario", []),
                range(1, 50),
                1,
            )
        if seleccion.get("reintegro"):
            usuario_ev["reintegro"] = _evaluar_tipo(
                analisis, "reintegro", seleccion["reintegro"], range(0, 10), 1
            )
            sugerencia_ev["reintegro"] = _evaluar_tipo(
                analisis,
                "reintegro",
                sug.numeros.get("reintegro", []),
                range(0, 10),
                1,
            )

    fila_u = ap.fila_apuesta_multiple(reglas, n_marc, est)
    fila_s = ap.fila_apuesta_multiple(reglas, n_marc, est)
    p_u = fila_u.prob_jackpot if fila_u else 0.0
    p_s = fila_s.prob_jackpot if fila_s else 0.0
    comb = fila_u.combinaciones if fila_u else 0
    coste = fila_u.coste_eur if fila_u else 0.0

    return ComparacionApuesta(
        usuario=usuario_ev,
        sugerencia=sugerencia_ev,
        combinaciones=comb,
        coste_eur=coste,
        prob_jackpot_usuario=p_u,
        prob_jackpot_sugerencia=p_s,
        numeros_marcados=n_marc,
        estrellas_marcadas=est,
    )


def nueva_sugerencia(
    analisis: AnalisisJuego,
    juego: str,
    *,
    semilla: int | None = None,
) -> dict[str, list[int]]:
    """Regenera la sugerencia heurística con otra semilla aleatoria."""
    pools = _POOLS.get(juego, {})
    out: dict[str, list[int]] = {}
    for tipo, freq in analisis.frecuencias.items():
        cant, mx = pools.get(tipo, (1, 49))
        salt = hash(tipo) & 0xFFFF
        out[tipo] = _sugerir_desde_frecuencia(
            freq, cant, mx, semilla=(semilla + salt) if semilla is not None else None
        )
    return out
