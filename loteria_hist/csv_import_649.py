from __future__ import annotations

import csv
import io
from pathlib import Path

import urllib.request

from .db import upsert_sorteo

EXPECTED_HEADER = ("fecha", "n1", "n2", "n3", "n4", "n5", "n6", "complementario", "reintegro")


def import_csv_6_de_49(conn, path: Path | str, *, juego: str, fuente: str) -> int:
    """
    CSV con cabecera:
    fecha,n1,n2,n3,n4,n5,n6,complementario,reintegro
    fecha en formato YYYY-MM-DD (también se acepta DD/MM/YYYY).
    juego: bonoloto | primitiva
    """
    if juego not in ("bonoloto", "primitiva"):
        raise ValueError(juego)

    raw = Path(path).read_bytes() if not str(path).startswith("http") else _fetch_bytes(str(path))
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("CSV sin cabecera")
    fields = [f.strip().lower() for f in reader.fieldnames]
    reader.fieldnames = fields

    missing = [c for c in EXPECTED_HEADER if c not in fields]
    if missing:
        raise ValueError(f"Faltan columnas {missing}. Cabecera actual: {fields}")

    count = 0
    for row in reader:
        fecha_raw = row["fecha"].strip()
        fecha = _norm_fecha(fecha_raw)
        main = sorted(int(row[f"n{i}"]) for i in range(1, 7))
        comp = int(row["complementario"])
        reint = int(row["reintegro"])
        nums: list[tuple[str, int, int]] = []
        for i, v in enumerate(main, start=1):
            nums.append(("principal", i, v))
        nums.append(("complementario", 1, comp))
        nums.append(("reintegro", 1, reint))
        upsert_sorteo(
            conn,
            juego=juego,
            fecha=fecha,
            dia_semana=None,
            numero_sorteo=None,
            premio_bote=None,
            id_externo=None,
            metadata=None,
            fuente=fuente,
            numeros=nums,
        )
        count += 1
    conn.commit()
    return count


def _fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"
            )
        },
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def _norm_fecha(s: str) -> str:
    s = s.strip()
    if "/" in s:
        d, m, y = s.split("/")
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    return s[:10]
