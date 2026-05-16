"""Rutas de la aplicación en desarrollo y en ejecutable empaquetado."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_FOLDER_NAME = "Markloto"

_mobile_data_dir: Path | None = None


def configure_mobile_storage(page) -> None:
    """Registra el directorio de datos de la app Flet (Android/iOS)."""
    global _mobile_data_dir
    try:
        import flet as ft

        perm = getattr(ft, "PathPermission", None)
        if perm is not None:
            data = page.get_directory(perm.APP_DATA)
        else:
            data = page.get_directory("DATA")  # type: ignore[attr-defined]
        if data:
            _mobile_data_dir = Path(data)
            return
    except (AttributeError, TypeError, RuntimeError, ImportError):
        pass
    for key in ("FLET_APP_STORAGE_DATA", "FLET_APP_DATA"):
        val = os.environ.get(key)
        if val:
            _mobile_data_dir = Path(val)
            break


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def bundle_root() -> Path:
    """Recursos de solo lectura (código embebido, schema.sql)."""
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        assets = os.environ.get("FLET_APP_ASSETS_PATH")
        if assets:
            return Path(assets)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def install_root() -> Path:
    """Carpeta del .exe o del proyecto (datos escribibles)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def schema_sql_path() -> Path:
    return bundle_root() / "loteria_hist" / "schema.sql"


def default_data_dir() -> Path:
    """En instalador: Windows → %LOCALAPPDATA%\\Markloto; Linux → ~/.markloto/data."""
    if _mobile_data_dir is not None:
        data = _mobile_data_dir / "data"
        data.mkdir(parents=True, exist_ok=True)
        return data
    if is_frozen():
        if sys.platform == "win32":
            base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
            data = base / APP_FOLDER_NAME / "data"
        else:
            data = Path.home() / f".{APP_FOLDER_NAME.lower()}" / "data"
    else:
        data = install_root() / "data"
    data.mkdir(parents=True, exist_ok=True)
    return data


def default_db_path() -> Path:
    return default_data_dir() / "loterias.sqlite"


def bundled_seed_db_path() -> Path:
    """Base SQLite precargada (histórico hasta la fecha del build)."""
    root = bundle_root()
    for rel in (
        Path("data") / "seed" / "loterias.sqlite",
        Path("assets") / "data" / "seed" / "loterias.sqlite",
    ):
        p = root / rel
        if p.is_file():
            return p
    return root / "data" / "seed" / "loterias.sqlite"


def seed_info_path() -> Path:
    root = bundle_root()
    for rel in (
        Path("data") / "seed" / "seed_info.json",
        Path("assets") / "data" / "seed" / "seed_info.json",
    ):
        p = root / rel
        if p.is_file():
            return p
    return root / "data" / "seed" / "seed_info.json"


def project_seed_db_path() -> Path:
    """Ruta de la semilla en el árbol del proyecto (para generar el build)."""
    return install_root() / "data" / "seed" / "loterias.sqlite"
