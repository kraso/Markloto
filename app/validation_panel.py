from __future__ import annotations

import sqlite3
import threading

import customtkinter as ctk

from app import theme as T
from app.widgets import MetallicPanel
from loteria_hist import validacion as val
from loteria_hist.apuestas import REGLAS
from loteria_hist.validacion import FilaValidacionSorteo, InformeValidacion

TIPO_LABEL = {
    "principal": "Principales",
    "estrella": "Estrellas",
    "complementario": "Comp.",
    "reintegro": "Reint.",
}


class ValidationPanel(ctk.CTkFrame):
    """Backtesting: % acierto de la heurística vs azar por sorteo."""

    def __init__(
        self,
        master,
        *,
        juego: str,
        accent: str,
        db_path: str,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.juego = juego
        self.accent = accent
        self.db_path = db_path
        reglas = REGLAS[juego]
        self._numeros = (
            reglas.base_principal if juego == "euromillones" else 7
        )
        self._estrellas: int | None = 2 if juego == "euromillones" else None
        self._informe: InformeValidacion | None = None
        self._loading = False

        panel = MetallicPanel(
            self,
            title="Validación histórica de la heurística",
            accent=accent,
        )
        panel.pack(fill="x")
        panel.body.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            panel.body,
            text=(
                "Por cada sorteo se calcula el bloque «más probable» solo con datos "
                "anteriores y se mide cuántas bolas ganadoras caían en ese bloque. "
                "Se compara con el rendimiento teórico del azar."
            ),
            font=T.FONT_SMALL,
            text_color=T.TEXT_DIM,
            wraplength=900,
            justify="left",
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        self._lbl_resumen = ctk.CTkLabel(
            panel.body,
            text="Pulsa recalcular o cambia el tamaño del bloque en apuestas múltiples.",
            font=T.FONT_BODY,
            text_color=T.TEXT,
            justify="left",
            anchor="w",
            wraplength=900,
        )
        self._lbl_resumen.grid(row=1, column=0, sticky="w", pady=(0, 8))

        self.btn_recalc = ctk.CTkButton(
            panel.body,
            text="Recalcular validación",
            width=160,
            font=T.FONT_SMALL,
            fg_color=T.BG_ELEVATED,
            border_width=1,
            border_color=accent,
            command=self.load_async,
        )
        self.btn_recalc.grid(row=2, column=0, sticky="w", pady=(0, 8))

        hdr = ctk.CTkFrame(panel.body, fg_color=T.BG_ELEVATED, corner_radius=6)
        hdr.grid(row=3, column=0, sticky="ew", pady=(4, 2))
        for i, txt in enumerate(("Fecha", "% acierto", "Detalle aciertos")):
            ctk.CTkLabel(
                hdr,
                text=txt,
                font=T.FONT_SMALL,
                text_color=accent,
                width=120 if i == 0 else 90,
            ).grid(row=0, column=i, padx=6, pady=4, sticky="w")

        ctk.CTkLabel(
            panel.body,
            text="Mayor correspondencia (top del histórico evaluado)",
            font=T.FONT_SMALL,
            text_color=T.SILVER_BRIGHT,
        ).grid(row=4, column=0, sticky="w", pady=(10, 4))

        self._rows_mejores = ctk.CTkFrame(panel.body, fg_color="transparent")
        self._rows_mejores.grid(row=5, column=0, sticky="ew")

        ctk.CTkLabel(
            panel.body,
            text="Últimos sorteos evaluados",
            font=T.FONT_SMALL,
            text_color=T.TEXT_DIM,
        ).grid(row=6, column=0, sticky="w", pady=(10, 4))

        self._rows_ultimos = ctk.CTkFrame(panel.body, fg_color="transparent")
        self._rows_ultimos.grid(row=7, column=0, sticky="ew", pady=(0, 8))

    def set_tamano_bloque(
        self,
        numeros_marcados: int,
        estrellas_marcadas: int | None = None,
    ) -> None:
        prev = (self._numeros, self._estrellas)
        self._numeros = numeros_marcados
        self._estrellas = estrellas_marcadas
        if prev == (numeros_marcados, estrellas_marcadas):
            return
        if self._informe and not self._loading:
            self.load_async()

    def load_async(self) -> None:
        if self._loading:
            return
        self._loading = True
        self.btn_recalc.configure(state="disabled")
        self._lbl_resumen.configure(text="Calculando validación walk-forward…")

        n, est = self._numeros, self._estrellas

        def work() -> InformeValidacion:
            conn = sqlite3.connect(self.db_path)
            try:
                return val.ejecutar_backtest(
                    conn,
                    self.juego,
                    numeros_marcados=n,
                    estrellas_marcadas=est,
                )
            finally:
                conn.close()

        def done(result: InformeValidacion | Exception) -> None:
            self._loading = False
            self.btn_recalc.configure(state="normal")
            if isinstance(result, Exception):
                self._lbl_resumen.configure(text=f"Error: {result}")
                return
            self._informe = result
            self._render_informe(result)

        def thread_main() -> None:
            try:
                out = work()
                self.after(0, lambda: done(out))
            except Exception as e:
                self.after(0, lambda: done(e))

        threading.Thread(target=thread_main, daemon=True).start()

    def _render_informe(self, inf: InformeValidacion) -> None:
        bloque = f"{inf.numeros_marcados} números"
        if inf.estrellas_marcadas:
            bloque += f" + {inf.estrellas_marcadas} estrellas"

        lineas = [
            f"Bloque evaluado: {bloque} · {inf.sorteos_evaluados:,} sorteos "
            f"(omitidos {inf.warmup_omitidos:,} iniciales sin historial)".replace(",", "."),
            f"Media global de acierto en bloque: {inf.media_pct_global:.2f} %",
            f"Azar teórico (tamaño del bloque / bombo): {inf.esperado_pct_global:.2f} %",
            f"Diferencia heurística − azar: {inf.media_pct_global - inf.esperado_pct_global:+.2f} p.p.",
            f"Primer tercio histórico: {inf.media_primer_tercio:.2f} % · "
            f"Último tercio: {inf.media_ultimo_tercio:.2f} %",
            "",
        ]
        for tipo, pct in inf.resumen.items():
            if tipo.endswith("_aciertos"):
                continue
            diff = inf.diferencia_vs_azar.get(tipo, 0.0)
            ac = inf.resumen.get(f"{tipo}_aciertos", 0.0)
            esp = inf.esperado_azar.get(f"{tipo}_aciertos", 0.0)
            lineas.append(
                f"  {TIPO_LABEL.get(tipo, tipo)}: {pct:.2f} % en bloque "
                f"({ac:.2f} aciertos/sorteo vs {esp:.2f} al azar, {diff:+.2f} p.p.)"
            )
        lineas.append("")
        lineas.append(inf.conclusion)
        self._lbl_resumen.configure(text="\n".join(lineas))

        self._fill_rows(self._rows_mejores, inf.mejores[:10])
        self._fill_rows(self._rows_ultimos, inf.ultimos)

    def _fill_rows(
        self,
        container: ctk.CTkFrame,
        filas: list[FilaValidacionSorteo],
    ) -> None:
        for child in container.winfo_children():
            child.destroy()
        for f in filas:
            row = ctk.CTkFrame(
                container,
                fg_color=T.BG_PANEL_HI,
                corner_radius=4,
            )
            row.pack(fill="x", pady=1)
            det = " · ".join(
                f"{TIPO_LABEL.get(t, t)} {f.aciertos[t]}/{f.bolas_sorteo.get(t, 0)}"
                for t in f.aciertos
            )
            ctk.CTkLabel(
                row,
                text=f.fecha,
                font=T.FONT_SMALL,
                width=110,
                anchor="w",
            ).grid(row=0, column=0, padx=6, pady=3, sticky="w")
            color = T.GOLD_BRIGHT if f.pct_medio >= 50 else T.TEXT
            ctk.CTkLabel(
                row,
                text=f"{f.pct_medio:.1f} %",
                font=T.FONT_SMALL,
                text_color=color,
                width=70,
                anchor="w",
            ).grid(row=0, column=1, padx=4, pady=3, sticky="w")
            ctk.CTkLabel(
                row,
                text=det,
                font=T.FONT_SMALL,
                text_color=T.TEXT_DIM,
                anchor="w",
            ).grid(row=0, column=2, padx=4, pady=3, sticky="w")
