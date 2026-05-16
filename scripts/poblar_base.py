#!/usr/bin/env python3
"""Inicializa la base SQLite y descarga históricos."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from loteria_hist.csv_euromillones import EUROMILLONES_CSV_DEFAULT, import_euromillones_csv
from loteria_hist.csv_import_649 import import_csv_6_de_49
from loteria_hist.db import connect, conteo_por_juego, init_schema
from loteria_hist.sync_selae import sincronizar_selae_retraso


def _parse_date(s: str) -> date:
    return date.fromisoformat(s)


def cmd_init(args: argparse.Namespace) -> None:
    db = Path(args.db)
    conn = connect(db)
    init_schema(conn)
    conn.close()
    print(f"Esquema creado en {db}")


def cmd_euromillones_csv(args: argparse.Namespace) -> None:
    conn = connect(args.db)
    src = args.url_or_file or EUROMILLONES_CSV_DEFAULT
    n = import_euromillones_csv(conn, src, fuente=args.fuente)
    conn.close()
    print(f"Euromillones: importados {n} sorteos desde {src}")


def cmd_selae(args: argparse.Namespace) -> None:
    conn = connect(args.db)
    fin = _parse_date(args.hasta) if args.hasta else date.today()
    ini = _parse_date(args.desde) if args.desde else None
    n = sincronizar_selae_retraso(
        conn,
        args.juego,
        fecha_fin=fin,
        fecha_min=ini,
        ventana_dias=args.ventana,
    )
    conn.close()
    print(f"{args.juego} (SELAE): procesados {n} registros")


def cmd_import649(args: argparse.Namespace) -> None:
    conn = connect(args.db)
    n = import_csv_6_de_49(
        conn,
        args.archivo,
        juego=args.juego,
        fuente=args.fuente or Path(args.archivo).name,
    )
    conn.close()
    print(f"{args.juego}: importadas {n} filas desde {args.archivo}")


def cmd_stats(args: argparse.Namespace) -> None:
    conn = connect(args.db)
    rows = conteo_por_juego(conn)
    conn.close()
    if not rows:
        print("Sin datos.")
        return
    for juego, n in rows:
        print(f"{juego}: {n} sorteos")


def main() -> None:
    p = argparse.ArgumentParser(
        description="Histórico Euromillones, Bonoloto, Primitiva",
        epilog=(
            "CSV Bonoloto/Primitiva (6/49): cabecera "
            "fecha,n1,n2,n3,n4,n5,n6,complementario,reintegro "
            "SELAE requiere: py -3.14 -m pip install curl_cffi"
        ),
    )
    p.add_argument("--db", default=str(ROOT / "loterias.sqlite"), help="Ruta SQLite")

    sub = p.add_subparsers(dest="cmd", required=True)

    s_init = sub.add_parser("init", help="Crea tablas")
    s_init.set_defaults(func=cmd_init)

    s_csv = sub.add_parser("euromillones-csv", help="Importa Euromillones desde CSV (URL o archivo)")
    s_csv.add_argument("url_or_file", nargs="?", default=None)
    s_csv.add_argument("--fuente", default="lottery-archive CSV")
    s_csv.set_defaults(func=cmd_euromillones_csv)

    s_selae = sub.add_parser("selae", help="Descarga desde API pública SELAE (Bonoloto/Primitiva/Euromillones)")
    s_selae.add_argument(
        "juego",
        choices=("euromillones", "bonoloto", "primitiva"),
    )
    s_selae.add_argument("--desde", default=None, help="YYYY-MM-DD")
    s_selae.add_argument("--hasta", default=None, help="YYYY-MM-DD")
    s_selae.add_argument(
        "--ventana",
        type=int,
        default=None,
        help="Días por petición (por defecto: 70 bonoloto, 120 primitiva, 182 euromillones)",
    )
    s_selae.set_defaults(func=cmd_selae)

    s_imp = sub.add_parser(
        "import-649",
        help="Importa Bonoloto o La Primitiva desde CSV local",
    )
    s_imp.add_argument("juego", choices=("bonoloto", "primitiva"))
    s_imp.add_argument("archivo", type=str)
    s_imp.add_argument("--fuente", default=None)
    s_imp.set_defaults(func=cmd_import649)

    s_stat = sub.add_parser("stats", help="Resumen por juego")
    s_stat.set_defaults(func=cmd_stats)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
