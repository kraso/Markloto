from __future__ import annotations

import sqlite3
import threading
from collections.abc import Callable
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app import theme as T
from app.widgets import BallRow, FreqGrid, MetallicPanel
from loteria_hist import repository
from loteria_hist.export_xlsx import exportar_sorteos_periodo
from loteria_hist.periodos import ETIQUETAS_PERIODO_UI
from loteria_hist.ultimos_data import DatosUltimosSorteos, cargar_datos

TIPO_LABEL = {
    "principal": "Números principales",
    "estrella": "Estrellas",
    "complementario": "Complementario",
    "reintegro": "Reintegro",
}


class UltimosSorteosTab(ctk.CTkFrame):
    """Pestaña con último sorteo destacado y resumen histórico por periodo."""

    def __init__(
        self,
        master,
        *,
        db_path: str,
        juegos: list[tuple[str, str, str, list[tuple[str, str]]]],
        on_status: Callable[[str], None] | None = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.db_path = db_path
        self._juegos = juegos
        self._on_status = on_status or (lambda _: None)
        self._loading = False
        self._load_gen = 0
        self._hot: set[int] = set()
        self._datos_actual: DatosUltimosSorteos | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctrl = ctk.CTkFrame(self, fg_color=T.BG_PANEL, corner_radius=8)
        ctrl.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        ctrl_inner = ctk.CTkFrame(ctrl, fg_color="transparent")
        ctrl_inner.pack(fill="x", padx=12, pady=10)

        ctk.CTkLabel(ctrl_inner, text="Juego:", font=T.FONT_BODY).pack(
            side="left", padx=(0, 8)
        )
        labels = [j[1] for j in juegos]
        self._var_juego = ctk.StringVar(value=labels[0] if labels else "")
        self._menu_juego = ctk.CTkOptionMenu(
            ctrl_inner,
            variable=self._var_juego,
            values=labels,
            width=160,
            command=self._on_filter_change,
        )
        self._menu_juego.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(ctrl_inner, text="Resumen histórico:", font=T.FONT_BODY).pack(
            side="left", padx=(0, 8)
        )
        self._periodo_labels = dict(ETIQUETAS_PERIODO_UI)
        self._var_periodo = ctk.StringVar(value="Trimestre actual")
        ctk.CTkOptionMenu(
            ctrl_inner,
            variable=self._var_periodo,
            values=list(self._periodo_labels.keys()),
            width=175,
            command=self._on_filter_change,
        ).pack(side="left", padx=(0, 12))

        ctk.CTkButton(
            ctrl_inner,
            text="Descargar Excel",
            width=130,
            font=T.FONT_SMALL,
            fg_color=T.ACCENT,
            hover_color=T.ACCENT_BRIGHT,
            text_color=T.BG_DEEP,
            command=self._exportar_xlsx,
        ).pack(side="right", padx=(6, 0))

        ctk.CTkButton(
            ctrl_inner,
            text="Actualizar",
            width=100,
            font=T.FONT_SMALL,
            fg_color=T.BG_ELEVATED,
            border_width=1,
            border_color=T.ACCENT,
            command=self.load_async,
        ).pack(side="right")

        scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=T.BG_ELEVATED,
            scrollbar_button_hover_color=T.BORDER_SHINE,
        )
        scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        scroll.grid_columnconfigure(0, weight=1)

        self._hero = MetallicPanel(
            scroll,
            title="Último sorteo",
            accent=T.GOLD_BRIGHT,
        )
        self._hero.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        self._hero_meta = ctk.CTkLabel(
            self._hero.body,
            text="Cargando…",
            font=("Segoe UI", 20, "bold"),
            text_color=T.TEXT,
            anchor="w",
        )
        self._hero_meta.pack(anchor="w", pady=(0, 8))
        self._hero_bote = ctk.CTkLabel(
            self._hero.body,
            text="",
            font=T.FONT_BODY,
            text_color=T.TEXT_DIM,
            anchor="w",
        )
        self._hero_bote.pack(anchor="w", pady=(0, 12))
        self._hero_balls = BallRow(self._hero.body)
        self._hero_balls.pack(anchor="w")

        self._resumen = MetallicPanel(
            scroll,
            title="Resumen del periodo",
            accent=T.ACCENT_BRIGHT,
        )
        self._resumen.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        self._lbl_periodo = ctk.CTkLabel(
            self._resumen.body,
            text="",
            font=T.FONT_BODY,
            text_color=T.TEXT_DIM,
            wraplength=900,
            justify="left",
        )
        self._lbl_periodo.pack(anchor="w", pady=(0, 10))

        self._freq_container = ctk.CTkFrame(self._resumen.body, fg_color="transparent")
        self._freq_container.pack(fill="x")
        self._freq_grids: dict[str, FreqGrid] = {}

        self._lista = MetallicPanel(
            scroll,
            title="Sorteos del periodo",
            accent=T.SILVER_BRIGHT,
        )
        self._lista.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        self._lista_body = ctk.CTkFrame(self._lista.body, fg_color="transparent")
        self._lista_body.pack(fill="x")

    def _cfg_actual(self) -> tuple[str, str, str, list[tuple[str, str]]]:
        label = self._var_juego.get()
        for key, tab, accent, grupos in self._juegos:
            if tab == label:
                return key, tab, accent, grupos
        return self._juegos[0]

    def _on_filter_change(self, _value: str = "") -> None:
        self.load_async()

    def load_async(self) -> None:
        self._load_gen += 1
        gen = self._load_gen
        self._loading = True
        self._on_status("Últimos sorteos: cargando…")
        key, _tab, _accent, grupos = self._cfg_actual()
        modo = self._periodo_labels.get(self._var_periodo.get(), "trimestre")

        def work() -> DatosUltimosSorteos:
            conn = sqlite3.connect(self.db_path, timeout=30)
            try:
                return cargar_datos(conn, key, grupos, modo)
            finally:
                conn.close()

        def done(result: DatosUltimosSorteos | Exception) -> None:
            if gen != self._load_gen:
                return
            self._loading = False
            if not self.winfo_exists():
                return
            if isinstance(result, Exception):
                self._hero_meta.configure(text=f"Error: {result}")
                self._on_status("Últimos sorteos: error")
                return
            try:
                self._render(result)
                self._datos_actual = result
            except Exception as exc:
                self._hero_meta.configure(text=f"Error al mostrar: {exc}")
                self._on_status("Últimos sorteos: error")
                return
            self._on_status("Últimos sorteos: listo")

        def thread_main() -> None:
            try:
                out = work()
                self.after(0, lambda o=out: done(o))
            except Exception as e:
                self.after(0, lambda err=e: done(err))

        threading.Thread(target=thread_main, daemon=True).start()

    def _render(self, datos: DatosUltimosSorteos) -> None:
        _key, tab, accent, grupos = self._cfg_actual()
        self._resumen.configure_border_color=accent  # type: ignore[attr-defined]

        if not datos.ultimo:
            self._datos_actual = datos
            self._hero_meta.configure(text=f"{tab} — sin sorteos en la base")
            self._hero_bote.configure(text="")
            self._hero_balls.set_numbers([])
            self._lbl_periodo.configure(
                text="Sincroniza con SELAE para cargar histórico."
            )
            return

        u = datos.ultimo
        fecha_txt = u.fecha
        if u.dia_semana:
            fecha_txt += f"  ·  {u.dia_semana}"
        self._hero_meta.configure(text=fecha_txt)
        self._hero_bote.configure(
            text=u.premio_bote if u.premio_bote else "Último resultado registrado"
        )

        groups: list[tuple[list[int], str]] = []
        for tipo, kind in grupos:
            vals = u.numeros.get(tipo, [])
            if vals:
                groups.append((vals, kind))
        self._hot = {n for nums, _ in groups for n in nums}
        self._hero_balls.set_numbers(groups, hot_sets=self._hot, ball_size=56)

        n_sorteos = len(datos.sorteos_periodo)
        self._lbl_periodo.configure(
            text=(
                f"{datos.periodo.etiqueta} · {n_sorteos} sorteo(s) · "
                f"Frecuencia = veces que salió cada número como premiado en el periodo."
            )
        )

        for child in self._freq_container.winfo_children():
            child.destroy()
        self._freq_grids.clear()

        col = 0
        row = 0
        for tipo, _kind in grupos:
            fg = FreqGrid(
                self._freq_container,
                title=TIPO_LABEL.get(tipo, tipo),
                accent=accent,
                height=160,
            )
            fg.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
            freq = datos.frecuencias.get(tipo, [])
            fg.load(freq, top=20)
            top5 = {n for n, _ in freq[:5]}
            self._hot |= top5
            col += 1
            if col > 1:
                col = 0
                row += 1

        for child in self._lista_body.winfo_children():
            child.destroy()
        if not datos.sorteos_periodo:
            ctk.CTkLabel(
                self._lista_body,
                text="No hay sorteos en este periodo.",
                text_color=T.TEXT_DIM,
            ).pack(anchor="w")
            return

        for s in datos.sorteos_periodo[:40]:
            row_f = ctk.CTkFrame(
                self._lista_body,
                fg_color=T.BG_PANEL_HI,
                corner_radius=8,
                border_width=1,
                border_color=T.BORDER,
            )
            row_f.pack(fill="x", pady=3)
            left = ctk.CTkFrame(row_f, fg_color="transparent", width=120)
            left.pack(side="left", padx=10, pady=8)
            left.pack_propagate(False)
            ctk.CTkLabel(
                left,
                text=s.fecha,
                font=T.FONT_BODY,
                text_color=T.TEXT,
            ).pack(anchor="w")
            if s.dia_semana:
                ctk.CTkLabel(
                    left,
                    text=s.dia_semana,
                    font=T.FONT_SMALL,
                    text_color=T.TEXT_DIM,
                ).pack(anchor="w")
            gr: list[tuple[list[int], str]] = []
            for tipo, kind in grupos:
                vals = s.numeros.get(tipo, [])
                if vals:
                    gr.append((vals, kind))
            br = BallRow(row_f)
            br.pack(side="left", padx=4, pady=8)
            br.set_numbers(gr, hot_sets=self._hot, ball_size=34)

        if len(datos.sorteos_periodo) > 40:
            ctk.CTkLabel(
                self._lista_body,
                text=f"… y {len(datos.sorteos_periodo) - 40} sorteos más en el periodo.",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
            ).pack(anchor="w", pady=6)

    def _exportar_xlsx(self) -> None:
        datos = self._datos_actual
        if not datos or not datos.sorteos_periodo:
            messagebox.showwarning(
                "Exportar Excel",
                "No hay sorteos en el periodo seleccionado.\n"
                "Elige un juego y periodo con datos y pulsa Actualizar.",
                parent=self.winfo_toplevel(),
            )
            return

        key, tab, _accent, _grupos = self._cfg_actual()
        modo = datos.periodo.modo
        safe_modo = modo.replace(" ", "_")
        default = f"{tab}_{safe_modo}_sorteos.xlsx"
        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            title="Guardar sorteos en Excel",
            defaultextension=".xlsx",
            initialfile=default,
            filetypes=[("Excel", "*.xlsx"), ("Todos", "*.*")],
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"

        try:
            n = exportar_sorteos_periodo(
                path,
                key,
                datos.periodo.etiqueta,
                datos.sorteos_periodo,
            )
        except Exception as exc:
            messagebox.showerror(
                "Exportar Excel",
                f"No se pudo guardar el archivo:\n{exc}",
                parent=self.winfo_toplevel(),
            )
            self._on_status("Últimos sorteos: error al exportar")
            return

        self._on_status(f"Últimos sorteos: exportados {n} sorteos")
        messagebox.showinfo(
            "Exportar Excel",
            f"Archivo guardado:\n{path}\n\n{n} sorteo(s) exportado(s).",
            parent=self.winfo_toplevel(),
        )
