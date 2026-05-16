from __future__ import annotations

import customtkinter as ctk

from app import theme as T
from app.widgets import BallRow, MetallicPanel, NumberPickerGrid
from loteria_hist import analytics, apuestas as ap
from loteria_hist.analytics import AnalisisJuego, ComparacionApuesta

TIPO_LABEL = {
    "principal": "Principales",
    "estrella": "Estrellas",
    "complementario": "Complementario",
    "reintegro": "Reintegro",
}


class UserBetPanel(ctk.CTkFrame):
    """Elige tus números y compara probabilidades con la sugerencia heurística."""

    def __init__(
        self,
        master,
        *,
        juego: str,
        accent: str,
        grupos_sorteo: list[tuple[str, str]],
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.juego = juego
        self.accent = accent
        self._grupos = grupos_sorteo
        self._reglas = ap.REGLAS[juego]
        self._analisis: AnalisisJuego | None = None
        self._hot: set[int] = set()
        self._pickers: dict[str, NumberPickerGrid] = {}

        panel = MetallicPanel(
            self,
            title="Tu apuesta — selección y probabilidades",
            accent=accent,
        )
        panel.pack(fill="x")
        body = panel.body
        body.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            body,
            text=(
                "Elige cuántos números juegas y márcalos en la rejilla. "
                "Verás probabilidad empírica, teórica y P(jackpot) frente a la sugerencia."
            ),
            font=T.FONT_SMALL,
            text_color=T.TEXT_DIM,
            wraplength=900,
            justify="left",
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        ctrl = ctk.CTkFrame(body, fg_color="transparent")
        ctrl.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        ctk.CTkLabel(ctrl, text="Números principales:", font=T.FONT_BODY).pack(
            side="left", padx=(0, 8)
        )
        self._var_n = ctk.StringVar(value=str(self._default_n()))
        ctk.CTkOptionMenu(
            ctrl,
            variable=self._var_n,
            values=[
                str(x)
                for x in range(self._reglas.min_marcados, self._reglas.max_marcados + 1)
            ],
            width=60,
            fg_color=T.BG_ELEVATED,
            command=self._on_count_change,
        ).pack(side="left", padx=4)

        self._star_ctrl = ctk.CTkFrame(ctrl, fg_color="transparent")
        self._var_est: ctk.StringVar | None = None
        if self._reglas.base_estrella:
            self._star_ctrl.pack(side="left", padx=(16, 0))
            ctk.CTkLabel(self._star_ctrl, text="Estrellas:", font=T.FONT_BODY).pack(
                side="left", padx=(0, 8)
            )
            self._var_est = ctk.StringVar(value=str(self._reglas.base_estrella))
            ctk.CTkOptionMenu(
                self._star_ctrl,
                variable=self._var_est,
                values=[
                    str(s)
                    for s in range(
                        self._reglas.min_estrellas, self._reglas.max_estrellas + 1
                    )
                ],
                width=60,
                fg_color=T.BG_ELEVATED,
                command=self._on_count_change,
            ).pack(side="left")

        ctk.CTkButton(
            ctrl,
            text="Usar sugerencia",
            width=120,
            font=T.FONT_SMALL,
            fg_color=T.BG_ELEVATED,
            border_width=1,
            border_color=accent,
            command=self._cargar_sugerencia,
        ).pack(side="right", padx=4)

        ctk.CTkButton(
            ctrl,
            text="Limpiar",
            width=80,
            font=T.FONT_SMALL,
            fg_color=T.BG_PANEL_HI,
            command=self._limpiar,
        ).pack(side="right")

        pick_frame = ctk.CTkFrame(body, fg_color="transparent")
        pick_frame.grid(row=2, column=0, sticky="ew", pady=(0, 8))

        n_main = int(self._var_n.get())
        self._pickers["principal"] = NumberPickerGrid(
            pick_frame,
            range(1, self._reglas.pool_principal + 1),
            max_select=n_main,
            kind="main",
            accent=accent,
            columns=10,
            label=f"Marca {n_main} números del 1 al {self._reglas.pool_principal}",
            on_change=lambda _: self._actualizar(),
        )
        self._pickers["principal"].pack(anchor="w", pady=(0, 8))

        if self._reglas.base_estrella and self._var_est:
            est_n = int(self._var_est.get())
            self._pickers["estrella"] = NumberPickerGrid(
                pick_frame,
                range(1, self._reglas.pool_estrella + 1),
                max_select=est_n,
                kind="estrella",
                accent=T.GOLD_BRIGHT,
                columns=6,
                label=f"Marca {est_n} estrellas del 1 al {self._reglas.pool_estrella}",
                on_change=lambda _: self._actualizar(),
            )
            self._pickers["estrella"].pack(anchor="w", pady=(0, 8))
        else:
            comp_row = ctk.CTkFrame(pick_frame, fg_color="transparent")
            comp_row.pack(anchor="w", fill="x")
            self._pickers["complementario"] = NumberPickerGrid(
                comp_row,
                range(1, 50),
                max_select=1,
                kind="complementario",
                accent=T.ACCENT_BRIGHT,
                columns=10,
                label="Complementario (1 número)",
                on_change=lambda _: self._actualizar(),
            )
            self._pickers["complementario"].pack(side="left", padx=(0, 16))
            self._pickers["reintegro"] = NumberPickerGrid(
                comp_row,
                range(0, 10),
                max_select=1,
                kind="reintegro",
                accent=T.ROSE,
                columns=10,
                label="Reintegro (1 dígito)",
                on_change=lambda _: self._actualizar(),
            )
            self._pickers["reintegro"].pack(side="left")

        sel_box = ctk.CTkFrame(
            body,
            fg_color=T.BG_PANEL_HI,
            corner_radius=8,
            border_width=1,
            border_color=accent,
        )
        sel_box.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(
            sel_box,
            text="Tu selección",
            font=T.FONT_SMALL,
            text_color=accent,
        ).pack(anchor="w", padx=12, pady=(8, 2))
        self._user_row = BallRow(sel_box)
        self._user_row.pack(anchor="w", padx=12, pady=4)

        cmp_box = ctk.CTkFrame(body, fg_color=T.BG_ELEVATED, corner_radius=8)
        cmp_box.grid(row=4, column=0, sticky="ew")
        ctk.CTkLabel(
            cmp_box,
            text="Comparación con sugerencia heurística",
            font=T.FONT_HEAD,
            text_color=T.SILVER_BRIGHT,
        ).pack(anchor="w", padx=12, pady=(10, 4))

        self._cmp_table = ctk.CTkFrame(cmp_box, fg_color="transparent")
        self._cmp_table.pack(fill="x", padx=12, pady=(0, 8))

        self._lbl_resumen = ctk.CTkLabel(
            cmp_box,
            text="Marca tus números para ver probabilidades.",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            justify="left",
            anchor="w",
            wraplength=880,
        )
        self._lbl_resumen.pack(fill="x", padx=12, pady=(0, 10))

    def _default_n(self) -> int:
        if self.juego == "euromillones":
            return self._reglas.base_principal  # 5 números = apuesta simple (2,50 €)
        return 7

    def set_analisis(self, analisis: AnalisisJuego | None, hot: set[int] | None = None) -> None:
        self._analisis = analisis
        if hot is not None:
            self._hot = hot
        self._actualizar()

    def _seleccion_completa(self) -> dict[str, list[int]] | None:
        n_need = int(self._var_n.get())
        prin = self._pickers["principal"].get_selected()
        if len(prin) != n_need:
            return None
        out: dict[str, list[int]] = {"principal": prin}
        if self._var_est and "estrella" in self._pickers:
            est_need = int(self._var_est.get())
            est = self._pickers["estrella"].get_selected()
            if len(est) != est_need:
                return None
            out["estrella"] = est
        else:
            comp = self._pickers.get("complementario")
            reint = self._pickers.get("reintegro")
            if comp and len(comp.get_selected()) != 1:
                return None
            if reint and len(reint.get_selected()) != 1:
                return None
            if comp:
                out["complementario"] = comp.get_selected()
            if reint:
                out["reintegro"] = reint.get_selected()
        return out

    def _on_count_change(self, _v: str = "") -> None:
        n = int(self._var_n.get())
        self._pickers["principal"].set_max_select(n)
        if self._var_est and "estrella" in self._pickers:
            self._pickers["estrella"].set_max_select(int(self._var_est.get()))
        self._actualizar()

    def _limpiar(self) -> None:
        for p in self._pickers.values():
            p.clear()

    def _cargar_sugerencia(self) -> None:
        if not self._analisis:
            return
        n = int(self._var_n.get())
        est = int(self._var_est.get()) if self._var_est else None
        combo = analytics.combinacion_para_apuesta_multiple(
            self._analisis, self.juego, numeros_marcados=n, estrellas_marcadas=est
        )
        self._pickers["principal"].set_selected(combo.numeros.get("principal", []))
        if "estrella" in self._pickers:
            self._pickers["estrella"].set_selected(combo.numeros.get("estrella", []))
        if "complementario" in self._pickers:
            self._pickers["complementario"].set_selected(
                combo.numeros.get("complementario", [])
            )
        if "reintegro" in self._pickers:
            self._pickers["reintegro"].set_selected(combo.numeros.get("reintegro", []))

    def _actualizar(self) -> None:
        sel = self._seleccion_completa()
        groups: list[tuple[list[int], str]] = []
        if sel:
            for tipo, kind in self._grupos:
                vals = sel.get(tipo)
                if vals:
                    groups.append((vals, kind))
        self._user_row.set_numbers(groups, hot_sets=self._hot)

        for child in self._cmp_table.winfo_children():
            child.destroy()

        if not self._analisis or not sel:
            n = int(self._var_n.get())
            falta = n - len(self._pickers["principal"].get_selected())
            self._lbl_resumen.configure(
                text=(
                    f"Selecciona {falta} número(s) principal(es) más"
                    + (
                        f" y {int(self._var_est.get()) - len(self._pickers['estrella'].get_selected())} estrella(s)"
                        if self._var_est and "estrella" in self._pickers
                        else ""
                    )
                    + " para comparar."
                )
            )
            return

        cmp = analytics.comparar_seleccion_con_sugerencia(
            self._analisis,
            self.juego,
            sel,
            numeros_marcados=int(self._var_n.get()),
            estrellas_marcadas=int(self._var_est.get()) if self._var_est else None,
        )
        if not cmp:
            self._lbl_resumen.configure(text="No se pudo evaluar la selección.")
            return

        self._render_comparison(cmp)

    def _render_comparison(self, cmp: ComparacionApuesta) -> None:
        headers = ("Métrica", "Tu apuesta", "Sugerencia", "Δ")
        for i, h in enumerate(headers):
            ctk.CTkLabel(
                self._cmp_table,
                text=h,
                font=T.FONT_SMALL,
                text_color=self.accent,
                width=140 if i == 0 else 110,
            ).grid(row=0, column=i, padx=4, pady=4, sticky="w")

        rows: list[tuple[str, str, str, str]] = [
            (
                "P(jackpot) bloque",
                ap.formatear_prob(cmp.prob_jackpot_usuario),
                ap.formatear_prob(cmp.prob_jackpot_sugerencia),
                self._delta_pct(cmp.prob_jackpot_usuario, cmp.prob_jackpot_sugerencia),
            ),
            (
                "Apuestas / coste",
                f"{cmp.combinaciones:,} · {ap.formatear_eur(cmp.coste_eur)}".replace(
                    ",", "."
                ),
                "—",
                "—",
            ),
        ]

        for tipo in cmp.usuario:
            u, s = cmp.usuario[tipo], cmp.sugerencia.get(tipo)
            if not s:
                continue
            label = TIPO_LABEL.get(tipo, tipo)
            rows.append(
                (
                    f"Score medio ({label})",
                    f"{u.score_medio:.3f}",
                    f"{s.score_medio:.3f}",
                    self._delta_num(u.score_medio, s.score_medio),
                )
            )
            rows.append(
                (
                    f"% empírico medio ({label})",
                    f"{u.prob_empirica_media * 100:.2f} %",
                    f"{s.prob_empirica_media * 100:.2f} %",
                    self._delta_num(u.prob_empirica_media, s.prob_empirica_media, pct=True),
                )
            )

        for ri, row in enumerate(rows, start=1):
            for ci, txt in enumerate(row):
                ctk.CTkLabel(
                    self._cmp_table,
                    text=txt,
                    font=T.FONT_SMALL,
                    text_color=T.TEXT if ci > 0 else T.TEXT_DIM,
                    width=140 if ci == 0 else 110,
                    anchor="w",
                ).grid(row=ri, column=ci, padx=4, pady=2, sticky="w")

        det_lines = ["Detalle por número (empírico = % de sorteos en el histórico):"]
        for tipo, ev in cmp.usuario.items():
            partes = []
            for d in ev.detalles:
                vtxt = f"{d.valor:02d}" if tipo != "reintegro" else str(d.valor)
                partes.append(f"{vtxt} {d.prob_empirica * 100:.1f}%")
            det_lines.append(f"  {TIPO_LABEL.get(tipo, tipo)}: " + ", ".join(partes))

        su = cmp.sugerencia.get("principal")
        if su:
            det_lines.append(
                f"Sugerencia principal (score {su.score_medio:.3f}): "
                + ", ".join(f"{n:02d}" for n in su.numeros)
            )

        mejor = "por encima" if cmp.prob_jackpot_usuario >= cmp.prob_jackpot_sugerencia else "por debajo"
        det_lines.append(
            f"\nTu bloque queda {mejor} de la sugerencia en P(jackpot) "
            f"(misma cantidad de números). Esto no garantiza mejor resultado en el próximo sorteo."
        )
        self._lbl_resumen.configure(text="\n".join(det_lines))

    @staticmethod
    def _delta_num(a: float, b: float, pct: bool = False) -> str:
        d = a - b
        if pct:
            d *= 100
            return f"{d:+.2f} p.p."
        return f"{d:+.3f}"

    @staticmethod
    def _delta_pct(a: float, b: float) -> str:
        if a <= 0 and b <= 0:
            return "—"
        if b <= 0:
            return "↑"
        ratio = (a - b) / b * 100
        return f"{ratio:+.1f} % rel."
