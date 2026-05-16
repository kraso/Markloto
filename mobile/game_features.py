"""Análisis avanzado y apuesta manual (paridad con escritorio)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import flet as ft

from loteria_hist import analytics, apuestas as ap
from loteria_hist.analytics import AnalisisJuego, ComparacionApuesta

from mobile.config import TIPO_LABEL
from mobile.widgets import balls_row, card, section_title


@dataclass
class PickerState:
    n_principal: int
    n_estrellas: int | None
    selected: dict[str, set[int]] = field(default_factory=dict)


def default_picker_state(juego: str) -> PickerState:
    reglas = ap.REGLAS[juego]
    n = reglas.base_principal if juego == "euromillones" else 7
    est = reglas.base_estrella if reglas.base_estrella else None
    selected: dict[str, set[int]] = {"principal": set()}
    if reglas.base_estrella:
        selected["estrella"] = set()
    else:
        selected["complementario"] = set()
        selected["reintegro"] = set()
    return PickerState(n_principal=n, n_estrellas=est, selected=selected)


def _groups_from_nums(
    numeros: dict[str, list[int]],
    grupos_sorteo: list[tuple[str, str]],
) -> list[tuple[list[int], str]]:
    out: list[tuple[list[int], str]] = []
    for tipo, kind in grupos_sorteo:
        vals = numeros.get(tipo, [])
        if vals:
            out.append((vals, kind))
    return out


def _fmt_detalle(tipo: str, dets: list) -> str:
    partes: list[str] = []
    for d in dets:
        pe = d.prob_empirica * 100
        pt = d.prob_teorica * 100
        if tipo == "reintegro":
            partes.append(f"{d.valor} ({pe:.1f}% · teor. {pt:.1f}%)")
        else:
            partes.append(f"{d.valor:02d} ({pe:.1f}% · teor. {pt:.1f}%)")
    return ", ".join(partes)


def improved_suggestion_card(
    *,
    juego: str,
    analisis: AnalisisJuego,
    state: PickerState,
    grupos: list[tuple[str, str]],
    accent: str,
    hot: set[int],
) -> ft.Control:
    est = state.n_estrellas if juego == "euromillones" else None
    combo = analytics.combinacion_para_apuesta_multiple(
        analisis,
        juego,
        numeros_marcados=state.n_principal,
        estrellas_marcadas=est,
    )
    lines = [
        "Top por frecuencia histórica, probabilidad empírica y teórica del bombo.",
        f"Bloque: {state.n_principal} principales"
        + (f" + {est} estrellas" if est else "")
        + ".",
    ]
    for tipo, dets in combo.detalle.items():
        if dets:
            lines.append(f"{TIPO_LABEL.get(tipo, tipo)}: {_fmt_detalle(tipo, dets)}")

    return card(
        ft.Column(
            [
                section_title("Combinación por frecuencias (score)", accent),
                ft.Text("\n".join(lines), size=12, color="#8d9aad"),
                balls_row(
                    _groups_from_nums(combo.numeros, grupos),
                    hot=hot,
                    accent=accent,
                ),
            ],
            spacing=8,
        ),
        accent=accent,
    )


def random_suggestion_card(
    *,
    sugerencia: dict[str, list[int]],
    grupos: list[tuple[str, str]],
    accent: str,
    hot: set[int],
    on_refresh: Callable[[], None],
) -> ft.Control:
    sug = sugerencia
    return card(
        ft.Column(
            [
                ft.Row(
                    [
                        section_title("Variación aleatoria", accent),
                        ft.TextButton(
                            content="Otra",
                            on_click=lambda _e: on_refresh(),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Text(
                    "Mezcla ponderada al azar entre números frecuentes.",
                    size=12,
                    color="#8d9aad",
                ),
                balls_row(_groups_from_nums(sug, grupos), hot=hot, accent=accent),
            ],
            spacing=8,
        ),
        accent=accent,
    )


def _fmt_entero(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _tabla_celda(texto: str, ancho: float, *, resaltar: bool = False) -> ft.Container:
    return ft.Container(
        content=ft.Text(
            texto,
            size=11,
            weight=ft.FontWeight.W_600 if resaltar else None,
            color="#0c1018" if resaltar else "#eef2f7",
            no_wrap=True,
        ),
        width=ancho,
    )


def _fila_tabla(
    textos: list[str],
    anchos: list[float],
    *,
    resaltada: bool = False,
    accent: str = "#4a5f7a",
) -> ft.Container:
    celdas = [
        _tabla_celda(t, w, resaltar=resaltada) for t, w in zip(textos, anchos, strict=True)
    ]
    return ft.Container(
        content=ft.Row(celdas, spacing=4),
        bgcolor=accent if resaltada else "#141a24",
        border=ft.Border.all(1, accent) if resaltada else None,
        border_radius=6,
        padding=ft.Padding.symmetric(horizontal=6, vertical=5),
    )


def _detalle_fila_seleccionada(
    reglas: ap.ReglasJuego,
    state: PickerState,
) -> str:
    est = state.n_estrellas if reglas.base_estrella else None
    fila = ap.fila_apuesta_multiple(reglas, state.n_principal, est)
    if not fila:
        return "Selección no válida para la tabla."

    n = state.n_principal
    if reglas.base_estrella:
        comb_txt = (
            f"C({n},{reglas.base_principal}) × "
            f"C({est or reglas.base_estrella},{reglas.base_estrella})"
        )
    elif n < reglas.base_principal:
        faltan = reglas.base_principal - n
        comb_txt = f"C({reglas.pool_principal - n},{faltan}) apuestas reducidas"
    else:
        comb_txt = f"C({n},{reglas.base_principal})"

    lineas = [
        f"Bloque activo: {n} números"
        + (f" + {est} estrellas" if reglas.base_estrella and est else ""),
        f"{_fmt_entero(fila.combinaciones)} apuestas ({comb_txt})",
        f"Coste por sorteo: {ap.formatear_eur(fila.coste_eur)}",
        f"P(jackpot): {ap.formatear_prob(fila.prob_jackpot)} "
        f"(×{fila.mejora_vs_simple:.0f} frente a una simple)",
    ]
    if not reglas.base_estrella:
        lineas.append(
            f"P(6 en bloque): {ap.formatear_prob(fila.prob_en_bloque_6)} · "
            f"P(≥5): {ap.formatear_prob(fila.prob_en_bloque_5)} · "
            f"P(≥4): {ap.formatear_prob(fila.prob_en_bloque_4)}"
        )
    return "\n".join(lineas)


def multiple_bets_card(
    *,
    juego: str,
    accent: str,
    state: PickerState,
) -> ft.Control:
    """Tabla de apuestas múltiples (combinaciones, coste, probabilidades)."""
    reglas = ap.REGLAS[juego]
    est = state.n_estrellas if reglas.base_estrella else None
    filas = ap.tabla_apuestas_multiples(juego, estrellas_marcadas=est)

    intro = (
        f"Apuesta simple: {ap.formatear_eur(reglas.precio_simple)} · "
        f"Jackpot ≈ {ap.formatear_prob(1 / reglas.total_combinaciones_sorteo)}"
    )
    if reglas.base_estrella:
        intro += (
            f". Marca más de {reglas.base_principal} números y/o "
            f"más de {reglas.base_estrella} estrellas: C(n,5)×C(e,2)."
        )
    else:
        intro += (
            f". Con {reglas.base_principal - 1} números fijos, apuestas reducidas; "
            f"desde {reglas.base_principal}, C(n,6)."
        )

    if reglas.base_estrella:
        cabeceras = ("Núm", "Est", "Apuestas", "Coste", "P(jackpot)", "×")
        anchos = (40.0, 36.0, 64.0, 56.0, 92.0, 44.0)
    else:
        cabeceras = ("Núm", "Apuestas", "Coste", "P(jackpot)", "P≥4", "P≥5", "×")
        anchos = (40.0, 64.0, 56.0, 88.0, 72.0, 72.0, 44.0)

    tabla_filas: list[ft.Control] = [
        _fila_tabla(
            list(cabeceras),
            list(anchos),
            resaltada=False,
            accent=accent,
        ),
    ]

    for fila in filas:
        resaltada = fila.numeros_marcados == state.n_principal
        if reglas.base_estrella:
            celdas = [
                str(fila.numeros_marcados),
                str(fila.estrellas_marcadas or reglas.base_estrella),
                _fmt_entero(fila.combinaciones),
                ap.formatear_eur(fila.coste_eur),
                ap.formatear_prob(fila.prob_jackpot),
                f"×{fila.mejora_vs_simple:.0f}",
            ]
        else:
            celdas = [
                str(fila.numeros_marcados),
                _fmt_entero(fila.combinaciones),
                ap.formatear_eur(fila.coste_eur),
                ap.formatear_prob(fila.prob_jackpot),
                ap.formatear_prob(fila.prob_en_bloque_4),
                ap.formatear_prob(fila.prob_en_bloque_5),
                f"×{fila.mejora_vs_simple:.0f}",
            ]
        tabla_filas.append(
            _fila_tabla(celdas, list(anchos), resaltada=resaltada, accent=accent)
        )

    tabla = ft.Column(tabla_filas, spacing=3, scroll=ft.ScrollMode.AUTO, height=220)
    tabla_h = ft.Row([tabla], scroll=ft.ScrollMode.AUTO)

    nota = (
        "P(jackpot): probabilidad del premio máximo en un sorteo. "
        "P(≥N en bloque): al menos N bolas ganadoras entre tus números "
        "(Bonoloto/Primitiva; sin complementario ni reintegro). "
        "La fila resaltada coincide con «Principales» en tu apuesta."
    )

    return card(
        ft.Column(
            [
                section_title("Apuestas múltiples — coste y probabilidad", accent),
                ft.Text(intro, size=12, color="#8d9aad"),
                tabla_h,
                ft.Text(
                    _detalle_fila_seleccionada(reglas, state),
                    size=12,
                    color="#eef2f7",
                ),
                ft.Text(nota, size=11, color="#5c6b7f"),
            ],
            spacing=8,
        ),
        accent=accent,
    )


def _number_chip(
    n: int,
    *,
    selected: bool,
    accent: str,
    on_click: Callable[[], None],
) -> ft.Container:
    return ft.Container(
        content=ft.Text(
            str(n),
            size=13,
            weight=ft.FontWeight.BOLD if selected else None,
            color="#0c1018" if selected else "#eef2f7",
        ),
        bgcolor=accent if selected else "#1e2836",
        border_radius=18,
        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
        on_click=lambda _e: on_click(),
    )


def _number_grid(
    pool: range,
    selected: set[int],
    max_select: int,
    accent: str,
    on_toggle: Callable[[int], None],
    *,
    columns: int = 10,
) -> ft.Column:
    row: list[ft.Control] = []
    rows: list[ft.Row] = []
    for n in pool:
        row.append(
            _number_chip(
                n,
                selected=n in selected,
                accent=accent,
                on_click=lambda num=n: on_toggle(num),
            )
        )
        if len(row) >= columns:
            rows.append(ft.Row(row, wrap=True, spacing=4, run_spacing=4))
            row = []
    if row:
        rows.append(ft.Row(row, wrap=True, spacing=4, run_spacing=4))
    return ft.Column(rows, spacing=4)


def _comparison_text(cmp: ComparacionApuesta) -> ft.Column:
    """Tabla compacta si DataTable falla en algún dispositivo."""
    lines = [
        f"P(jackpot): tú {ap.formatear_prob(cmp.prob_jackpot_usuario)} · "
        f"sugerencia {ap.formatear_prob(cmp.prob_jackpot_sugerencia)}",
        f"Apuestas: {cmp.combinaciones} · {ap.formatear_eur(cmp.coste_eur)}",
    ]
    for tipo, u in cmp.usuario.items():
        s = cmp.sugerencia.get(tipo)
        if s:
            lines.append(
                f"{TIPO_LABEL.get(tipo, tipo)}: score {u.score_medio:.3f} / {s.score_medio:.3f}"
            )
    mejor = (
        "por encima"
        if cmp.prob_jackpot_usuario >= cmp.prob_jackpot_sugerencia
        else "por debajo"
    )
    lines.append(
        f"Tu bloque queda {mejor} en P(jackpot). No garantiza mejor resultado futuro."
    )
    return ft.Column(
        [
            ft.Text(
                "Comparación con la sugerencia (mismo tamaño)",
                weight=ft.FontWeight.W_600,
            ),
            *[ft.Text(t, size=12, color="#8d9aad") for t in lines],
        ],
        spacing=4,
    )


def user_bet_card(
    *,
    juego: str,
    analisis: AnalisisJuego,
    state: PickerState,
    grupos: list[tuple[str, str]],
    accent: str,
    hot: set[int],
    on_change: Callable[[], None],
    show_snack: Callable[[str], None],
) -> ft.Control:
    reglas = ap.REGLAS[juego]

    def seleccion() -> dict[str, list[int]]:
        return {k: sorted(v) for k, v in state.selected.items() if v}

    def toggle(tipo: str, n: int, max_sel: int) -> None:
        sel = state.selected.setdefault(tipo, set())
        if n in sel:
            sel.remove(n)
        elif len(sel) >= max_sel:
            show_snack(f"Máximo {max_sel} en {TIPO_LABEL.get(tipo, tipo)}")
            return
        else:
            sel.add(n)
        on_change()

    def set_n_principal(val: str) -> None:
        state.n_principal = int(val)
        state.selected["principal"] = set()
        on_change()

    def set_n_estrellas(val: str) -> None:
        if state.n_estrellas is not None:
            state.n_estrellas = int(val)
            state.selected["estrella"] = set()
            on_change()

    def usar_sugerencia(_e) -> None:
        est = state.n_estrellas if juego == "euromillones" else None
        combo = analytics.combinacion_para_apuesta_multiple(
            analisis,
            juego,
            numeros_marcados=state.n_principal,
            estrellas_marcadas=est,
        )
        for tipo, nums in combo.numeros.items():
            state.selected[tipo] = set(nums)
        on_change()

    def limpiar(_e) -> None:
        for s in state.selected.values():
            s.clear()
        on_change()

    n_opts = [
        ft.DropdownOption(key=str(x), text=str(x))
        for x in range(reglas.min_marcados, reglas.max_marcados + 1)
    ]
    controls_row: list[ft.Control] = [
        ft.Dropdown(
            label="Principales",
            width=110,
            value=str(state.n_principal),
            options=n_opts,
            on_select=lambda e: set_n_principal(e.control.value),
        ),
    ]
    if state.n_estrellas is not None and reglas.base_estrella:
        est_opts = [
            ft.DropdownOption(key=str(s), text=str(s))
            for s in range(reglas.min_estrellas, reglas.max_estrellas + 1)
        ]
        controls_row.append(
            ft.Dropdown(
                label="Estrellas",
                width=110,
                value=str(state.n_estrellas),
                options=est_opts,
                on_select=lambda e: set_n_estrellas(e.control.value),
            )
        )

    pickers: list[ft.Control] = [
        ft.Text(
            "Marca tus números en la rejilla y compáralos con la sugerencia por score.",
            size=12,
            color="#8d9aad",
        ),
        ft.Row(
            [
                *controls_row,
                ft.TextButton(content="Usar sugerencia", on_click=usar_sugerencia),
                ft.TextButton(content="Limpiar", on_click=limpiar),
            ],
            wrap=True,
            spacing=8,
        ),
    ]

    pickers.append(
        ft.Text(
            f"Principales ({len(state.selected.get('principal', set()))}/{state.n_principal})",
            size=13,
            color=accent,
        )
    )
    pickers.append(
        _number_grid(
            range(1, reglas.pool_principal + 1),
            state.selected.get("principal", set()),
            state.n_principal,
            accent,
            lambda n: toggle("principal", n, state.n_principal),
        )
    )

    if state.n_estrellas is not None and reglas.base_estrella:
        pickers.append(
            ft.Text(
                f"Estrellas ({len(state.selected.get('estrella', set()))}/{state.n_estrellas})",
                size=13,
                color=accent,
            )
        )
        pickers.append(
            _number_grid(
                range(1, reglas.pool_estrella + 1),
                state.selected.get("estrella", set()),
                state.n_estrellas or 2,
                accent,
                lambda n: toggle("estrella", n, state.n_estrellas or 2),
                columns=6,
            )
        )
    else:
        pickers.append(ft.Text("Complementario (1)", size=13, color=accent))
        pickers.append(
            _number_grid(
                range(1, 50),
                state.selected.get("complementario", set()),
                1,
                accent,
                lambda n: toggle("complementario", n, 1),
            )
        )
        pickers.append(ft.Text("Reintegro (1)", size=13, color=accent))
        pickers.append(
            _number_grid(
                range(0, 10),
                state.selected.get("reintegro", set()),
                1,
                accent,
                lambda n: toggle("reintegro", n, 1),
                columns=10,
            )
        )

    sel = seleccion()
    if sel:
        pickers.append(
            ft.Text("Tu selección", size=14, weight=ft.FontWeight.W_600, color=accent)
        )
        pickers.append(
            balls_row(_groups_from_nums(sel, grupos), hot=hot, accent=accent)
        )

    cmp_block: ft.Control | None = None
    if sel:
        cmp = analytics.comparar_seleccion_con_sugerencia(
            analisis,
            juego,
            sel,
            numeros_marcados=state.n_principal,
            estrellas_marcadas=state.n_estrellas,
        )
        if cmp:
            cmp_block = _comparison_text(cmp)
        else:
            falta_p = state.n_principal - len(state.selected.get("principal", set()))
            extra = ""
            if state.n_estrellas is not None:
                falta_e = (state.n_estrellas or 0) - len(
                    state.selected.get("estrella", set())
                )
                if falta_e > 0:
                    extra = f" y {falta_e} estrella(s)"
            cmp_block = ft.Text(
                f"Selecciona {falta_p} principal(es) más{extra} para comparar.",
                color="#8d9aad",
            )

    body_controls = pickers + ([cmp_block] if cmp_block else [])
    return card(
        ft.Column(body_controls, spacing=10),
        accent=accent,
    )
