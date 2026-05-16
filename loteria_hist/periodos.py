"""Rangos de fechas para resúmenes históricos (mes, trimestre, año, etc.)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class RangoPeriodo:
    modo: str
    etiqueta: str
    inicio: date
    fin: date

    @property
    def inicio_iso(self) -> str:
        return self.inicio.isoformat()

    @property
    def fin_iso(self) -> str:
        return self.fin.isoformat()


MODOS_PERIODO = (
    "mes",
    "trimestre",
    "semestre",
    "anio",
    "bianual",
    "completo",
)

ETIQUETAS_PERIODO_UI: dict[str, str] = {
    "Mes actual": "mes",
    "Trimestre actual": "trimestre",
    "Semestre actual": "semestre",
    "Año actual": "anio",
    "Últimos 2 años": "bianual",
    "Histórico completo": "completo",
}


def inicio_mes(ref: date) -> date:
    return date(ref.year, ref.month, 1)


def inicio_trimestre(ref: date) -> date:
    mes_inicio = ((ref.month - 1) // 3) * 3 + 1
    return date(ref.year, mes_inicio, 1)


def inicio_semestre(ref: date) -> date:
    mes_inicio = 1 if ref.month <= 6 else 7
    return date(ref.year, mes_inicio, 1)


def inicio_anio(ref: date) -> date:
    return date(ref.year, 1, 1)


def inicio_bianual(ref: date) -> date:
    """Desde el 1 de enero del año anterior al actual (dos años naturales)."""
    return date(ref.year - 1, 1, 1)


def _fmt_rango(inicio: date, fin: date) -> str:
    return f"{inicio.strftime('%d/%m/%Y')} – {fin.strftime('%d/%m/%Y')}"


def rango_periodo(
    modo: str,
    ref: date | None = None,
    *,
    fecha_min: date | None = None,
    fecha_max: date | None = None,
) -> RangoPeriodo:
    ref = ref or date.today()
    fin = fecha_max or ref

    if modo == "completo":
        if fecha_min is None:
            raise ValueError("Histórico completo requiere fecha_min en la base de datos")
        inicio = fecha_min
        etiqueta = f"Histórico completo · {_fmt_rango(inicio, fin)}"
    elif modo == "mes":
        inicio = inicio_mes(ref)
        etiqueta = f"Mes {ref.strftime('%m/%Y')} · {_fmt_rango(inicio, fin)}"
    elif modo == "semestre":
        inicio = inicio_semestre(ref)
        sem = 1 if inicio.month == 1 else 2
        etiqueta = f"Semestre {sem} · {_fmt_rango(inicio, fin)}"
    elif modo == "anio":
        inicio = inicio_anio(ref)
        etiqueta = f"Año {ref.year} · {_fmt_rango(inicio, fin)}"
    elif modo == "bianual":
        inicio = inicio_bianual(ref)
        etiqueta = f"Últimos 2 años · {_fmt_rango(inicio, fin)}"
    else:
        inicio = inicio_trimestre(ref)
        trim = (inicio.month - 1) // 3 + 1
        etiqueta = f"Trimestre {trim} · {_fmt_rango(inicio, fin)}"

    return RangoPeriodo(modo=modo, etiqueta=etiqueta, inicio=inicio, fin=fin)
