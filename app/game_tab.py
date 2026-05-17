from __future__ import annotations

import threading
from collections.abc import Callable
import customtkinter as ctk

from app import theme as T
from app.bet_calculator import MultipleBetPanel
from app.user_bet_panel import UserBetPanel
from app.validation_panel import ValidationPanel
from app.widgets import BallRow, FreqGrid, MetallicPanel, NumberBall
from pathlib import Path

from loteria_hist import analysis_cache, analytics, db, repository
from loteria_hist.analytics import AnalisisJuego

TIPO_LABEL = {
    "principal": "Números principales",
    "estrella": "Estrellas",
    "complementario": "Complementario",
    "reintegro": "Reintegro",
}


class GameTab(ctk.CTkFrame):
    """Pestaña de estadísticas para un juego."""

    def __init__(
        self,
        master,
        *,
        juego: str,
        titulo: str,
        accent: str,
        db_path: str,
        analizar: Callable[[sqlite3.Connection], AnalisisJuego],
        grupos_sorteo: list[tuple[str, str]],
        on_status: Callable[[str], None] | None = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.juego = juego
        self.titulo = titulo
        self.accent = accent
        self.db_path = db_path
        self._analizar = analizar
        self._grupos_sorteo = grupos_sorteo
        self._on_status = on_status or (lambda _: None)
        self._analisis: AnalisisJuego | None = None
        self._hot: set[int] = set()
        self._loading = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_body()

    def _on_block_size_change(self, numeros: int, estrellas: int | None) -> None:
        if hasattr(self, "validation"):
            self.validation.set_tamano_bloque(numeros, estrellas)

    def _build_header(self) -> None:
        hdr = MetallicPanel(self, title=self.titulo, accent=self.accent)
        hdr.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 8))
        hdr.body.grid_columnconfigure(0, weight=1)

        self.lbl_resumen = ctk.CTkLabel(
            hdr.body,
            text="Cargando…",
            font=T.FONT_BODY,
            text_color=T.TEXT_DIM,
            anchor="w",
        )
        self.lbl_resumen.grid(row=0, column=0, sticky="w")

        actions = ctk.CTkFrame(hdr.body, fg_color="transparent")
        actions.grid(row=0, column=1, sticky="e", padx=(12, 0))

        self.btn_refresh = ctk.CTkButton(
            actions,
            text="Actualizar vista",
            width=130,
            font=T.FONT_SMALL,
            fg_color=T.BG_ELEVATED,
            hover_color=T.BORDER_SHINE,
            border_width=1,
            border_color=self.accent,
            command=lambda: self.load_async(force=True),
        )
        self.btn_refresh.pack(side="left", padx=4)

        self.btn_suggest = ctk.CTkButton(
            actions,
            text="Nueva sugerencia",
            width=140,
            font=T.FONT_SMALL,
            fg_color=self.accent,
            hover_color=T.ACCENT,
            text_color=T.BG_DEEP,
            command=self._nueva_sugerencia,
        )
        self.btn_suggest.pack(side="left", padx=4)

    def _build_body(self) -> None:
        scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=T.BG_ELEVATED,
            scrollbar_button_hover_color=T.BORDER_SHINE,
        )
        scroll.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        scroll.grid_columnconfigure(0, weight=1)
        scroll.grid_columnconfigure(1, weight=1)

        # Sugerencia heurística
        sug = MetallicPanel(
            scroll,
            title="Sugerencias — heurística y apuesta múltiple",
            accent=self.accent,
        )
        sug.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.sug_row = BallRow(sug.body)
        self.sug_row.pack(anchor="w", pady=4)
        ctk.CTkLabel(
            sug.body,
            text="Solo describe frecuencias pasadas; no predice resultados.",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
        ).pack(anchor="w")

        self.user_bet = UserBetPanel(
            scroll,
            juego=self.juego,
            accent=self.accent,
            grupos_sorteo=self._grupos_sorteo,
        )
        self.user_bet.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        self.bet_calc = MultipleBetPanel(
            scroll,
            juego=self.juego,
            accent=self.accent,
            grupos_sorteo=self._grupos_sorteo,
        )
        self.bet_calc.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        self.validation = ValidationPanel(
            scroll,
            juego=self.juego,
            accent=self.accent,
            db_path=self.db_path,
        )
        self.validation.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.bet_calc.on_block_change = self._on_block_size_change

        # Frecuencias
        self.freq_frames: dict[str, FreqGrid] = {}
        row_f = 4
        col = 0
        for tipo, _kind in self._grupos_sorteo:
            fg = FreqGrid(
                scroll,
                title=f"Top frecuencia — {TIPO_LABEL.get(tipo, tipo)}",
                accent=self.accent,
            )
            fg.grid(row=row_f, column=col, sticky="nsew", padx=4, pady=4)
            self.freq_frames[tipo] = fg
            col += 1
            if col > 1:
                col = 0
                row_f += 1

        # Retrasos
        delay_panel = MetallicPanel(scroll, title="Mayor retraso (sorteos sin salir)", accent=T.ROSE)
        delay_panel.grid(row=row_f + 1, column=0, columnspan=2, sticky="ew", pady=8)
        self.delay_body = ctk.CTkFrame(delay_panel.body, fg_color="transparent")
        self.delay_body.pack(fill="x")

        # Últimos sorteos
        hist = MetallicPanel(scroll, title="Últimos sorteos", accent=T.SILVER_BRIGHT)
        hist.grid(row=row_f + 2, column=0, columnspan=2, sticky="ew", pady=8)
        self.hist_list = ctk.CTkFrame(hist.body, fg_color="transparent")
        self.hist_list.pack(fill="both", expand=True)

    def load_async(self, *, force: bool = False) -> None:
        if self._loading:
            return
        self._loading = True
        self.btn_refresh.configure(state="disabled")
        self.lbl_resumen.configure(text="Cargando datos…")
        self._on_status(f"{self.titulo}: cargando…")

        def work() -> tuple[AnalisisJuego, list[repository.SorteoVista]]:
            db_path = Path(self.db_path)
            if not force:
                cached = analysis_cache.load(db_path, self.juego)
            else:
                cached = None
            conn = db.connect(self.db_path)
            try:
                ult = repository.ultimos_sorteos(conn, self.juego, limit=8)
                if cached is not None:
                    return cached, ult
                a = self._analizar(conn)
                analysis_cache.save(db_path, self.juego, a)
                return a, ult
            finally:
                conn.close()

        # Validación walk-forward: solo bajo demanda (Recalcular). Evita 3 backtests
        # completos al arrancar, que bloquean la UI en Linux.

        def done(result: tuple[AnalisisJuego, list[repository.SorteoVista]] | Exception) -> None:
            self._loading = False
            self.btn_refresh.configure(state="normal")
            if isinstance(result, Exception):
                self.lbl_resumen.configure(text=f"Error: {result}")
                self._on_status(f"{self.titulo}: error")
                return
            analisis, ultimos = result
            self._apply(analisis, ultimos)
            self._on_status(f"{self.titulo}: listo")

        def thread_main() -> None:
            try:
                out = work()
                self.after(0, lambda: done(out))
            except Exception as e:
                self.after(0, lambda: done(e))

        threading.Thread(target=thread_main, daemon=True).start()

    def _apply(
        self,
        analisis: AnalisisJuego,
        ultimos: list[repository.SorteoVista],
    ) -> None:
        self._analisis = analisis
        r = analisis.resumen
        self.lbl_resumen.configure(
            text=(
                f"{r.total:,} sorteos · {r.fecha_min or '—'} → {r.fecha_max or '—'}"
                + (f" · {r.fuente}" if r.fuente else "")
            ).replace(",", ".")
        )

        freq_p = analisis.frecuencias.get("principal", [])
        self._hot = {n for n, _ in freq_p[:8]}

        self._render_sugerencia(analisis.sugerencia, defer_bet_table=True)

        def fase_frecuencias() -> None:
            if not self.winfo_exists():
                return
            for tipo, fg in self.freq_frames.items():
                fg.load(analisis.frecuencias.get(tipo, []), top=10)

        def fase_paneles() -> None:
            if not self.winfo_exists():
                return
            self.bet_calc.set_analisis(analisis, self._hot, refresh_table=False)

        def fase_pesada() -> None:
            if not self.winfo_exists():
                return
            self._render_delays(analisis)
            self._render_historial(ultimos)
            self.user_bet.set_analisis(analisis, self._hot)
            self.bet_calc.refresh_table_deferred()

        self.after(1, fase_frecuencias)
        self.after(40, fase_paneles)
        self.after(80, fase_pesada)

    def _render_delays(self, analisis: AnalisisJuego) -> None:
        for child in self.delay_body.winfo_children():
            child.destroy()
        col_frame: ctk.CTkFrame | None = None
        for i, (tipo, _kind) in enumerate(self._grupos_sorteo):
            if i % 2 == 0:
                col_frame = ctk.CTkFrame(self.delay_body, fg_color="transparent")
                col_frame.pack(fill="x", pady=4)
            retrasos = analisis.retrasos.get(tipo, [])[:6]
            block = ctk.CTkFrame(col_frame, fg_color=T.BG_PANEL_HI, corner_radius=8)
            block.pack(side="left", fill="x", expand=True, padx=4)
            ctk.CTkLabel(
                block,
                text=TIPO_LABEL.get(tipo, tipo),
                font=T.FONT_SMALL,
                text_color=self.accent,
            ).pack(anchor="w", padx=8, pady=(6, 2))
            balls = ctk.CTkFrame(block, fg_color="transparent")
            balls.pack(anchor="w", padx=8, pady=(0, 8))
            for num, delay in retrasos:
                wrap = ctk.CTkFrame(balls, fg_color="transparent")
                wrap.pack(side="left", padx=2)
                NumberBall(wrap, num, kind=tipo if tipo != "principal" else "main", hot=True, size=34).pack()
                ctk.CTkLabel(
                    wrap,
                    text=f"{delay}",
                    font=T.FONT_SMALL,
                    text_color=T.TEXT_MUTED,
                ).pack()

    def _render_sugerencia(
        self,
        sug: dict[str, list[int]],
        *,
        defer_bet_table: bool = False,
    ) -> None:
        groups: list[tuple[list[int], str]] = []
        for tipo, kind in self._grupos_sorteo:
            vals = sug.get(tipo, [])
            if vals:
                groups.append((vals, kind))
        self.sug_row.set_numbers(groups, hot_sets=self._hot)
        principales = sug.get("principal", [])
        if principales and hasattr(self, "bet_calc"):
            n = len(principales)
            opts = self.bet_calc._spin_nums.cget("values")
            if str(n) in opts:
                self.bet_calc._var_nums.set(str(n))
                if defer_bet_table:
                    self.bet_calc._update_combo_recomendada()
                else:
                    self.bet_calc._on_selection_change()

    def _nueva_sugerencia(self) -> None:
        if not self._analisis:
            self.load_async()
            return
        import random

        semilla = random.randint(0, 2**31 - 1)
        self._render_sugerencia(
            analytics.nueva_sugerencia(self._analisis, self.juego, semilla=semilla)
        )

    def _render_historial(self, ultimos: list[repository.SorteoVista]) -> None:
        """Lista compacta (menos widgets = carga mucho más rápida en Linux)."""
        for child in self.hist_list.winfo_children():
            child.destroy()
        for s in ultimos:
            nums_txt: list[str] = []
            for tipo, _kind in self._grupos_sorteo:
                vals = s.numeros.get(tipo, [])
                if vals:
                    label = TIPO_LABEL.get(tipo, tipo)[:4]
                    nums_txt.append(
                        f"{label}: " + ", ".join(f"{v:02d}" for v in vals)
                    )
            line = f"{s.fecha}"
            if s.dia_semana:
                line += f" ({s.dia_semana})"
            if nums_txt:
                line += " — " + " · ".join(nums_txt)
            ctk.CTkLabel(
                self.hist_list,
                text=line,
                font=T.FONT_SMALL,
                text_color=T.TEXT,
                anchor="w",
                justify="left",
                wraplength=820,
            ).pack(fill="x", padx=4, pady=2)
