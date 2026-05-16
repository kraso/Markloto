#!/usr/bin/env python3
"""Markloto — cliente móvil (Flet). Desarrollo: flet run run_mobile.py"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import flet as ft

from mobile.app import main


if __name__ == "__main__":
    run = getattr(ft, "run", None) or getattr(ft, "app", None)
    if run is None:
        raise RuntimeError("Flet no expone ft.run ni ft.app")
    run(main)
