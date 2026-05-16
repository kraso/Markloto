"""Configuración compartida del cliente móvil."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from loteria_hist import analytics
from loteria_hist.analytics import AnalisisJuego

ACCENT = {
    "euromillones": "#f5e6a8",
    "bonoloto": "#a8dcff",
    "primitiva": "#e8eef5",
}

TIPO_LABEL = {
    "principal": "Principales",
    "estrella": "Estrellas",
    "complementario": "Complementario",
    "reintegro": "Reintegro",
}


@dataclass(frozen=True)
class JuegoConfig:
    key: str
    title: str
    accent: str
    analizar: Callable
    grupos: list[tuple[str, str]]


GAME_CONFIG: list[JuegoConfig] = [
    JuegoConfig(
        "euromillones",
        "Euromillones",
        ACCENT["euromillones"],
        analytics.analizar_euromillones,
        [("principal", "main"), ("estrella", "estrella")],
    ),
    JuegoConfig(
        "bonoloto",
        "Bonoloto",
        ACCENT["bonoloto"],
        analytics.analizar_bonoloto,
        [("principal", "main"), ("complementario", "complementario"), ("reintegro", "reintegro")],
    ),
    JuegoConfig(
        "primitiva",
        "La Primitiva",
        ACCENT["primitiva"],
        analytics.analizar_primitiva,
        [("principal", "main"), ("complementario", "complementario"), ("reintegro", "reintegro")],
    ),
]
