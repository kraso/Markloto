"""Widgets reutilizables (Flet)."""

from __future__ import annotations

import flet as ft


def ball_chip(num: int, *, hot: bool = False, accent: str = "#a8dcff") -> ft.Container:
    bg = accent if hot else "#1e2836"
    return ft.Container(
        content=ft.Text(str(num), size=14, weight=ft.FontWeight.BOLD, color="#0c1018"),
        bgcolor=bg,
        border_radius=20,
        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
        alignment=ft.Alignment.CENTER,
    )


def balls_row(
    groups: list[tuple[list[int], str]],
    *,
    hot: set[int] | None = None,
    accent: str = "#a8dcff",
) -> ft.Row:
    hot = hot or set()
    chips: list[ft.Control] = []
    for nums, _kind in groups:
        for n in nums:
            chips.append(ball_chip(n, hot=n in hot, accent=accent))
    return ft.Row(chips, wrap=True, spacing=6, run_spacing=6)


def section_title(text: str, accent: str) -> ft.Text:
    return ft.Text(text, size=18, weight=ft.FontWeight.BOLD, color=accent)


def card(content: ft.Control, *, accent: str = "#4a5f7a") -> ft.Container:
    return ft.Container(
        content=content,
        bgcolor="#141a24",
        border=ft.Border.all(1, accent),
        border_radius=12,
        padding=16,
    )
