from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from app import theme as T
from app.widgets import BallRow, MetallicPanel
from loteria_hist import analytics, apuestas as ap
from loteria_hist.analytics import AnalisisJuego

TIPO_LABEL = {
    "principal": "Principales",
    "estrella": "Estrellas",
    "complementario": "Complementario",
    "reintegro": "Reintegro",
}


class MultipleBetPanel(ctk.CTkFrame):
    """Tabla de apuestas múltiples: combinaciones, coste y probabilidades."""

    def __init__(
        self,
        master,
        *,
        juego: str,
        accent: str,
        grupos_sorteo: list[tuple[str, str]] | None = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.juego = juego
        self.accent = accent
        self._grupos_sorteo = grupos_sorteo or []
        self._reglas = ap.REGLAS[juego]
        self._filas: list[ap.FilaApuestaMultiple] = []
        self._analisis: AnalisisJuego | None = None
        self._hot: set[int] = set()
        self.on_block_change: Callable[[int, int | None], None] | None = None

        self.grid_columnconfigure(0, weight=1)

        panel = MetallicPanel(
            self,
            title="Apuestas múltiples — coste y probabilidad",
            accent=accent,
        )
        panel.grid(row=0, column=0, sticky="ew")
        panel.body.grid_columnconfigure(0, weight=1)

        intro = (
            f"Apuesta simple: {ap.formatear_eur(self._reglas.precio_simple)} · "
            f"Jackpot ≈ {ap.formatear_prob(1 / self._reglas.total_combinaciones_sorteo)}"
        )
        if self._reglas.base_estrella:
            intro += (
                f" · Marca más de {self._reglas.base_principal} números y/o "
                f"más de {self._reglas.base_estrella} estrellas: el boleto genera "
                f"todas las combinaciones C(n,5)×C(e,2)."
            )
        else:
            intro += (
                f" · Con {self._reglas.base_principal - 1} números fijos se generan "
                f"apuestas reducidas; desde {self._reglas.base_principal} números, C(n,6)."
            )

        ctk.CTkLabel(
            panel.body,
            text=intro,
            font=T.FONT_SMALL,
            text_color=T.TEXT_DIM,
            wraplength=900,
            justify="left",
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

        ctrl = ctk.CTkFrame(panel.body, fg_color="transparent")
        ctrl.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        ctk.CTkLabel(ctrl, text="Números en el bloque:", font=T.FONT_BODY).pack(
            side="left", padx=(0, 8)
        )
        self._var_nums = ctk.StringVar(value=str(self._default_nums()))
        self._spin_nums = ctk.CTkOptionMenu(
            ctrl,
            variable=self._var_nums,
            values=[str(n) for n in range(self._reglas.min_marcados, self._reglas.max_marcados + 1)],
            width=70,
            fg_color=T.BG_ELEVATED,
            button_color=T.BORDER_SHINE,
            button_hover_color=self.accent,
            command=self._on_selection_change,
        )
        self._spin_nums.pack(side="left", padx=4)

        self._star_frame = ctk.CTkFrame(ctrl, fg_color="transparent")
        self._star_frame.pack(side="left", padx=(16, 0))
        self._var_stars: ctk.StringVar | None = None
        if self._reglas.base_estrella:
            ctk.CTkLabel(self._star_frame, text="Estrellas:", font=T.FONT_BODY).pack(
                side="left", padx=(0, 8)
            )
            self._var_stars = ctk.StringVar(value=str(self._reglas.base_estrella))
            ctk.CTkOptionMenu(
                self._star_frame,
                variable=self._var_stars,
                values=[
                    str(s)
                    for s in range(self._reglas.min_estrellas, self._reglas.max_estrellas + 1)
                ],
                width=70,
                fg_color=T.BG_ELEVATED,
                button_color=T.BORDER_SHINE,
                button_hover_color=T.GOLD,
                command=self._on_selection_change,
            ).pack(side="left")

        self._detail = ctk.CTkFrame(
            panel.body,
            fg_color=T.BG_PANEL_HI,
            corner_radius=8,
            border_width=1,
            border_color=self.accent,
        )
        self._detail.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        self._lbl_detail = ctk.CTkLabel(
            self._detail,
            text="",
            font=T.FONT_BODY,
            text_color=T.TEXT,
            justify="left",
            anchor="w",
        )
        self._lbl_detail.pack(fill="x", padx=12, pady=10)

        combo_box = ctk.CTkFrame(
            panel.body,
            fg_color=T.BG_ELEVATED,
            corner_radius=8,
            border_width=1,
            border_color=T.GOLD if self._reglas.base_estrella else self.accent,
        )
        combo_box.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(
            combo_box,
            text="Combinación más probable para tu bloque",
            font=T.FONT_HEAD,
            text_color=self.accent,
        ).pack(anchor="w", padx=12, pady=(10, 4))
        ctk.CTkLabel(
            combo_box,
            text=(
                "Top números por frecuencia histórica, probabilidad empírica (% de sorteos) "
                "y probabilidad teórica del bombo. Ordenados por puntuación combinada."
            ),
            font=T.FONT_SMALL,
            text_color=T.TEXT_DIM,
            wraplength=880,
            justify="left",
        ).pack(anchor="w", padx=12)
        self._combo_row = BallRow(combo_box)
        self._combo_row.pack(anchor="w", padx=12, pady=8)
        self._lbl_combo_detail = ctk.CTkLabel(
            combo_box,
            text="Carga datos históricos para ver la combinación recomendada.",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            justify="left",
            anchor="w",
            wraplength=880,
        )
        self._lbl_combo_detail.pack(fill="x", padx=12, pady=(0, 10))

        headers = self._headers()
        hdr_row = ctk.CTkFrame(panel.body, fg_color=T.BG_ELEVATED, corner_radius=6)
        hdr_row.grid(row=4, column=0, sticky="ew", pady=(0, 4))
        hdr_row.grid_columnconfigure(0, weight=1)
        for i, (text, w) in enumerate(headers):
            ctk.CTkLabel(
                hdr_row,
                text=text,
                font=T.FONT_SMALL,
                text_color=self.accent,
                width=w,
            ).grid(row=0, column=i, padx=4, pady=6, sticky="w")

        self._table_body = ctk.CTkFrame(panel.body, fg_color="transparent")
        self._table_body.grid(row=5, column=0, sticky="ew")
        self._table_body.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            panel.body,
            text=(
                "P(jackpot): probabilidad de acertar el premio máximo en un sorteo. "
                "P(≥N en bloque): al menos N bolas ganadoras entre tus números marcados "
                "(aprox. premios altos en 6/49). No incluye complementario ni reintegro."
            ),
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            wraplength=900,
            justify="left",
        ).grid(row=6, column=0, sticky="w", pady=(8, 0))

        # La tabla se rellena al cargar datos (no al crear las 3 pestañas).

    def set_analisis(
        self,
        analisis: AnalisisJuego | None,
        hot: set[int] | None = None,
        *,
        refresh_table: bool = True,
    ) -> None:
        self._analisis = analisis
        if hot is not None:
            self._hot = hot
        if refresh_table:
            self._on_selection_change()
        else:
            self._update_combo_recomendada()

    def refresh_table_deferred(self) -> None:
        """Reconstruye la tabla en el siguiente ciclo UI (tras datos ya visibles)."""
        if self.winfo_exists():
            self.after(1, self._on_selection_change)

    def _default_nums(self) -> int:
        if self.juego == "euromillones":
            return self._reglas.base_principal  # 5 = apuesta mínima
        return 7

    def _headers(self) -> list[tuple[str, int]]:
        if self._reglas.base_estrella:
            return [
                ("Núms", 48),
                ("Est.", 40),
                ("Apuestas", 72),
                ("Coste", 72),
                ("P(jackpot)", 100),
                ("× vs simple", 72),
            ]
        return [
            ("Núms", 52),
            ("Apuestas", 80),
            ("Coste", 80),
            ("P(jackpot)", 110),
            ("P≥4 bloque", 90),
            ("P≥5 bloque", 90),
            ("× vs simple", 72),
        ]

    def _estrellas(self) -> int | None:
        if not self._var_stars:
            return None
        return int(self._var_stars.get())

    def _on_selection_change(self, _value: str = "") -> None:
        if self._reglas.base_estrella and self._var_stars:
            self.refresh_table()
        else:
            self._update_detail()
            self._highlight_row()
        self._update_combo_recomendada()
        self._notify_block_change()

    def _notify_block_change(self) -> None:
        if self.on_block_change:
            self.on_block_change(int(self._var_nums.get()), self._estrellas())

    def refresh_table(self) -> None:
        est = self._estrellas() if self._reglas.base_estrella else None
        self._filas = ap.tabla_apuestas_multiples(self.juego, estrellas_marcadas=est)
        for child in self._table_body.winfo_children():
            child.destroy()

        sel_nums = int(self._var_nums.get())
        widths = [w for _, w in self._headers()]

        for idx, fila in enumerate(self._filas):
            bg = T.BG_PANEL_HI if idx % 2 == 0 else T.BG_PANEL
            row = ctk.CTkFrame(self._table_body, fg_color=bg, corner_radius=4)
            row.pack(fill="x", pady=1)
            row._fila_nums = fila.numeros_marcados  # type: ignore[attr-defined]

            cells: list[str]
            if self._reglas.base_estrella:
                est_txt = str(fila.estrellas_marcadas or self._reglas.base_estrella)
                cells = [
                    str(fila.numeros_marcados),
                    est_txt,
                    f"{fila.combinaciones:,}".replace(",", "."),
                    ap.formatear_eur(fila.coste_eur),
                    ap.formatear_prob(fila.prob_jackpot),
                    f"×{fila.mejora_vs_simple:.0f}",
                ]
            else:
                cells = [
                    str(fila.numeros_marcados),
                    f"{fila.combinaciones:,}".replace(",", "."),
                    ap.formatear_eur(fila.coste_eur),
                    ap.formatear_prob(fila.prob_jackpot),
                    ap.formatear_prob(fila.prob_en_bloque_4),
                    ap.formatear_prob(fila.prob_en_bloque_5),
                    f"×{fila.mejora_vs_simple:.0f}",
                ]

            for i, (txt, w) in enumerate(zip(cells, widths)):
                lbl = ctk.CTkLabel(
                    row,
                    text=txt,
                    font=T.FONT_SMALL,
                    text_color=T.TEXT,
                    width=w,
                    anchor="w",
                )
                lbl.grid(row=0, column=i, padx=4, pady=4, sticky="w")
                row._labels = getattr(row, "_labels", [])  # type: ignore[attr-defined]
                row._labels.append(lbl)  # type: ignore[attr-defined]

            if fila.numeros_marcados == sel_nums:
                row.configure(border_width=1, border_color=self.accent)

        self._update_detail()
        self._update_combo_recomendada()

    def _update_combo_recomendada(self) -> None:
        if not self._analisis:
            return
        n = int(self._var_nums.get())
        est = self._estrellas()
        try:
            combo = analytics.combinacion_para_apuesta_multiple(
                self._analisis,
                self.juego,
                numeros_marcados=n,
                estrellas_marcadas=est,
            )
        except Exception:
            self._lbl_combo_detail.configure(
                text="No se pudo calcular la combinación para esta selección."
            )
            return

        groups: list[tuple[list[int], str]] = []
        for tipo, kind in self._grupos_sorteo:
            vals = combo.numeros.get(tipo)
            if vals:
                groups.append((vals, kind))

        self._combo_row.set_numbers(groups, hot_sets=self._hot)

        lines: list[str] = []
        if self._reglas.base_estrella:
            lines.append(
                f"Bloque seleccionado: {n} números + {est or 2} estrellas."
            )
        else:
            lines.append(f"Bloque seleccionado: {n} números en apuesta múltiple.")

        for tipo, dets in combo.detalle.items():
            if not dets:
                continue
            partes = []
            for d in dets:
                pe = d.prob_empirica * 100
                pt = d.prob_teorica * 100
                partes.append(
                    f"{d.valor:02d} ({pe:.1f}% sorteos · teor. {pt:.1f}%)"
                    if tipo != "reintegro"
                    else f"{d.valor} ({pe:.1f}% sorteos · teor. {pt:.1f}%)"
                )
            lines.append(f"{TIPO_LABEL.get(tipo, tipo)}: " + ", ".join(partes))

        if self.juego in ("bonoloto", "primitiva") and n < self._reglas.base_principal:
            lines.append(
                f"Nota: con {n} números fijos el boleto genera apuestas reducidas "
                f"(completa con el resto del bombo)."
            )

        lines.append(
            "Basado en histórico; cada sorteo es independiente y aleatorio."
        )
        self._lbl_combo_detail.configure(text="\n".join(lines))

    def _highlight_row(self) -> None:
        sel = int(self._var_nums.get())
        for row in self._table_body.winfo_children():
            if getattr(row, "_fila_nums", None) == sel:
                row.configure(border_width=1, border_color=self.accent)
            else:
                row.configure(border_width=0)

    def _update_detail(self) -> None:
        n = int(self._var_nums.get())
        est = self._estrellas()
        fila = ap.fila_apuesta_multiple(self._reglas, n, est)
        if not fila:
            self._lbl_detail.configure(text="Selección no válida.")
            return

        if self._reglas.base_estrella:
            comb_txt = (
                f"C({n},{self._reglas.base_principal}) × "
                f"C({est or self._reglas.base_estrella},{self._reglas.base_estrella})"
            )
        elif n < self._reglas.base_principal:
            faltan = self._reglas.base_principal - n
            comb_txt = f"C({self._reglas.pool_principal - n},{faltan}) apuestas reducidas"
        else:
            comb_txt = f"C({n},{self._reglas.base_principal})"

        lines = [
            f"Con {n} números",
            f" → {fila.combinaciones:,} apuestas ({comb_txt})".replace(",", "."),
            f" → Coste por sorteo: {ap.formatear_eur(fila.coste_eur)}",
            f" → P(jackpot): {ap.formatear_prob(fila.prob_jackpot)} "
            f"(×{fila.mejora_vs_simple:.0f} frente a una simple)",
        ]
        if not self._reglas.base_estrella:
            lines.append(
                f" → P(6 en bloque): {ap.formatear_prob(fila.prob_en_bloque_6)} · "
                f"P(≥5): {ap.formatear_prob(fila.prob_en_bloque_5)} · "
                f"P(≥4): {ap.formatear_prob(fila.prob_en_bloque_4)}"
            )
        self._lbl_detail.configure(text="\n".join(lines))
