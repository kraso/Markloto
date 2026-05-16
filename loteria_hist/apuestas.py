"""Apuestas múltiples: combinaciones, coste y probabilidades (SELAE)."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ReglasJuego:
    juego: str
    etiqueta: str
    precio_simple: float
    base_principal: int
    pool_principal: int
    base_estrella: int = 0
    pool_estrella: int = 0
    min_marcados: int = 5
    max_marcados: int = 11
    min_estrellas: int = 2
    max_estrellas: int = 5
    total_combinaciones_sorteo: int = 0  # jackpot; 0 = calcular automático

    def __post_init__(self) -> None:
        if self.total_combinaciones_sorteo <= 0:
            t = math.comb(self.pool_principal, self.base_principal)
            if self.base_estrella:
                t *= math.comb(self.pool_estrella, self.base_estrella)
            object.__setattr__(self, "total_combinaciones_sorteo", t)


REGLAS: dict[str, ReglasJuego] = {
    "euromillones": ReglasJuego(
        juego="euromillones",
        etiqueta="Euromillones",
        precio_simple=2.50,
        base_principal=5,
        pool_principal=50,
        base_estrella=2,
        pool_estrella=12,
        min_marcados=5,
        max_marcados=10,
        min_estrellas=2,
        max_estrellas=5,
        total_combinaciones_sorteo=139_838_160,
    ),
    "bonoloto": ReglasJuego(
        juego="bonoloto",
        etiqueta="Bonoloto",
        precio_simple=0.50,
        base_principal=6,
        pool_principal=49,
        min_marcados=5,
        max_marcados=11,
    ),
    "primitiva": ReglasJuego(
        juego="primitiva",
        etiqueta="La Primitiva",
        precio_simple=1.00,
        base_principal=6,
        pool_principal=49,
        min_marcados=5,
        max_marcados=11,
    ),
}


@dataclass(frozen=True)
class FilaApuestaMultiple:
    numeros_marcados: int
    estrellas_marcadas: int | None
    combinaciones: int
    coste_eur: float
    prob_jackpot: float
    prob_en_bloque_4: float
    prob_en_bloque_5: float
    prob_en_bloque_6: float
    mejora_vs_simple: float  # prob_jackpot / prob de 1 apuesta simple


def _combinaciones_apuesta(
    reglas: ReglasJuego,
    numeros_marcados: int,
    estrellas_marcadas: int | None = None,
) -> int:
    base = reglas.base_principal
    if numeros_marcados < reglas.min_marcados or numeros_marcados > reglas.max_marcados:
        return 0
    if numeros_marcados < base:
        # Apuesta múltiple reducida: fijos + resto del bombo
        faltan = base - numeros_marcados
        return math.comb(reglas.pool_principal - numeros_marcados, faltan)
    return math.comb(numeros_marcados, base)


def _combinaciones_totales(
    reglas: ReglasJuego,
    numeros_marcados: int,
    estrellas_marcadas: int | None,
) -> int:
    c = _combinaciones_apuesta(reglas, numeros_marcados)
    if not reglas.base_estrella:
        return c
    est = estrellas_marcadas if estrellas_marcadas is not None else reglas.base_estrella
    if est < reglas.min_estrellas or est > reglas.max_estrellas:
        return 0
    if est < reglas.base_estrella:
        return 0
    return c * math.comb(est, reglas.base_estrella)


def probabilidad_jackpot(
    reglas: ReglasJuego,
    numeros_marcados: int,
    estrellas_marcadas: int | None = None,
) -> float:
    """
    P(acertar categoría máxima) con una apuesta múltiple en un sorteo.
    Equivale a (combinaciones jugadas) / (combinaciones posibles del sorteo)
    cuando todas las bolas ganadoras caen dentro de tu bloque marcado.
    """
    comb = _combinaciones_totales(reglas, numeros_marcados, estrellas_marcadas)
    if comb <= 0:
        return 0.0
    return comb / reglas.total_combinaciones_sorteo


def probabilidad_bolas_en_bloque(
    reglas: ReglasJuego,
    numeros_marcados: int,
    aciertos_minimos: int,
) -> float:
    """
    P(al menos `aciertos_minimos` de las 6 bolas ganadoras están entre tus
    `numeros_marcados` elegidos). Indicador de premios altos en 6/49.
    """
    if numeros_marcados < aciertos_minimos:
        return 0.0
    pool = reglas.pool_principal
    k = numeros_marcados
    total = math.comb(pool, reglas.base_principal)
    p = 0.0
    drawn = reglas.base_principal
    for r in range(aciertos_minimos, min(k, drawn) + 1):
        if r > drawn:
            break
        p += math.comb(k, r) * math.comb(pool - k, drawn - r) / total
    return p


def fila_apuesta_multiple(
    reglas: ReglasJuego,
    numeros_marcados: int,
    estrellas_marcadas: int | None = None,
) -> FilaApuestaMultiple | None:
    comb = _combinaciones_totales(reglas, numeros_marcados, estrellas_marcadas)
    if comb <= 0:
        return None
    coste = comb * reglas.precio_simple
    p_jack = probabilidad_jackpot(reglas, numeros_marcados, estrellas_marcadas)
    p_simple = 1.0 / reglas.total_combinaciones_sorteo
    est = estrellas_marcadas
    return FilaApuestaMultiple(
        numeros_marcados=numeros_marcados,
        estrellas_marcadas=est,
        combinaciones=comb,
        coste_eur=coste,
        prob_jackpot=p_jack,
        prob_en_bloque_4=probabilidad_bolas_en_bloque(reglas, numeros_marcados, 4),
        prob_en_bloque_5=probabilidad_bolas_en_bloque(reglas, numeros_marcados, 5),
        prob_en_bloque_6=probabilidad_bolas_en_bloque(reglas, numeros_marcados, 6),
        mejora_vs_simple=p_jack / p_simple if p_simple else 0.0,
    )


def tabla_apuestas_multiples(
    juego: str,
    *,
    estrellas_marcadas: int | None = None,
) -> list[FilaApuestaMultiple]:
    reglas = REGLAS[juego]
    filas: list[FilaApuestaMultiple] = []
    for n in range(reglas.min_marcados, reglas.max_marcados + 1):
        f = fila_apuesta_multiple(reglas, n, estrellas_marcadas)
        if f:
            filas.append(f)
    return filas


def formatear_prob(p: float) -> str:
    if p <= 0:
        return "—"
    if p >= 0.01:
        return f"{p * 100:.4f} %"
    odds = 1.0 / p
    if odds >= 1_000_000:
        return f"1 en {odds:,.0f}".replace(",", ".")
    if odds >= 10_000:
        return f"1 en {odds:,.0f}".replace(",", ".")
    return f"1 en {odds:,.1f}".replace(",", ".")


def formatear_eur(v: float) -> str:
    if v == int(v):
        return f"{int(v)} €"
    return f"{v:.2f} €".replace(".", ",")
