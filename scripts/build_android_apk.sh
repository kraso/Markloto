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
yes | flet build apk --split-per-abi
FLET_RC=$?
set -e
if [[ "$FLET_RC" -ne 0 ]]; then
  echo "AVISO: flet build terminó con código $FLET_RC (suele fallar solo al copiar/renombrar; buscando APK…)" >&2
fi

echo "==> Parcheando NormalTheme (fix pantalla blanca en Android)..."
# El template flet-build-template usa "?android:colorBackground" en el NormalTheme, que en
# tema claro (Theme.Light) es BLANCO. Flutter quitamos el splash y aplica NormalTheme antes
# de que el Flutter UI renderice o que serious_python arranque Python → pantalla blanca.
# Parcheamos styles.xml para usar #0c1018 (dark theme de Markloto) como fondo del NormalTheme.
FLUTTER_DIR="$ROOT/build/flutter"
if [[ ! -d "$FLUTTER_DIR" ]]; then
  echo "ERROR: No existe $FLUTTER_DIR — flet build no generó el projecto Flutter." >&2
  exit 1
fi
for styles in \
  "$FLUTTER_DIR/android/app/src/main/res/values/styles.xml" \
  "$FLUTTER_DIR/android/app/src/main/res/values-night/styles.xml"; do
  if [[ -f "$styles" ]]; then
    sed -i 's|?android:colorBackground|#0c1018|g' "$styles"
    echo "  -> $styles (NormalTheme parcheado)"
  fi
done

echo "==> flutter build apk (rebuild con NormalTheme corregido)..."
# Flet-cli instala Flutter en ~/flutter/<version>/ — no esta en PATH global.
# Añadimos el bin dir al PATH para poder llamar flutter directamente.
FLUTTER_SDK_DIR="$HOME/flutter"
export PATH="$FLUTTER_SDK_DIR:$PATH"
# Also try version-specific path
for fv in "$FLUTTER_SDK_DIR"/*/; do
  [[ -d "$fv/bin" ]] && export PATH="$fv/bin:$PATH"
done
FLUTTER_BIN=$(command -v flutter 2>/dev/null || true)
if [[ -n "$FLUTTER_BIN" ]]; then
  echo "  -> flutter encontrado en: $FLUTTER_BIN"
else
  echo "  -> ADVERTENCIA: flutter no encontrado en PATH, intentando ~/flutter/*/bin..." >&2
  export PATH="$FLUTTER_SDK_DIR/3.41.7/bin:$PATH"
fi

# Parcheamos el pubspec.yaml del flutter_dir para que flutter_native_splash
# use #0c1018 como color de splash (en vez de '#ffffff' que tiene el template).
# Esto es crítico: el flutter build apk rebuild re-ejecuta flutter_native_splash:run,
# que regenera drawable/launch_background.xml. Si el color es blanco, el splash
# inicial es blanco → pantalla blanca antes de que Flutter engine arranque.
PUBSPEC="$FLUTTER_DIR/pubspec.yaml"
if [[ -f "$PUBSPEC" ]]; then
  sed -i "s|color: '#ffffff'|color: '#0c1018'|g" "$PUBSPEC"
  sed -i "s|color_dark: '#222222'|color_dark: '#0c1018'|g" "$PUBSPEC"
  echo "  -> pubspec.yaml: flutter_native_splash color -> #0c1018"
fi

# serious_python plugin needs this env var to find site-packages.
# flet-cli sets it during flet build, but our standalone flutter rebuild needs it too.
SITE_PKGS="$ROOT/build/site-packages"
if [[ -d "$SITE_PKGS" ]]; then
  export SERIOUS_PYTHON_SITE_PACKAGES="$SITE_PKGS"
  echo "  -> SERIOUS_PYTHON_SITE_PACKAGES=$SITE_PKGS"
else
  echo "  -> ADVERTENCIA: $SITE_PKGS no existe — flutter build puede fallar" >&2
fi

echo "==> Parcheando main.dart (BlankScreen background oscuro)..."
# El template main.dart usa MaterialApp() sin theme, con BlankScreen que muestra
# Scaffold blanco durante el loading entre prepareApp() y runPythonApp().
# Parcheamos: (1) blank screen background #0c1018, (2) MaterialApp themeMode dark.
MAIN_DART="$FLUTTER_DIR/lib/main.dart"
if [[ -f "$MAIN_DART" ]]; then
  # Replace BlankScreen's empty Scaffold with a dark-background Scaffold
  sed -i 's|return const Scaffold(|return Scaffold(|g' "$MAIN_DART"
  sed -i 's|body: SizedBox.shrink(),|body: SizedBox.shrink(), backgroundColor: Color(0xFF0c1018),|g' "$MAIN_DART"
  # Add dark theme to all MaterialApp calls (so blank screen has dark background)
  sed -i 's|return MaterialApp(|return MaterialApp(themeMode: ThemeMode.dark,|g' "$MAIN_DART"
  echo "  -> main.dart parcheado (BlankScreen + MaterialApp dark theme)"
else
  echo "  -> ADVERTENCIA: $MAIN_DART no encontrado, no se puede parchear" >&2
fi

set +e
cd "$FLUTTER_DIR"
# Remove Flet's pre-built APKs so we only keep our rebuilt ones.
# NOTE: do NOT run flutter clean — it would wipe flutter_native_splash and
# flutter_launcher_icons resources generated by flet build apk.
rm -rf "$ROOT/build/apk" 2>/dev/null || true
flutter pub get --suppress-analytics 2>/dev/null || true
# Force Dart recompilation so main.dart patches take effect.
# Three approaches combined to guarantee the Dart compiler sees the patched
# main.dart (otherwise Gradle/Dart incremental cache reuses stale libapp.so):
#   1. Delete ALL intermetediates (Dart snapshot, stripDebugSymbol, etc.)
#   2. touch main.dart to invalidate Gradle's incremental build
#   3. Use --dart-define with a unique timestamp to bypass Gradle cache entirely
rm -rf "$FLUTTER_DIR/build/app/intermediates" 2>/dev/null || true
rm -rf "$FLUTTER_DIR/build/app/outputs" 2>/dev/null || true
touch "$MAIN_DART"
FORCE_DART_RECOMPILE=$(date +%s)
flutter build apk --split-per-abi --no-version-check --dart-define=FORCE_DART_RECOMPILE=$FORCE_DART_RECOMPILE --suppress-analytics
FLUTTER_RC=$?
set -e
if [[ "$FLUTTER_RC" -ne 0 ]]; then
  echo "AVISO: flutter build apk terminó con código $FLUTTER_RC" >&2
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
