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
flet build apk --split-per-abi --clear-cache
FLET_RC=$?
set -e
if [[ "$FLET_RC" -ne 0 ]]; then
  echo "AVISO: flet build terminó con código $FLET_RC (suele fallar solo al copiar/renombrar; buscando APK...)" >&2
fi

FLUTTER_DIR="$ROOT/build/flutter"
if [[ ! -d "$FLUTTER_DIR" ]]; then
  echo "ERROR: No existe $FLUTTER_DIR — flet build no generó el projecto Flutter." >&2
  exit 1
fi

echo "==> Parcheando NormalTheme (styles.xml)..."
# El template flet-build-template usa "?android:colorBackground" en el NormalTheme, que en
# tema claro (Theme.Light) es BLANCO. Flutter quitamos el splash y aplica NormalTheme antes
# de que el Flutter UI renderice o que serious_python arranque Python → pantalla blanca.
# Parcheamos styles.xml para usar #0c1018 (dark theme de Markloto).
for styles in \
  "$FLUTTER_DIR/android/app/src/main/res/values/styles.xml" \
  "$FLUTTER_DIR/android/app/src/main/res/values-night/styles.xml"; do
  if [[ -f "$styles" ]]; then
    sed -i 's|?android:colorBackground|#0c1018|g' "$styles"
    echo "  -> $styles (NormalTheme parcheado)"
  fi
done

echo "==> Parcheando main.dart (BlankScreen + MaterialApp dark)..."
MAIN_DART="$FLUTTER_DIR/lib/main.dart"
# BlankScreen: Scaffold const -> add backgroundColor Color(0xFF0c1018)
# This forces the Dart source content hash to change, invalidating Gradle/Dart cache.
sed -i 's|body: SizedBox.shrink(),|body: SizedBox.shrink(),\n      backgroundColor: Color(0xFF0c1018),|g' "$MAIN_DART"
# MaterialApp loading state: add themeMode: ThemeMode.dark + darkTheme
sed -i 's|return MaterialApp(|return MaterialApp(themeMode: ThemeMode.dark, darkTheme: ThemeData.dark(), |' "$MAIN_DART"

echo "  -> main.dart parcheado:"
grep -n "backgroundColor\|themeMode\|darkTheme" "$MAIN_DART" | head -5

echo "==> Parcheando flutter_native_splash color en pubspec.yaml..."
PUBspec="$FLUTTER_DIR/pubspec.yaml"
sed -i "s|color: '#ffffff'|color: '#0c1018'|g" "$PUBspec"
sed -i "s|color_dark: '#222222'|color_dark: '#0c1018'|g" "$PUBspec"

echo "==> flutter build apk (rebuild con todos los parches de Dart)..."
# Force Dart recompilation by clearing the Gradle build cache + Dart kernel cache.
# The "--no-build-cache" flag is a Gradle flag that must be passed AFTER "--".
FLUTTER_SDK_DIR="$HOME/flutter"
export PATH="$FLUTTER_SDK_DIR:$PATH"
for fv in "$FLUTTER_SDK_DIR"/*/; do
  [[ -d "$fv/bin" ]] && export PATH="$fv/bin:$PATH"
done
FLUTTER_BIN=$(command -v flutter 2>/dev/null || echo "$FLUTTER_SDK_DIR/3.41.7/bin")
if [[ -z "$FLUTTER_BIN" || "$FLUTTER_BIN" == "$FLUTTER_SDK_DIR/3.41.7/bin" ]]; then
  echo "  -> flutter encontrado via PATH de flet"
else
  echo "  -> flutter encontrado en: $FLUTTER_BIN"
fi

cd "$FLUTTER_DIR"
# Clear Dart kernel cache to force full recompilation.
rm -rf .dart_tool/flutter_build
rm -rf build/app/intermediates/mergedJsCompiled
# Use --no-build-cache (Gradle flag) to disable build cache, forcing full rebuild.
set +e
flutter build apk --split-per-abi --no-build-cache 2>&1
FLUTTER_RC=$?
set -e
if [[ "$FLUTTER_RC" -ne 0 ]]; then
  echo "  -> ADVERTENCIA: flutter build apk terminó con código $FLUTTER_RC" >&2
  # The APKs might still have been generated; continue.
fi
cd "$ROOT"

echo "==> Copiando APKs a $OUT_DIR..."
mkdir -p "$OUT_DIR"
for apk_file in "$FLUTTER_DIR"/build/app/outputs/flutter-apk/*-release.apk; do
  if [[ -f "$apk_file" ]]; then
    base_name=$(basename "$apk_file")
    arch=$(echo "$base_name" | sed 's/app-//; s/-release\.apk//')
    dest="$OUT_DIR/markloto_${VERSION}_${arch}.apk"
    cp "$apk_file" "$dest"
    echo "  -> $dest"
  fi
done

echo "==> ¡Listo!"
