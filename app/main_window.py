from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

from app import metadata as meta
from app import theme as T
from app.about_tab import AboutTab
from app.game_tab import GameTab
from app.ultimos_sorteos_tab import UltimosSorteosTab
from loteria_hist import analytics
from loteria_hist.bootstrap_db import ensure_user_database, read_seed_info
from loteria_hist.paths import default_db_path, install_root
from loteria_hist.sync_coordinator import SyncCoordinator, SyncMode

ROOT = install_root()
DEFAULT_DB = default_db_path()

GAME_CONFIG = [
    {
        "key": "euromillones",
        "tab": "Euromillones",
        "accent": T.GAME_ACCENTS["euromillones"],
        "analizar": analytics.analizar_euromillones,
        "grupos": [
            ("principal", "main"),
            ("estrella", "estrella"),
        ],
    },
    {
        "key": "bonoloto",
        "tab": "Bonoloto",
        "accent": T.GAME_ACCENTS["bonoloto"],
        "analizar": analytics.analizar_bonoloto,
        "grupos": [
            ("principal", "main"),
            ("complementario", "complementario"),
            ("reintegro", "reintegro"),
        ],
    },
    {
        "key": "primitiva",
        "tab": "La Primitiva",
        "accent": T.GAME_ACCENTS["primitiva"],
        "analizar": analytics.analizar_primitiva,
        "grupos": [
            ("principal", "main"),
            ("complementario", "complementario"),
            ("reintegro", "reintegro"),
        ],
    },
]


