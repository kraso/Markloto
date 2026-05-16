#!/usr/bin/env bash
# Convierte finales de línea CRLF → LF en scripts .sh (útil en WSL tras editar en Windows).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
for f in scripts/*.sh packaging/debian/*.sh; do
  if [[ -f "$f" ]]; then
    sed -i 's/\r$//' "$f"
    chmod +x "$f"
    echo "OK: $f"
  fi
done
