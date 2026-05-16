#!/usr/bin/env python3
"""Lanza la interfaz de análisis de loterías."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main_window import MainWindow, DEFAULT_DB


def main() -> None:
    p = argparse.ArgumentParser(description="GUI Loterías (SELAE)")
    p.add_argument("--db", default=str(DEFAULT_DB), help="Ruta SQLite")
    args = p.parse_args()
    app = MainWindow(db_path=args.db)
    app.mainloop()


if __name__ == "__main__":
    main()
