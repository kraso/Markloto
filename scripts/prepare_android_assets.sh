#!/usr/bin/env bash
# Copia recursos necesarios para el APK (semilla + esquema) antes de flet build.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p assets/data/seed assets/loteria_hist

if [[ -f data/seed/loterias.sqlite ]]; then
  cp -f data/seed/loterias.sqlite assets/data/seed/
  echo "Semilla copiada a assets/data/seed/"
else
  echo "AVISO: no hay data/seed/loterias.sqlite — el APK arrancará sin histórico embebido."
  echo "       Ejecuta: python scripts/build_seed_db.py"
fi

if [[ -f data/seed/seed_info.json ]]; then
  cp -f data/seed/seed_info.json assets/data/seed/
fi

cp -f loteria_hist/schema.sql assets/loteria_hist/
echo "Recursos Android listos en assets/"
