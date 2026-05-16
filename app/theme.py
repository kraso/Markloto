"""Tema oscuro metalizado / brillante."""

from __future__ import annotations

# Paleta base
BG_DEEP = "#07090d"
BG_MAIN = "#0c1018"
BG_PANEL = "#141a24"
BG_PANEL_HI = "#1a2230"
BG_ELEVATED = "#222c3c"

BORDER = "#2e3a4d"
BORDER_SHINE = "#4a5f7a"
BORDER_GLOW = "#6b8cb8"

TEXT = "#eef2f7"
TEXT_DIM = "#8d9aad"
TEXT_MUTED = "#5c6b7f"

ACCENT = "#7ec8ff"
ACCENT_BRIGHT = "#a8dcff"
GOLD = "#e4c76b"
GOLD_BRIGHT = "#f5e6a8"
SILVER = "#c5d0de"
SILVER_BRIGHT = "#e8eef5"
ROSE = "#f0a8c0"

# Acentos por juego
GAME_ACCENTS = {
    "euromillones": GOLD_BRIGHT,
    "bonoloto": ACCENT_BRIGHT,
    "primitiva": SILVER_BRIGHT,
}

BALL_MAIN = "#1e2836"
BALL_MAIN_HOT = "#2d4a6e"
BALL_STAR = "#2a2418"
BALL_STAR_HOT = "#6b5528"
BALL_COMP = "#1e2a24"
BALL_REINT = "#2a1e28"

CTK_THEME = {
    "CTk": {
        "fg_color": BG_MAIN,
        "text_color": TEXT,
    },
    "CTkFrame": {
        "fg_color": BG_PANEL,
        "border_color": BORDER,
    },
    "CTkLabel": {
        "text_color": TEXT,
    },
    "CTkButton": {
        "fg_color": BG_ELEVATED,
        "hover_color": BORDER_SHINE,
        "border_color": BORDER_GLOW,
        "text_color": TEXT,
    },
    "CTkTabview": {
        "fg_color": BG_PANEL,
        "segmented_button_fg_color": BG_DEEP,
        "segmented_button_selected_color": BG_ELEVATED,
        "segmented_button_selected_hover_color": BORDER_SHINE,
        "segmented_button_unselected_color": BG_PANEL,
        "segmented_button_unselected_hover_color": BG_PANEL_HI,
        "text_color": TEXT,
    },
    "CTkScrollableFrame": {
        "fg_color": BG_PANEL_HI,
        "label_fg_color": BG_PANEL,
    },
}

FONT_TITLE = ("Segoe UI", 22, "bold")
FONT_HEAD = ("Segoe UI", 14, "bold")
FONT_BODY = ("Segoe UI", 12)
FONT_SMALL = ("Segoe UI", 10)
FONT_BALL = ("Segoe UI", 13, "bold")
