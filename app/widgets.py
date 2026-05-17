from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from app import theme as T


class MetallicPanel(ctk.CTkFrame):
    """Panel con borde tipo metal pulido."""

    def __init__(
        self,
        master,
        *,
        title: str | None = None,
        accent: str | None = None,
        **kwargs,
    ):
        kwargs.setdefault("fg_color", T.BG_PANEL)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", T.BORDER_SHINE)
        kwargs.setdefault("corner_radius", 12)
        super().__init__(master, **kwargs)

        self.grid_columnconfigure(0, weight=1)
        row = 0
        if title:
            bar = ctk.CTkFrame(self, fg_color=T.BG_ELEVATED, corner_radius=8, height=36)
            bar.grid(row=row, column=0, sticky="ew", padx=8, pady=(8, 4))
            bar.grid_propagate(False)
            ctk.CTkLabel(
                bar,
                text=title,
                font=T.FONT_HEAD,
                text_color=accent or T.ACCENT_BRIGHT,
            ).pack(side="left", padx=12, pady=4)
            row += 1
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=row, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.body.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(row, weight=1)


class NumberBall(ctk.CTkLabel):
    def __init__(
        self,
        master,
        value: int,
        *,
        kind: str = "main",
        hot: bool = False,
        size: int = 40,
        **kwargs,
    ):
        if kind == "estrella":
            fg = T.BALL_STAR_HOT if hot else T.BALL_STAR
            tc = T.GOLD_BRIGHT if hot else T.GOLD
        elif kind == "complementario":
            fg = T.BALL_COMP
            tc = T.ACCENT_BRIGHT if hot else T.ACCENT
        elif kind == "reintegro":
            fg = T.BALL_REINT
            tc = T.ROSE if hot else T.TEXT
        else:
            fg = T.BALL_MAIN_HOT if hot else T.BALL_MAIN
            tc = T.SILVER_BRIGHT if hot else T.SILVER

        super().__init__(
            master,
            text=f"{value:02d}",
            width=size,
            height=size,
            corner_radius=size // 2,
            fg_color=fg,
            text_color=tc,
            font=T.FONT_BALL,
            **kwargs,
        )


class BallRow(ctk.CTkFrame):
    """Fila de bolas para una combinación."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._balls: list[NumberBall] = []

    def set_numbers(
        self,
        groups: list[tuple[list[int], str]],
        hot_sets: set[int] | None = None,
        *,
        ball_size: int = 40,
    ) -> None:
        for w in self._balls:
            w.destroy()
        self._balls.clear()
        hot_sets = hot_sets or set()
        col = 0
        for nums, kind in groups:
            for n in nums:
                b = NumberBall(
                    self,
                    n,
                    kind=kind,
                    hot=n in hot_sets,
                    size=ball_size,
                )
                b.grid(row=0, column=col, padx=3, pady=2)
                self._balls.append(b)
                col += 1


class NumberPickerGrid(ctk.CTkFrame):
    """Rejilla de números seleccionables (toggle)."""

    def __init__(
        self,
        master,
        pool: range,
        *,
        max_select: int,
        kind: str = "main",
        accent: str | None = None,
        columns: int = 10,
        on_change: Callable[[list[int]], None] | None = None,
        label: str = "",
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._pool = list(pool)
        self._max = max(1, max_select)
        self._kind = kind
        self._accent = accent or T.ACCENT_BRIGHT
        self._on_change = on_change
        self._selected: set[int] = set()
        self._buttons: dict[int, ctk.CTkButton] = {}

        if label:
            ctk.CTkLabel(
                self,
                text=label,
                font=T.FONT_SMALL,
                text_color=T.TEXT_DIM,
            ).pack(anchor="w", pady=(0, 4))

        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(anchor="w")
        for i, n in enumerate(self._pool):
            txt = f"{n:02d}" if self._kind != "reintegro" else str(n)
            size = 36 if len(self._pool) <= 12 else 32
            btn = ctk.CTkButton(
                grid,
                text=txt,
                width=size,
                height=size,
                corner_radius=size // 2,
                font=T.FONT_SMALL,
                fg_color=T.BG_ELEVATED,
                hover_color=T.BORDER_SHINE,
                text_color=T.TEXT_DIM,
                command=lambda v=n: self._toggle(v),
            )
            r, c = divmod(i, columns)
            btn.grid(row=r, column=c, padx=2, pady=2)
            self._buttons[n] = btn
        self._refresh_buttons()

    def get_selected(self) -> list[int]:
        return sorted(self._selected)

    def set_max_select(self, max_select: int) -> None:
        self._max = max(1, max_select)
        while len(self._selected) > self._max:
            self._selected.remove(max(self._selected))
        self._refresh_buttons()
        self._fire()

    def set_selected(self, numeros: list[int]) -> None:
        self._selected = set(numeros[: self._max])
        self._refresh_buttons()
        self._fire()

    def clear(self) -> None:
        self._selected.clear()
        self._refresh_buttons()
        self._fire()

    def _toggle(self, n: int) -> None:
        if n in self._selected:
            self._selected.remove(n)
        elif len(self._selected) < self._max:
            self._selected.add(n)
        self._refresh_buttons()
        self._fire()

    def _refresh_buttons(self) -> None:
        full = len(self._selected) >= self._max
        for n, btn in self._buttons.items():
            if n in self._selected:
                btn.configure(
                    fg_color=self._accent,
                    text_color=T.BG_DEEP,
                    border_width=0,
                )
            else:
                btn.configure(
                    fg_color=T.BG_ELEVATED,
                    text_color=T.TEXT_DIM if not full else T.TEXT_MUTED,
                    border_width=0,
                    state="normal" if not full else "disabled",
                )

    def _fire(self) -> None:
        if self._on_change:
            self._on_change(self.get_selected())


class FreqGrid(ctk.CTkScrollableFrame):
    """Top números por frecuencia en mini rejilla."""

    def __init__(self, master, *, title: str, accent: str, **kwargs):
        height = kwargs.pop("height", 140)
        super().__init__(
            master,
            fg_color=T.BG_PANEL_HI,
            label_text=title,
            label_font=T.FONT_BODY,
            label_fg_color=T.BG_PANEL,
            label_text_color=accent,
            height=height,
            **kwargs,
        )
        self._accent = accent

    def load(self, freq: list[tuple[int, int]], top: int = 15) -> None:
        """Vista compacta (1 widget): mucho más rápida que barras + bolas en Linux."""
        for child in self.winfo_children():
            child.destroy()
        if not freq:
            ctk.CTkLabel(self, text="Sin datos", text_color=T.TEXT_DIM).pack()
            return
        max_c = max(c for _, c in freq) or 1
        lines: list[str] = []
        for num, count in freq[:top]:
            bar_len = max(1, int(12 * count / max_c))
            lines.append(f"{num:02d}  {'█' * bar_len} {count}")
        ctk.CTkLabel(
            self,
            text="\n".join(lines),
            font=("Consolas", 11),
            text_color=T.TEXT,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=6, pady=4)
