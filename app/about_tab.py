from __future__ import annotations

import webbrowser

import customtkinter as ctk

from pathlib import Path

from app import metadata as meta
from app import theme as T
from app.widgets import MetallicPanel
from loteria_hist.bootstrap_db import texto_bd_local, texto_historico_embebido


class AboutTab(ctk.CTkFrame):
    """Pestaña Acerca de."""

    def __init__(self, master, *, db_path: str | Path | None = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._db_path = Path(db_path) if db_path else None
        self._lbl_bd_local: ctk.CTkLabel | None = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=T.BG_ELEVATED,
            scrollbar_button_hover_color=T.BORDER_SHINE,
        )
        scroll.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        scroll.grid_columnconfigure(0, weight=1)

        panel = MetallicPanel(scroll, title="Acerca de", accent=T.GOLD_BRIGHT)
        panel.grid(row=0, column=0, sticky="new", pady=(0, 12))
        panel.body.grid_columnconfigure(1, weight=1)

        version = meta.app_version()
        fields: list[tuple[str, str]] = [
            ("Nombre de la App", meta.APP_NAME),
            ("Versión", version),
            ("Autor", meta.AUTHOR),
            ("Email", meta.EMAIL),
            ("Fecha de creación", meta.CREATION_DATE),
        ]
        embebido = texto_historico_embebido()
        if embebido:
            fields.append(("Histórico embebido", embebido))
        if self._db_path is not None:
            local = texto_bd_local(self._db_path) or "—"
            fields.append(("Base de datos local", local))

        for row, (label, value) in enumerate(fields):
            ctk.CTkLabel(
                panel.body,
                text=label,
                font=T.FONT_BODY,
                text_color=T.TEXT_DIM,
                anchor="e",
                width=160,
            ).grid(row=row, column=0, padx=(0, 12), pady=8, sticky="ne")
            if label == "Email":
                btn = ctk.CTkButton(
                    panel.body,
                    text=value,
                    font=T.FONT_BODY,
                    fg_color="transparent",
                    hover_color=T.BG_ELEVATED,
                    text_color=T.ACCENT_BRIGHT,
                    anchor="w",
                    height=28,
                    command=lambda: webbrowser.open(f"mailto:{meta.EMAIL}"),
                )
                btn.grid(row=row, column=1, sticky="w", pady=8)
            else:
                weight = "bold" if label == "Nombre de la App" else "normal"
                font = (T.FONT_BODY[0], T.FONT_BODY[1], weight)
                tc = T.GOLD_BRIGHT if label == "Nombre de la App" else T.TEXT
                lbl = ctk.CTkLabel(
                    panel.body,
                    text=value,
                    font=font,
                    text_color=tc,
                    anchor="w",
                    justify="left",
                )
                lbl.grid(row=row, column=1, sticky="w", pady=8)
                if label == "Base de datos local":
                    self._lbl_bd_local = lbl

    def refresh_db_status(self) -> None:
        if self._db_path is None or self._lbl_bd_local is None:
            return
        self._lbl_bd_local.configure(text=texto_bd_local(self._db_path) or "—")

        info = MetallicPanel(
            scroll,
            title="Información adicional",
            accent=T.ACCENT_BRIGHT,
        )
        info.grid(row=1, column=0, sticky="ew")
        ctk.CTkLabel(
            info.body,
            text=meta.ABOUT_TEXT,
            font=T.FONT_BODY,
            text_color=T.TEXT,
            wraplength=720,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=4, pady=4)

        ctk.CTkLabel(
            scroll,
            text="Los sorteos son aleatorios. Markloto no garantiza premios ni predice resultados.",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            wraplength=720,
            justify="left",
        ).grid(row=2, column=0, sticky="w", pady=(16, 8))
