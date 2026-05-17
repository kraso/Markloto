"""Utilidades de interfaz (throttle de actualizaciones Tk)."""

from __future__ import annotations

from collections.abc import Callable


class ThrottledCallback:
    """Agrupa llamadas frecuentes (p. ej. progreso SELAE) para no saturar el hilo UI."""

    def __init__(
        self,
        widget,
        callback: Callable[[str], None],
        *,
        interval_ms: int = 400,
    ) -> None:
        self._widget = widget
        self._callback = callback
        self._interval_ms = max(50, interval_ms)
        self._pending: str | None = None
        self._after_id: str | None = None

    def push(self, message: str) -> None:
        self._pending = message
        if self._after_id is not None:
            try:
                self._widget.after_cancel(self._after_id)
            except Exception:
                pass
        self._after_id = self._widget.after(self._interval_ms, self._flush)

    def flush_now(self) -> None:
        if self._after_id is not None:
            try:
                self._widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        self._flush()

    def _flush(self) -> None:
        self._after_id = None
        msg = self._pending
        self._pending = None
        if not msg:
            return
        try:
            if self._widget.winfo_exists():
                self._callback(msg)
        except Exception:
            pass
