#!/bin/sh
# Lanzador del paquete .deb (ruta fija FHS).
APP=/usr/share/markloto/Markloto
LOG_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/markloto"
LOG_FILE="$LOG_DIR/last-run.log"

mkdir -p "$LOG_DIR"

if ! "$APP" "$@" 2>"$LOG_FILE"; then
  if command -v zenity >/dev/null 2>&1; then
    zenity --error --width=420 --title="Markloto" \
      --text="No se pudo iniciar Markloto.\n\nDetalle en:\n$LOG_FILE"
  elif command -v kdialog >/dev/null 2>&1; then
    kdialog --error "No se pudo iniciar Markloto. Ver: $LOG_FILE"
  else
    echo "markloto: error al iniciar. Ver $LOG_FILE" >&2
    tail -n 30 "$LOG_FILE" >&2
  fi
  exit 1
fi
