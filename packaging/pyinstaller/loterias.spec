# -*- mode: python ; coding: utf-8 -*-
# PyInstaller: ejecutable Windows x64 con Python y dependencias embebidas.
# Uso: pyinstaller packaging/pyinstaller/loterias.spec --clean --noconfirm

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH).resolve().parents[1]
_IS_WIN = sys.platform == "win32"
_USE_UPX = _IS_WIN

block_cipher = None

ctk_datas, ctk_binaries, ctk_hidden = collect_all("customtkinter")

try:
    curl_datas, curl_binaries, curl_hidden = collect_all("curl_cffi")
except Exception:
    curl_datas, curl_binaries, curl_hidden = [], [], []

try:
    xlsx_datas, xlsx_binaries, xlsx_hidden = collect_all("openpyxl")
except Exception:
    xlsx_datas, xlsx_binaries, xlsx_hidden = [], [], []

_seed_db = ROOT / "data" / "seed" / "loterias.sqlite"
_seed_info = ROOT / "data" / "seed" / "seed_info.json"
_seed_datas = []
if _seed_db.is_file():
    _seed_datas.append((str(_seed_db), "data/seed"))
if _seed_info.is_file():
    _seed_datas.append((str(_seed_info), "data/seed"))

datas = [
    (str(ROOT / "loteria_hist" / "schema.sql"), "loteria_hist"),
    (str(ROOT / "VERSION"), "."),
] + _seed_datas + ctk_datas + curl_datas + xlsx_datas

binaries = ctk_binaries + curl_binaries + xlsx_binaries

hiddenimports = (
    collect_submodules("curl_cffi")
    + collect_submodules("loteria_hist")
    + collect_submodules("app")
    + [
        "curl_cffi",
        "curl_cffi.requests",
        "_cffi_backend",
        "sqlite3",
        "tkinter",
        "_tkinter",
    ]
    + ctk_hidden
    + curl_hidden
    + xlsx_hidden
)

a = Analysis(
    [str(ROOT / "run_gui.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Markloto",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=_USE_UPX,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=_IS_WIN,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=_USE_UPX,
    upx_exclude=[],
    name="Markloto",
)
