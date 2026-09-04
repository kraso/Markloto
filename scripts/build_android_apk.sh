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

VERSION="$(tr -d '\r\n' < "$ROOT/VERSION")"
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
python -m pip install -q "flet==0.85.1"  # 0.86.x incluye serious_python 4.6 que genera app.zip >4GB (bug Flet)

if [[ "${MARKLOTO_SKIP_SEED:-}" != "1" ]] && [[ ! -f data/seed/loterias.sqlite ]]; then
  echo "==> Generando semilla (puede tardar)..."
  pip install -q -r requirements.txt
  python scripts/build_seed_db.py
fi

chmod +x scripts/prepare_android_assets.sh
./scripts/prepare_android_assets.sh

echo "==> flet build apk (split por ABI)..."
# Clean previous build artifacts that serious_python would otherwise include in app.zip.
# The 'build/' dir from a prior run (Flutter SDK ~1.9 GB) makes APKs enormous.
rm -rf build/
export FLET_BUILD_VERBOSE=1
set +e
# No usar --project: en rutas con enlace provoca ValueError al renombrar el APK.
# --template: usa nuestro template parcheado con BlankScreen #0c1018 + themeMode:dark
flet build apk --split-per-abi \
  --template gh:kraso/flet-template-markloto \
  --template-dir build \
  --template-ref main \
  --clear-cache
FLET_RC=$?
set -e
if [[ "$FLET_RC" -ne 0 ]]; then
  echo "AVISO: flet build terminó con código $FLET_RC (suele fallar solo al copiar/renombrar; buscando APK...)" >&2
fi

echo "==> Copiando APKs a $OUT_DIR..."
mkdir -p "$OUT_DIR"
for apk_file in "$ROOT"/build/app/outputs/flutter-apk/*-release.apk; do
  if [[ -f "$apk_file" ]]; then
    base_name=$(basename "$apk_file")
    # Renombrar: app-arm64-v8a-release.apk -> markloto_VERSION_arm64-v8a-release.apk
    arch=$(echo "$base_name" | sed 's/app-//; s/-release\.apk//')
    dest="$OUT_DIR/markloto_${VERSION}_${arch}.apk"
    cp "$apk_file" "$dest"
    echo "  -> $dest"
  fi
done

echo "==> ¡Listo!"
