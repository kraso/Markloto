from __future__ import annotations

import csv
import io
import urllib.request
from pathlib import Path

from .db import upsert_sorteo

EUROMILLONES_CSV_DEFAULT = (
    "https://raw.githubusercontent.com/daowa89/lottery-archive/"
    "main/eu/euromillions/results.csv"
)


def import_euromillones_csv(
    conn,
    source: str | Path,
    *,
    fuente: str = "lottery-archive/eu/euromillions/results.csv",
) -> int:
    """
    CSV con columnas: date,n1,n2,n3,n4,n5,s1,s2
    source puede ser URL https o ruta local.
    """
    if isinstance(source, Path) or (isinstance(source, str) and not source.startswith("http")):
        raw = Path(source).read_bytes()
    else:
        req = urllib.request.Request(
            str(source),
            headers={"User-Agent": "Mozilla/5.0 (compatible; LoteriaHist/0.1)"},
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()

    text = raw.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    count = 0
    for row in reader:
        fecha = row["date"].strip()[:10]
        main = sorted(int(row[k]) for k in ("n1", "n2", "n3", "n4", "n5"))
        stars = sorted(int(row[k]) for k in ("s1", "s2"))
        nums: list[tuple[str, int, int]] = []
        for i, v in enumerate(main, start=1):
            nums.append(("principal", i, v))
        for i, v in enumerate(stars, start=1):
            nums.append(("estrella", i, v))
        upsert_sorteo(
            conn,
            juego="euromillones",
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
