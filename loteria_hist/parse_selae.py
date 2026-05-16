from __future__ import annotations

import re
from typing import Any

_RE_BONO_PRIMITIVA = re.compile(
    r"^(?P<main>[\d\s\-]+)\s+C\((?P<c>\d+)\)\s+R\((?P<r>\d*)\)\s*$"
)
_RE_EMIL = re.compile(r"^\s*((?:\d{1,2}\s*-\s*){6}\d{1,2})\s*$")


def _ints_from_dash_segment(segment: str) -> list[int]:
    parts = [p.strip() for p in segment.split("-")]
    out: list[int] = []
    for p in parts:
        if not p:
            continue
        out.append(int(p))
    return out


def parse_combinacion_emil(combinacion: str) -> tuple[list[int], list[int]]:
    """Euromillones: 5 principales + 2 estrellas en un único campo."""
    m = _RE_EMIL.match(combinacion.strip())
    if not m:
        raise ValueError(f"combinacion EMIL no reconocida: {combinacion!r}")
    nums = _ints_from_dash_segment(m.group(1))
    if len(nums) != 7:
        raise ValueError(f"EMIL esperaba 7 números, hay {len(nums)}: {combinacion!r}")
    main = sorted(nums[:5])
    stars = sorted(nums[5:7])
    return main, stars


def parse_combinacion_bono_primitiva(
    combinacion: str,
) -> tuple[list[int], int, int]:
    """Bonoloto / La Primitiva: 6 principales + complementario + reintegro."""
    m = _RE_BONO_PRIMITIVA.match(combinacion.strip())
    if not m:
        raise ValueError(f"combinacion BONO/LAPR no reconocida: {combinacion!r}")
    main = sorted(_ints_from_dash_segment(m.group("main")))
    if len(main) != 6:
        raise ValueError(f"Se esperaban 6 principales: {combinacion!r}")
    c = int(m.group("c"))
    r_raw = m.group("r").strip()
    r = int(r_raw) if r_raw else 0
    return main, c, r


def numeros_rows_from_selae_record(row: dict[str, Any], juego: str) -> list[tuple[str, int, int]]:
    """Devuelve tuplas (tipo, orden, valor) para upsert_sorteo."""
    combo = str(row.get("combinacion", ""))
    out: list[tuple[str, int, int]] = []

    if juego == "euromillones":
        main, stars = parse_combinacion_emil(combo)
        for i, v in enumerate(main, start=1):
            out.append(("principal", i, v))
        for i, v in enumerate(stars, start=1):
            out.append(("estrella", i, v))
        return out

    main, comp, reint = parse_combinacion_bono_primitiva(combo)
    for i, v in enumerate(main, start=1):
        out.append(("principal", i, v))
    out.append(("complementario", 1, comp))
    out.append(("reintegro", 1, reint))
    return out


def metadata_selae(row: dict[str, Any], juego: str) -> dict[str, Any] | None:
    meta: dict[str, Any] = {}
    if juego == "euromillones" and row.get("millon"):
        meta["el_millon"] = row["millon"]
    if juego == "primitiva" and row.get("joker"):
        meta["joker"] = row["joker"]
    return meta or None
