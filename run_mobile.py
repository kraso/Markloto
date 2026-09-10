#!/usr/bin/env python3
"""Markloto — cliente móvil (Flet). Desarrollo: flet run run_mobile.py"""

from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path

_TRACE_LOGS = [
    "/storage/emulated/0/Android/data/es.kraso.markloto.markloto/files/trace.log",
    "/sdcard/Download/markloto_trace.log",
]

def _open_trace():
    for p in _TRACE_LOGS:
        try:
            Path(p).parent.mkdir(parents=True, exist_ok=True)
            f = open(p, "a", buffering=1)
            f.write(f"[boot] opened {p}\n")
            return f
        except Exception:
            continue
    return None

_trace_file = _open_trace()

def _t(msg: str) -> None:
    ts = time.monotonic()
    line = f"[{ts:.3f}] {msg}\n"
    sys.stderr.write(line)
    if _trace_file:
        try:
            _trace_file.write(line)
            _trace_file.flush()
        except Exception:
            pass

_t("=== run_mobile.py START ===")
_t(f"cwd={os.getcwd()}")
_t(f"pid={os.getpid()}")
_t(f"sys.path={[p for p in sys.path[:5]]}")

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_t(f"ROOT={ROOT}")

_t("import flet...")
import flet as ft
_t(f"flet imported OK, version={getattr(ft, '__version__', '?')}")

_t("import mobile.app...")
from mobile.app import main
_t("mobile.app imported OK")

if __name__ == "__main__":
    _t("entering __main__")
    run = getattr(ft, "run", None) or getattr(ft, "app", None)
    if run is None:
        _t("ERROR: Flet no expone ft.run ni ft.app")
        raise RuntimeError("Flet no expone ft.run ni ft.app")
    _t(f"calling run(main)...")
    try:
        run(main)
        _t("run(main) returned normally")
    except Exception:
        _t(f"EXCEPTION in run(main):\n{traceback.format_exc()}")
        raise
