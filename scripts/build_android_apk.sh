#!/usr/bin/env bash
# Genera APK(s) de Markloto con Flet. Ejecutar en Linux (o WSL2).
#
# Salida: dist/installers/android/markloto_VERSION_<abi>.apk
#
# Nota: Flet falla al renombrar APK si la ruta del proyecto tiene espacios o
# tildes (p. ej. "Loterías"). Este script compila desde ~/markloto-build (enlace).
# También falla si se pasa --project con ruta absoluta (ValueError en with_name).

set -euo pipefail

ORIG_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_LINK="${MARKLOTO_BUILD_LINK:-$HOME/markloto-build}"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "ERROR: Compila el APK en Linux o WSL2." >&2
  exit 1
fi

mkdir -p "$(dirname "$BUILD_LINK")"
ln -sfn "$ORIG_ROOT" "$BUILD_LINK"
ROOT="$BUILD_LINK"
cd "$ROOT"

VERSION="$(tr -d '\r\n' < VERSION)"
OUT_DIR="$ORIG_ROOT/dist/installers/android"
VENV="$ORIG_ROOT/.venv-build-android"

echo "==> Markloto $VERSION — APK Android"
echo "    Origen: $ORIG_ROOT"
echo "    Build:  $ROOT (enlace, evita bug Flet con tildes en la ruta)"

if [[ ! -d "$VENV" ]]; then
  python3 -m venv "$VENV"
fi
# shellcheck source=/dev/null
source "$VENV/bin/activate"
python -m pip install -q --upgrade pip
python -m pip install -q "flet>=0.85.0"

if [[ "${MARKLOTO_SKIP_SEED:-}" != "1" ]] && [[ ! -f data/seed/loterias.sqlite ]]; then
  echo "==> Generando semilla (puede tardar)..."
  pip install -q -r requirements.txt
  python scripts/build_seed_db.py
fi

chmod +x scripts/prepare_android_assets.sh
./scripts/prepare_android_assets.sh

echo "==> flet build apk (split por ABI)..."
export FLET_BUILD_VERBOSE=1
set +e
# No usar --project: en rutas con enlace provoca ValueError al renombrar el APK.
yes | flet build apk --split-per-abi
FLET_RC=$?
set -e
if [[ "$FLET_RC" -ne 0 ]]; then
  echo "AVISO: flet build terminó con código $FLET_RC (suele fallar solo al copiar/renombrar; buscando APK…)">&2
fi

mkdir -p "$OUT_DIR"
shopt -s nullglob

abi_key() {
  case "$1" in
    *arm64-v8a*) echo arm64-v8a ;;
    *armeabi-v7a*) echo armeabi-v7a ;;
    *x86_64*) echo x86_64 ;;
    *) basename "$1" ;;
  esac
}

copy_apk() {
  local src="$1"
  local abi="$2"
  local dest="$OUT_DIR/markloto_${VERSION}_${abi}-release.apk"
  cp -f "$src" "$dest"
  echo "  -> $dest"
}

# APK recién generados (más nuevos primero; sin duplicar rutas)
mapfile -t APK_CANDIDATES < <(
  find \
    "$ROOT/build/apk" \
    "$ROOT/build/flutter/build/app/outputs/flutter-apk" \
    "$ROOT/build/flutter/build/app/outputs/apk" \
    -name '*.apk' -type f -printf '%T@\t%p\n' 2>/dev/null \
    | sort -rn \
    | cut -f2- \
    | awk '!seen[$0]++'
)

declare -A ABI_DONE=()
FOUND=0
for apk in "${APK_CANDIDATES[@]}"; do
  [[ -f "$apk" ]] || continue
  key="$(abi_key "$apk")"
  [[ -n "${ABI_DONE[$key]:-}" ]] && continue
  ABI_DONE[$key]=1
  copy_apk "$apk" "$key"
  FOUND=$((FOUND + 1))
done

if [[ "$FOUND" -eq 0 ]]; then
  echo "ERROR: No se encontró ningún APK bajo build/. Revisa la salida de flet." >&2
  exit 1
fi

echo ""
echo "APK(s) listos ($FOUND):"
ls -la "$OUT_DIR"/markloto_${VERSION}_*-release.apk 2>/dev/null || ls -la "$OUT_DIR"/*.apk
echo ""
echo "En un móvil físico instala normalmente: markloto_${VERSION}_arm64-v8a-release.apk"
