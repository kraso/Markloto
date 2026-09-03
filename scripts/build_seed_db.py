#!/usr/bin/env python3
"""Genera data/seed/loterias.sqlite con histórico SELAE.

Por defecto: últimos 90 días (seed ligero ~1-2 MB, ideal para APKs).
Con --full-history: histórico completo (varios GB).

Ejecutar antes de empaquetar el instalador:

    py -3 scripts/build_seed_db.py              # seed ligero
    py -3 scripts/build_seed_db.py --full-history  # histórico completo

La semilla se copia al arranque si la BD del usuario está vacía; luego la app
solo sincroniza novedades (incremental).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
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

# Default: last 90 days for lightweight seeds (APKs / dev).
# Full historical seed only on request (--full-history).
DEFAULT_LIMIT_DAYS = 90


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--full-history",
        action="store_true",
        help="Descarga el histórico completo (desde 1985/1988/2004). Genera varios GB.",
    )
    p.add_argument(
        "--limit-days",
        type=int,
        default=DEFAULT_LIMIT_DAYS,
        help=f"Días hacia atrás desde hoy (default: {DEFAULT_LIMIT_DAYS}). Ignorado si --full-history.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    if SEED_DB.exists():
        SEED_DB.unlink()

    conn = connect(SEED_DB)
    init_schema(conn)
    ensure_performance_indexes(conn)
    conn.commit()
    fin = date.today()
    if args.full_history:
        fecha_min = None
        nota = "Histórico SELAE completo hasta la fecha de generación."
    else:
        fecha_min = fin - timedelta(days=args.limit_days)
        nota = f"Últimos {args.limit_days} días (seed ligero para APK). App completa histórico al iniciar."
    totals: dict[str, int] = {}

    print(f"==> Generando semilla en {SEED_DB}")
    for juego in JUEGOS:
        print(f"\n--- {juego} ---")
        totals[juego] = sincronizar_selae_retraso(
            conn,
            juego,
            fecha_fin=fin,
            fecha_min=fecha_min,
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
        "nota": nota,
    }
    INFO_JSON.write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")

    size_mb = SEED_DB.stat().st_size / (1024 * 1024)
    print(f"\n==> Listo: {SEED_DB} ({size_mb:.1f} MB)")
    print(f"    {INFO_JSON}")


if __name__ == "__main__":
    main()
