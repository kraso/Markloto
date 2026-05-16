"""Aplicación Flet (Android / escritorio ligero)."""

from __future__ import annotations

import sqlite3
import threading

import flet as ft

from loteria_hist import metadata as meta
from loteria_hist import repository
from loteria_hist.bootstrap_db import ensure_user_database, read_seed_info, texto_bd_local
from loteria_hist.paths import configure_mobile_storage, default_db_path
from loteria_hist.periodos import ETIQUETAS_PERIODO_UI
from loteria_hist.sync_coordinator import SyncCoordinator, SyncMode
from loteria_hist.ultimos_data import cargar_datos

from loteria_hist import analytics

from mobile.config import GAME_CONFIG, TIPO_LABEL
from mobile.game_features import (
    default_picker_state,
    improved_suggestion_card,
    multiple_bets_card,
    random_suggestion_card,
    user_bet_card,
)
from mobile.widgets import balls_row, card, section_title

_TAB_LABELS = [g.title for g in GAME_CONFIG] + ["Últimos", "Acerca de"]


def _snack(message: str) -> ft.SnackBar:
    return ft.SnackBar(content=ft.Text(message), open=True)


def _material_icon(name: str, *, fallback: str = "casino") -> str:
    icons = getattr(ft, "Icons", None) or getattr(ft, "icons", None)
    if icons is not None:
        return getattr(icons, name, None) or fallback
    return fallback