class MainWindow(ctk.CTk):
    def __init__(self, db_path: Path | str | None = None):
        super().__init__()
        self.db_path = Path(db_path or DEFAULT_DB)
        self._sync = SyncCoordinator(self.db_path)
        self._auto_sync_done = False

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        for widget, colors in T.CTK_THEME.items():
            try:
                ctk.ThemeManager.theme[widget].update(colors)
            except (KeyError, TypeError):
                pass

        self.title(f"{meta.APP_NAME} — Análisis histórico")
        self.geometry("1100x780")
        self.minsize(900, 640)
        self.configure(fg_color=T.BG_DEEP)

        self._seed_message = self._ensure_db()
        self._build_ui()
        self.after(120, self._initial_load)
        self.after(400, self._auto_sync_selae)

    def _ensure_db(self) -> str | None:
        applied, msg = ensure_user_database(self.db_path)
        if applied and msg:
            return msg
        return None

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self, fg_color=T.BG_MAIN, corner_radius=0, height=72)
        top.grid(row=0, column=0, sticky="ew")
        top.grid_propagate(False)
        top.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            top,
            text=meta.APP_NAME,
            font=("Segoe UI", 26, "bold"),
            text_color=T.GOLD_BRIGHT,
        ).grid(row=0, column=0, padx=20, pady=16, sticky="w")

        ctk.CTkLabel(
            top,
            text="Estadísticas SELAE · Euromillones · Bonoloto · Primitiva",
            font=T.FONT_BODY,
            text_color=T.TEXT_DIM,
        ).grid(row=0, column=1, padx=8, sticky="w")

        sync_frame = ctk.CTkFrame(top, fg_color="transparent")
        sync_frame.grid(row=0, column=2, padx=20, pady=16)

        self.btn_sync = ctk.CTkButton(
            sync_frame,
            text="Sincronizar SELAE",
            width=160,
            font=T.FONT_BODY,
            fg_color=T.BG_ELEVATED,
            hover_color=T.BORDER_GLOW,
            border_width=1,
            border_color=T.ACCENT,
            command=lambda: self._sync_all_async(SyncMode.INCREMENTAL),
        )
        self.btn_sync.pack(side="left", padx=(0, 6))

        self.btn_sync_full = ctk.CTkButton(
            sync_frame,
            text="Histórico completo",
            width=130,
            font=T.FONT_SMALL,
            fg_color=T.BG_PANEL_HI,
            hover_color=T.BG_ELEVATED,
            border_width=1,
            border_color=T.BORDER,
            command=lambda: self._sync_all_async(SyncMode.FULL),
        )
        self.btn_sync_full.pack(side="left")

        self.tabs = ctk.CTkTabview(
            self,
            fg_color=T.BG_MAIN,
            segmented_button_fg_color=T.BG_DEEP,
            segmented_button_selected_color=T.BG_ELEVATED,
            segmented_button_selected_hover_color=T.BORDER_SHINE,
            segmented_button_unselected_color=T.BG_PANEL,
            segmented_button_unselected_hover_color=T.BG_PANEL_HI,
            text_color=T.TEXT,
            corner_radius=12,
        )
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))
        self.tabs._segmented_button.configure(font=T.FONT_HEAD)

        self.game_tabs: dict[str, GameTab] = {}
        for cfg in GAME_CONFIG:
            self.tabs.add(cfg["tab"])
            frame = self.tabs.tab(cfg["tab"])
            frame.grid_columnconfigure(0, weight=1)
            frame.grid_rowconfigure(0, weight=1)
            tab = GameTab(
                frame,
                juego=cfg["key"],
                titulo=cfg["tab"],
                accent=cfg["accent"],
                db_path=str(self.db_path),
                analizar=cfg["analizar"],
                grupos_sorteo=cfg["grupos"],
                on_status=self._set_status,
            )
            tab.grid(row=0, column=0, sticky="nsew")
            self.game_tabs[cfg["key"]] = tab

        self.tabs.add("Últimos sorteos")
        ultimos_frame = self.tabs.tab("Últimos sorteos")
        ultimos_frame.grid_columnconfigure(0, weight=1)
        ultimos_frame.grid_rowconfigure(0, weight=1)
        juegos_ultimos = [
            (c["key"], c["tab"], c["accent"], c["grupos"]) for c in GAME_CONFIG
        ]
        self.ultimos_tab = UltimosSorteosTab(
            ultimos_frame,
            db_path=str(self.db_path),
            juegos=juegos_ultimos,
            on_status=self._set_status,
        )
        self.ultimos_tab.grid(row=0, column=0, sticky="nsew")

        self.tabs.add("Acerca de")
        about_frame = self.tabs.tab("Acerca de")
        about_frame.grid_columnconfigure(0, weight=1)
        about_frame.grid_rowconfigure(0, weight=1)
        self.about_tab = AboutTab(about_frame, db_path=self.db_path)
        self.about_tab.grid(row=0, column=0, sticky="nsew")

        status_bar = ctk.CTkFrame(self, fg_color=T.BG_PANEL, height=28, corner_radius=0)
        status_bar.grid(row=2, column=0, sticky="ew")
        status_bar.grid_propagate(False)
        self.lbl_status = ctk.CTkLabel(
            status_bar,
            text=f"Base: {self.db_path.name}",
            font=T.FONT_SMALL,
            text_color=T.TEXT_DIM,
            anchor="w",
        )
        self.lbl_status.pack(side="left", padx=12, pady=4)

    def _set_status(self, msg: str) -> None:
        self.lbl_status.configure(text=msg)

    def _initial_load(self) -> None:
        if self._seed_message:
            self._set_status(self._seed_message)
        info = read_seed_info()
        if info and info.get("fecha_max") and not self._seed_message:
            self._set_status(
                f"Base: {self.db_path.name} · histórico hasta {info['fecha_max']}"
            )
        for tab in self.game_tabs.values():
            tab.load_async()
        if hasattr(self, "ultimos_tab"):
            self.ultimos_tab.load_async()
        if hasattr(self, "about_tab"):
            self.about_tab.refresh_db_status()

    def _auto_sync_selae(self) -> None:
        if self._auto_sync_done:
            return
        self._auto_sync_done = True
        self._sync_all_async(
            SyncMode.INCREMENTAL,
            reason="inicio",
            quiet_if_busy=False,
        )

    def _set_sync_ui_busy(self, busy: bool) -> None:
        if busy:
            self.btn_sync.configure(state="disabled", text="Sincronizando…")
            self.btn_sync_full.configure(state="disabled")
        else:
            self.btn_sync.configure(state="normal", text="Sincronizar SELAE")
            self.btn_sync_full.configure(state="normal")

    def _reload_after_sync(self) -> None:
        for tab in self.game_tabs.values():
            tab.load_async()
        if hasattr(self, "ultimos_tab"):
            self.ultimos_tab.load_async()
        if hasattr(self, "about_tab"):
            self.about_tab.refresh_db_status()

    def _sync_all_async(
        self,
        mode: SyncMode,
        *,
        reason: str = "manual",
        quiet_if_busy: bool = True,
    ) -> None:
        juegos = [c["key"] for c in GAME_CONFIG]
        if self._sync.is_running:
            if quiet_if_busy and reason == "inicio":
                return
            self._set_status("Sincronización en curso…")

        self._set_sync_ui_busy(True)
        etiqueta = (
            "novedades SELAE"
            if mode == SyncMode.INCREMENTAL
            else "histórico completo SELAE"
        )
        self._set_status(f"Descargando {etiqueta}…")

        def on_progress(msg: str) -> None:
            self.after(0, lambda m=msg: self._set_status(m[:120]))

        def on_done(result) -> None:
            if not self._sync.is_running:
                self._set_sync_ui_busy(False)
            if isinstance(result, Exception):
                self._set_status(f"Error SELAE: {result}")
                return
            parts = [f"{k}: +{v}" for k, v in result.totals.items()]
            modo = "incremental" if result.mode == SyncMode.INCREMENTAL else "completa"
            self._set_status(f"SELAE ({modo}) OK · " + " · ".join(parts))
            self._reload_after_sync()

        started = self._sync.request(
            juegos,
            mode=mode,
            reason=reason,
            on_progress=on_progress,
            on_done=on_done,
            schedule=lambda fn: self.after(0, fn),
        )
        if not started:
            self._set_sync_ui_busy(True)
