"""Rutas de la aplicación en desarrollo y en ejecutable empaquetado."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_FOLDER_NAME = "Markloto"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def bundle_root() -> Path:
    """Recursos de solo lectura (código embebido, schema.sql)."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
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
    return bundle_root() / "data" / "seed" / "loterias.sqlite"


def seed_info_path() -> Path:
    return bundle_root() / "data" / "seed" / "seed_info.json"


def project_seed_db_path() -> Path:
    """Ruta de la semilla en el árbol del proyecto (para generar el build)."""
    return install_root() / "data" / "seed" / "loterias.sqlite"