class MarklotoMobile:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        configure_mobile_storage(page)
        self.db_path = default_db_path()
        self._sync = SyncCoordinator(self.db_path)
        self._periodo_labels = dict(ETIQUETAS_PERIODO_UI)
        self._periodo = "trimestre"
        self._juego_ultimos = GAME_CONFIG[0].key
        self._analisis_cache: dict = {}
        self._ultimo_cache: dict = {}
        self._resumen_cache: dict = {}
        self._picker_states: dict = {}
        self._random_sug: dict = {}

        page.title = "Markloto"
        page.theme_mode = ft.ThemeMode.DARK
        page.bgcolor = "#07090d"
        page.padding = 12
        page.scroll = None  # evita pantalla negra con layout en Android (Flet #4908)

        self._tab_index = 0
        self._ready = False
        self.status = ft.Text("Preparando base de datos…", size=12, color="#8d9aad")
        self.body = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.ProgressRing(),
                ft.Text("Cargando histórico…", color="#8d9aad"),
            ],
        )
        self._tab_buttons: list[ft.TextButton] = []
        tab_row = ft.Row(scroll=ft.ScrollMode.AUTO, spacing=4)
        for i, label in enumerate(_TAB_LABELS):
            btn = ft.TextButton(
                content=label,
                on_click=lambda e, idx=i: self._select_tab(idx),
            )
            self._tab_buttons.append(btn)
            tab_row.controls.append(btn)

        page.appbar = ft.AppBar(
            title=ft.Text("Markloto", color="#f5e6a8"),
            bgcolor="#0c1018",
            actions=[
                ft.IconButton(
                    icon=_material_icon("SYNC", fallback="sync"),
                    tooltip="Sincronizar SELAE",
                    on_click=self._on_sync_click,
                ),
            ],
        )
        page.add(
            ft.Column(
                [
                    tab_row,
                    ft.Divider(height=1, color="#2e3a4d"),
                    self.body,
                    ft.Container(
                        content=self.status,
                        padding=ft.Padding.symmetric(horizontal=12, vertical=6),
                        bgcolor="#141a24",
                    ),
                ],
                expand=True,
            )
        )
        self._update_tab_bar()
        page.update()
        threading.Thread(target=self._bootstrap_database, daemon=True).start()

    def _ui(self, fn) -> None:
        """Ejecuta actualización de UI en el hilo principal (Android)."""
        run = getattr(self.page, "run_thread", None)
        if callable(run):
            run(fn)
        else:
            fn()

    def _bootstrap_database(self) -> None:
        try:
            _applied, msg = ensure_user_database(self.db_path)

            def finish() -> None:
                self._ready = True
                if msg:
                    self.page.snack_bar = _snack(msg)
                self._set_status("Listo")
                self._render_current_tab()

            self._ui(finish)
        except Exception as exc:
            self._ui(lambda: self._show_fatal_error(str(exc)))

    def _show_fatal_error(self, message: str) -> None:
        self.body.controls.clear()
        self.body.controls.append(
            ft.Text(f"No se pudo iniciar la app:\n{message}", color="#f0a8c0")
        )
        self._set_status("Error al iniciar")
        self.body.update()

    def _select_tab(self, index: int) -> None:
        self._tab_index = index
        self._update_tab_bar()
        self._render_current_tab()

    def _update_tab_bar(self) -> None:
        for i, btn in enumerate(self._tab_buttons):
            selected = i == self._tab_index
            btn.style = ft.ButtonStyle(
                color="#f5e6a8" if selected else "#8d9aad",
            )
        self.page.update()

    def _set_status(self, msg: str) -> None:
        self.status.value = msg
        self.status.update()

    def _show_snack(self, message: str) -> None:
        self.page.snack_bar = _snack(message)
        self.page.update()

    def _picker_state(self, juego: str):
        if juego not in self._picker_states:
            self._picker_states[juego] = default_picker_state(juego)
        return self._picker_states[juego]

    def _refresh_game_ui(self, cfg) -> None:
        analisis = self._analisis_cache.get(cfg.key)
        if analisis is None:
            self._render_game(cfg)
            return
        self._paint_game(
            cfg,
            analisis,
            self._ultimo_cache.get(cfg.key),
            self._resumen_cache.get(cfg.key),
        )

    def _new_random_suggestion(self, cfg, analisis) -> None:
        import random

        semilla = random.randint(0, 2**31 - 1)
        self._random_sug[cfg.key] = analytics.nueva_sugerencia(
            analisis, cfg.key, semilla=semilla
        )
        self._refresh_game_ui(cfg)

    def _paint_game(self, cfg, analisis, ultimo, resumen) -> None:
        self.body.controls.clear()
        state = self._picker_state(cfg.key)
        hot: set[int] = set()
        if ultimo:
            for tipo, _ in cfg.grupos:
                hot.update(ultimo.numeros.get(tipo, []))
        if not hot and analisis.frecuencias.get("principal"):
            hot = {n for n, _ in analisis.frecuencias["principal"][:8]}

        blocks: list[ft.Control] = [
            card(
                ft.Column(
                    [
                        section_title(cfg.title, cfg.accent),
                        ft.Text(
                            f"{resumen.total} sorteos · "
                            f"{resumen.fecha_min or '—'} → {resumen.fecha_max or '—'}",
                            color="#8d9aad",
                        ),
                    ]
                ),
                accent=cfg.accent,
            ),
        ]

        if ultimo:
            groups = [
                (ultimo.numeros.get(t, []), k)
                for t, k in cfg.grupos
                if ultimo.numeros.get(t)
            ]
            blocks.append(
                card(
                    ft.Column(
                        [
                            section_title("Último sorteo", cfg.accent),
                            ft.Text(ultimo.fecha, size=16, weight=ft.FontWeight.W_600),
                            ft.Text(ultimo.premio_bote or "", color="#8d9aad"),
                            balls_row(groups, hot=hot, accent=cfg.accent),
                        ],
                        spacing=8,
                    ),
                    accent=cfg.accent,
                )
            )

        blocks.append(
            improved_suggestion_card(
                juego=cfg.key,
                analisis=analisis,
                state=state,
                grupos=cfg.grupos,
                accent=cfg.accent,
                hot=hot,
            )
        )
        sug_alea = self._random_sug.get(cfg.key) or analisis.sugerencia
        blocks.append(
            random_suggestion_card(
                sugerencia=sug_alea,
                grupos=cfg.grupos,
                accent=cfg.accent,
                hot=hot,
                on_refresh=lambda: self._new_random_suggestion(cfg, analisis),
            )
        )
        blocks.append(
            multiple_bets_card(
                juego=cfg.key,
                accent=cfg.accent,
                state=state,
            )
        )
        blocks.append(
            user_bet_card(
                juego=cfg.key,
                analisis=analisis,
                state=state,
                grupos=cfg.grupos,
                accent=cfg.accent,
                hot=hot,
                on_change=lambda: self._refresh_game_ui(cfg),
                show_snack=self._show_snack,
            )
        )

        for tipo, _kind in cfg.grupos:
            freq = analisis.frecuencias.get(tipo, [])[:12]
            if not freq:
                continue
            lines = [
                ft.Text(f"{n:2d}  →  {c} veces", font_family="monospace")
                for n, c in freq
            ]
            blocks.append(
                card(
                    ft.Column(
                        [
                            section_title(TIPO_LABEL.get(tipo, tipo), cfg.accent),
                            *lines,
                        ],
                        spacing=4,
                    ),
                    accent=cfg.accent,
                )
            )

        self.body.controls.extend(blocks)
        self.body.update()
        self._set_status(f"{cfg.title}: listo")

    def _on_sync_click(self, _e: ft.ControlEvent) -> None:
        self._run_sync(SyncMode.INCREMENTAL)

    def _run_sync(self, mode: SyncMode) -> None:
        if self._sync.is_running:
            self._set_status("Sincronización en curso…")
            return
        self.page.snack_bar = _snack("Descargando novedades SELAE…")
        juegos = [g.key for g in GAME_CONFIG]

        def on_progress(msg: str) -> None:
            self.status.value = msg[:100]
            self.status.update()

        def on_done(result) -> None:
            if isinstance(result, Exception):
                err = str(result)
                if "curl_cffi" in err.lower() or "ImportError" in err:
                    err = (
                        "Sync SELAE no disponible en este APK. "
                        "Usa la versión de escritorio o actualiza cuando haya soporte móvil."
                    )
                self._set_status(f"Error: {err}")
                self.page.snack_bar = _snack(err)
                return
            parts = [f"{k}: +{v}" for k, v in result.totals.items()]
            self._set_status("SELAE OK · " + " · ".join(parts))
            self.page.snack_bar = _snack("Sincronización completada")
            self._render_current_tab()

        started = self._sync.request(
            juegos,
            mode=mode,
            on_progress=on_progress,
            on_done=lambda r: self._ui(lambda: on_done(r)),
            schedule=self._ui,
        )
        if not started:
            self._set_status("En cola tras la sincronización actual…")

    def _render_current_tab(self) -> None:
        if not self._ready:
            return
        idx = self._tab_index
        n_games = len(GAME_CONFIG)
        if idx < n_games:
            self._render_game(GAME_CONFIG[idx])
        elif idx == n_games:
            self._render_ultimos()
        else:
            self._render_about()

    def _render_game(self, cfg) -> None:
        self.body.controls.clear()
        self.body.controls.append(ft.ProgressRing())
        self.body.update()

        def work():
            conn = sqlite3.connect(self.db_path, timeout=30)
            try:
                analisis = cfg.analizar(conn)
                ultimo = repository.ultimo_sorteo(conn, cfg.key)
                return analisis, ultimo
            finally:
                conn.close()

        def done(result):
            if isinstance(result, Exception):
                self.body.controls.clear()
                self.body.controls.append(ft.Text(f"Error: {result}", color="#f0a8c0"))
                self.body.update()
                return
            analisis, ultimo = result
            conn = sqlite3.connect(self.db_path, timeout=30)
            try:
                resumen = repository.resumen_juego(conn, cfg.key)
            finally:
                conn.close()
            self._analisis_cache[cfg.key] = analisis
            self._ultimo_cache[cfg.key] = ultimo
            self._resumen_cache[cfg.key] = resumen
            self._paint_game(cfg, analisis, ultimo, resumen)

        def thread_main():
            try:
                out = work()
                self._ui(lambda: done(out))
            except Exception as exc:
                self._ui(lambda: done(exc))

        threading.Thread(target=thread_main, daemon=True).start()

    def _render_ultimos(self) -> None:
        self.body.controls.clear()
        self.body.controls.append(
            ft.Row(
                [
                    ft.Dropdown(
                        label="Juego",
                        width=160,
                        value=self._juego_ultimos,
                        options=[
                            ft.DropdownOption(key=g.key, text=g.title)
                            for g in GAME_CONFIG
                        ],
                        on_select=self._on_ultimos_juego,
                    ),
                    ft.Dropdown(
                        label="Periodo",
                        width=180,
                        value=next(
                            k
                            for k, v in self._periodo_labels.items()
                            if v == self._periodo
                        ),
                        options=[
                            ft.DropdownOption(
                                key=k, text=self._periodo_labels[k]
                            )
                            for k in self._periodo_labels
                        ],
                        on_select=self._on_ultimos_periodo,
                    ),
                    ft.ElevatedButton(
                        content="Actualizar",
                        on_click=self._reload_ultimos,
                    ),
                ],
                wrap=True,
            )
        )
        self._ultimos_list = ft.Column(spacing=8)
        self.body.controls.append(self._ultimos_list)
        self.body.update()
        self._reload_ultimos(None)

    def _on_ultimos_juego(self, e: ft.ControlEvent) -> None:
        self._juego_ultimos = e.control.value
        self._reload_ultimos(None)

    def _on_ultimos_periodo(self, e: ft.ControlEvent) -> None:
        self._periodo = self._periodo_labels.get(e.control.value, "trimestre")
        self._reload_ultimos(None)

    def _reload_ultimos(self, _e) -> None:
        cfg = next(g for g in GAME_CONFIG if g.key == self._juego_ultimos)
        self._ultimos_list.controls.clear()
        self._ultimos_list.controls.append(ft.ProgressRing())
        self._ultimos_list.update()

        def work():
            conn = sqlite3.connect(self.db_path, timeout=30)
            try:
                return cargar_datos(conn, cfg.key, cfg.grupos, self._periodo)
            finally:
                conn.close()

        def done(result):
            self._ultimos_list.controls.clear()
            if isinstance(result, Exception):
                self._ultimos_list.controls.append(ft.Text(f"Error: {result}"))
                self._ultimos_list.update()
                return
            self._ultimos_list.controls.append(
                ft.Text(
                    f"{result.periodo.etiqueta} · {len(result.sorteos_periodo)} sorteos",
                    color="#8d9aad",
                )
            )
            hot: set[int] = set()
            for tipo, _ in cfg.grupos:
                for n, _ in result.frecuencias.get(tipo, [])[:5]:
                    hot.add(n)
            for s in result.sorteos_periodo[:25]:
                groups = [
                    (s.numeros.get(t, []), k)
                    for t, k in cfg.grupos
                    if s.numeros.get(t)
                ]
                self._ultimos_list.controls.append(
                    card(
                        ft.Column(
                            [
                                ft.Text(s.fecha, weight=ft.FontWeight.W_600),
                                balls_row(groups, hot=hot, accent=cfg.accent),
                            ],
                            spacing=6,
                        ),
                        accent=cfg.accent,
                    )
                )
            if len(result.sorteos_periodo) > 25:
                self._ultimos_list.controls.append(
                    ft.Text(
                        f"… y {len(result.sorteos_periodo) - 25} más",
                        color="#5c6b7f",
                    )
                )
            self._ultimos_list.update()

        def thread_main():
            try:
                out = work()
                self._ui(lambda: done(out))
            except Exception as exc:
                self._ui(lambda: done(exc))

        threading.Thread(target=thread_main, daemon=True).start()

    def _render_about(self) -> None:
        self.body.controls.clear()
        version = meta.app_version()
        embebido = read_seed_info()
        local = texto_bd_local(self.db_path)
        rows = [
            ("App", meta.APP_NAME),
            ("Versión", version),
            ("Autor", meta.AUTHOR),
            ("Email", meta.EMAIL),
            ("Base local", local or "—"),
        ]
        if embebido and embebido.get("fecha_max"):
            rows.append(
                (
                    "Semilla embebida",
                    f"hasta {embebido['fecha_max']}",
                )
            )
        content = ft.Column(
            [
                card(
                    ft.Column(
                        [ft.Text(f"{k}: {v}", size=14) for k, v in rows],
                        spacing=6,
                    )
                ),
                card(
                    ft.Text(meta.ABOUT_TEXT, color="#eef2f7"),
                ),
                ft.Text(
                    "Los sorteos son aleatorios. Markloto no garantiza premios.",
                    size=12,
                    color="#5c6b7f",
                ),
            ],
            spacing=12,
        )
        self.body.controls.append(content)
        self.body.update()


def main(page: ft.Page) -> None:
    try:
        MarklotoMobile(page)
    except Exception as exc:
        page.scroll = None
        page.bgcolor = "#07090d"
        page.add(
            ft.Text(
                f"Error al abrir Markloto:\n{exc}",
                color="#f0a8c0",
                selectable=True,
            )
        )
        page.update()
