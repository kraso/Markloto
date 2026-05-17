#!/usr/bin/env python3
"""
Genera data/seed/loterias.sqlite con histórico SELAE completo.

Ejecutar antes de empaquetar el instalador (tarda varios minutos):

    py -3 scripts/build_seed_db.py

La semilla se copia al arranque si la BD del usuario está vacía; luego la app
solo sincroniza novedades (incremental).
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from loteria_hist.db import connect, ensure_performance_indexes, init_schema  # noqa: E402
from loteria_hist.repository import resumen_juego  # noqa: E402
from loteria_hist.sync_selae import sincronizar_selae_retraso  # noqa: E402

JUEGOS = ("euromillones", "bonoloto", "primitiva")
SEED_DIR = ROOT / "data" / "seed"
SEED_DB = SEED_DIR / "loterias.sqlite"
INFO_JSON = SEED_DIR / "seed_info.json"


def main() -> None:
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    if SEED_DB.exists():
        SEED_DB.unlink()

    conn = connect(SEED_DB)
    init_schema(conn)
    ensure_performance_indexes(conn)
    conn.commit()
    fin = date.today()
    totals: dict[str, int] = {}

    print(f"==> Generando semilla en {SEED_DB}")
    for juego in JUEGOS:
        print(f"\n--- {juego} ---")
        totals[juego] = sincronizar_selae_retraso(
            conn,
            juego,
            fecha_fin=fin,
            fecha_min=None,
        )
        conn.commit()
        res = resumen_juego(conn, juego)
        print(f"    total en BD: {res.total} ({res.fecha_min} .. {res.fecha_max})")

    conn.close()

    fecha_max_global = None
    conn = connect(SEED_DB)
    try:
        for j in JUEGOS:
            r = resumen_juego(conn, j)
            if r.fecha_max and (fecha_max_global is None or r.fecha_max > fecha_max_global):
                fecha_max_global = r.fecha_max
    finally:
        conn.close()

    info = {
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "fecha_max": fecha_max_global,
        "juegos": totals,
        "nota": "Histórico SELAE hasta la fecha de generación; la app completa novedades al iniciar.",
    }
    INFO_JSON.write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")

    size_mb = SEED_DB.stat().st_size / (1024 * 1024)
    print(f"\n==> Listo: {SEED_DB} ({size_mb:.1f} MB)")
    print(f"    {INFO_JSON}")


if __name__ == "__main__":
    main()
