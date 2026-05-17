"""Metadatos de Markloto (escritorio y móvil)."""

from __future__ import annotations

from loteria_hist.paths import bundle_root

APP_NAME = "Markloto ©"
AUTHOR = "Marcos Calabrés Ibáñez"
EMAIL = "markbiophysicist@gmail.com"
CREATION_DATE = "16/05/2026"
ABOUT_TEXT = (
    "Una aplicación que puedes usar como asistencia informativa a la hora de realizar "
    "tus apuestas en el sorteo de la Primitiva, la Bonoloto o el Euromillón. "
    "¡Qué la disfrutes y que tengas mucha suerte!"
)


def app_version() -> str:
    path = bundle_root() / "VERSION"
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return "1.0.1"
