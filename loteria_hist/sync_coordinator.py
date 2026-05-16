"""Coordinación de sincronizaciones SELAE (una activa, cola opcional, incremental)."""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path

from .db import connect
from .sync_selae import sincronizar_selae_incremental, sincronizar_selae_retraso

ScheduleFn = Callable[[Callable[[], None]], None]


class SyncMode(str, Enum):
    INCREMENTAL = "incremental"
    FULL = "full"


@dataclass
class SyncRequest:
    mode: SyncMode = SyncMode.INCREMENTAL
    juegos: list[str] = field(default_factory=list)
    reason: str = "manual"


@dataclass
class SyncResult:
    totals: dict[str, int]
    mode: SyncMode
    reason: str


class SyncCoordinator:
    """Evita solapes: una sincronización en segundo plano; encola o ignora el resto."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self._lock = threading.Lock()
        self._running = False
        self._queued: SyncRequest | None = None

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def request(
        self,
        juegos: list[str],
        *,
        mode: SyncMode = SyncMode.INCREMENTAL,
        reason: str = "manual",
        on_progress: Callable[[str], None] | None = None,
        on_done: Callable[[SyncResult | Exception], None] | None = None,
        schedule: ScheduleFn | None = None,
    ) -> bool:
        """
        Lanza la sincronización en un hilo daemon.
        Devuelve False si ya hay una en curso y esta petición queda en cola (una sola).
        """
        req = SyncRequest(mode=mode, juegos=list(juegos), reason=reason)
        schedule = schedule or (lambda fn: fn())

        with self._lock:
            if self._running:
                self._queued = req
                if on_progress:
                    on_progress("Sincronización en curso; esta petición esperará al terminar…")
                return False
            self._running = True

        def thread_main() -> None:
            try:
                result = self._run_sync(req, on_progress)
                if on_done:
                    schedule(lambda: on_done(result))
            except Exception as exc:
                if on_done:
                    schedule(lambda: on_done(exc))
            finally:
                next_req: SyncRequest | None = None
                with self._lock:
                    self._running = False
                    if self._queued is not None:
                        next_req = self._queued
                        self._queued = None
                        self._running = True
                if next_req is not None:
                    def run_queued() -> None:
                        try:
                            result = self._run_sync(next_req, on_progress)
                            if on_done:
                                schedule(lambda: on_done(result))
                        except Exception as exc:
                            if on_done:
                                schedule(lambda: on_done(exc))
                        finally:
                            with self._lock:
                                self._running = False

                    threading.Thread(target=run_queued, daemon=True).start()

        threading.Thread(target=thread_main, daemon=True).start()
        return True

    def _run_sync(
        self,
        req: SyncRequest,
        on_progress: Callable[[str], None] | None,
    ) -> SyncResult:
        conn = connect(self.db_path)
        try:
            totals: dict[str, int] = {}
            fin = date.today()
            for j in req.juegos:
                if on_progress:
                    etiqueta = "completa" if req.mode == SyncMode.FULL else "incremental"
                    on_progress(
                        f"SELAE ({etiqueta}): {j}…"
                    )
                if req.mode == SyncMode.FULL:
                    totals[j] = sincronizar_selae_retraso(
                        conn,
                        j,
                        fecha_fin=fin,
                        fecha_min=None,
                        on_progress=on_progress,
                    )
                else:
                    totals[j] = sincronizar_selae_incremental(
                        conn,
                        j,
                        fecha_fin=fin,
                        on_progress=on_progress,
                    )
            conn.commit()
            return SyncResult(totals=totals, mode=req.mode, reason=req.reason)
        finally:
            conn.close()
