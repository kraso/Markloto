#!/usr/bin/env bash
# Genera el AppImage de Markloto (Linux x64 o arm64) usando linuxdeploy+appimagetool.
#
# Ejecutar EN LINUX:
#   chmod +x scripts/build_linux_appimage.sh
#   ./scripts/build_linux_appimage.sh
#
# Salida:
#   dist/installers/linux-<arch>/Markloto-<VERSION>-<arch>.AppImage
#
# Requisitos (Fedora):
#   sudo dnf install python3 python3-venv python3-devel python3-tkinter gcc binutils \
#        libffi-devel openssl-devel file fuse-libs
#   Descarga automática de linuxdeploy y appimagetool (AppImage GitHub releases) a build/bin/.
#
# Nota: el AppImage incluye el binario PyInstaller completo embebido.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "ERROR: Este script debe ejecutarse en Linux." >&2
  exit 1
fi

VERSION="$(tr -d '\r\n' < VERSION)"
UNAME_M="$(uname -m)"
case "$UNAME_M" in
  x86_64)         APP_ARCH="x86_64"; OUT_DIR="linux-x64"; LINUXDEPLOY_ARCH="x86_64" ;;
  aarch64|arm64)  APP_ARCH="aarch64"; OUT_DIR="linux-arm64"; LINUXDEPLOY_ARCH="aarch64" ;;
  *)
    echo "ERROR: Arquitectura no soportada: $UNAME_M" >&2
    exit 1
    ;;
esac

APPIMAGE_NAME="Markloto-${VERSION}-${APP_ARCH}.AppImage"
OUT_BASE="$ROOT/dist/installers/$OUT_DIR"
APPIMAGE_PATH="$OUT_BASE/$APPIMAGE_NAME"
TOOLS="$ROOT/build/bin"
mkdir -p "$TOOLS"

VENV="$ROOT/.venv-build-linux"
BUILT="$ROOT/dist/Markloto"

echo "==> Markloto $VERSION — AppImage ($APP_ARCH)"

echo "==> Entorno virtual de build..."
if [[ ! -d "$VENV" ]]; then
  python3 -m venv "$VENV"
fi
# shellcheck source=/dev/null
source "$VENV/bin/activate"
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt -r requirements-build.txt

if ! python -c "import tkinter" 2>/dev/null; then
  echo "ERROR: tkinter no disponible. Fedora: sudo dnf install python3-tkinter" >&2
  exit 1
fi

SEED_DB="$ROOT/data/seed/loterias.sqlite"
if [[ "${MARKLOTO_SKIP_SEED:-}" == "1" ]]; then
  echo "==> Semilla: omitida (MARKLOTO_SKIP_SEED=1)"
elif [[ ! -f "$SEED_DB" ]]; then
  echo "==> Generando base semilla SELAE (primera vez, varios minutos)..."
  python "$ROOT/scripts/build_seed_db.py"
  if [[ ! -f "$SEED_DB" ]]; then
    echo "ERROR: No se generó data/seed/loterias.sqlite" >&2
    exit 1
  fi
else
  echo "==> Semilla existente: data/seed/loterias.sqlite"
fi

echo "==> PyInstaller..."
pyinstaller packaging/pyinstaller/loterias.spec --clean --noconfirm

if [[ ! -x "$BUILT/Markloto" ]]; then
  echo "ERROR: No se generó dist/Markloto/Markloto" >&2
  exit 1
fi

# Descargar herramientas (linuxdeploy y appimagetool) si no están.
LINUXDEPLOY="$TOOLS/linuxdeploy.AppImage"
APPIMAGETOOL="$TOOLS/appimagetool.AppImage"
BASE_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous"
if [[ ! -x "$LINUXDEPLOY" ]]; then
  echo "==> Descargando linuxdeploy..."
  curl -L --fail -o "$LINUXDEPLOY" \
    "https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-${LINUXDEPLOY_ARCH}.AppImage"
  chmod +x "$LINUXDEPLOY"
fi
if [[ ! -x "$APPIMAGETOOL" ]]; then
  echo "==> Descargando appimagetool..."
  curl -L --fail -o "$APPIMAGETOOL" \
    "$BASE_URL/appimagetool-${LINUXDEPLOY_ARCH}.AppImage"
  chmod +x "$APPIMAGETOOL"
fi

# En entornos sin FUSE, extraer y ejecutar la app interna de los .AppImage.
run_appimage() {
  local tool="$1"; shift
  if "$tool" --appimage-help >/dev/null 2>&1; then
    "$tool" "$@"
  else
    echo "FUSE no disponible: usare --appimage-extract-and-run."
    "$tool" --appimage-extract-and-run "$@"
  fi
}

APPDIR="$ROOT/build/AppDir"
echo "==> Montando AppDir..."
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/lib/markloto"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"

cp -a "$BUILT"/. "$APPDIR/usr/lib/markloto/"

sed 's/\r$//' packaging/appimage/AppRun > "$APPDIR/AppRun"
chmod +x "$APPDIR/AppRun"

sed 's/\r$//' packaging/appimage/markloto.desktop > "$APPDIR/usr/share/applications/markloto.desktop"

# Icono: usar assets/icon.png como icono de la app.
cp assets/icon.png "$APPDIR/usr/share/icons/hicolor/256x256/apps/markloto.png"

# Enlace que linuxdeploy/appimagetool esperan en la raíz del AppDir.
cp "$APPDIR/usr/share/applications/markloto.desktop" "$APPDIR/markloto.desktop"
cp "$APPDIR/usr/share/icons/hicolor/256x256/apps/markloto.png" "$APPDIR/markloto.png"
# .DirIcon: icono que muestran los gestores de archivos/menús para el AppImage.
cp "$APPDIR/markloto.png" "$APPDIR/.DirIcon"

echo "==> linuxdeploy (usa el binario PyInstaller como ejecutable)..."
# linuxdeploy espera el binario en usr/bin con el nombre de la app.
cp -a "$APPDIR/usr/lib/markloto/Markloto" "$APPDIR/usr/bin/markloto"
run_appimage "$LINUXDEPLOY" --appdir "$APPDIR" \
  --desktop-file "$APPDIR/usr/share/applications/markloto.desktop" \
  --icon-file "$APPDIR/usr/share/icons/hicolor/256x256/apps/markloto.png" \
  --output appimage \
  2>"$ROOT/build/appimage-output.log" || {
    echo "linuxdeploy fallo (log: build/appimage-output.log)." >&2
    tail -n 40 "$ROOT/build/appimage-output.log" >&2
    exit 1
  }

# El AppImage se genera en la raíz del proyecto o en el AppDir; búsquelo.
FOUND="$( \
  ls -1 "$ROOT"/Markloto-*.AppImage "$ROOT"/build/AppDir/Markloto-*.AppImage 2>/dev/null \
  | grep -i "AppImage" | head -1 || true)"
if [[ -z "$FOUND" ]]; then
  echo "ERROR: No se generó el AppImage." >&2
  exit 1
fi

mkdir -p "$OUT_BASE"
rm -f "$APPIMAGE_PATH"
cp -f "$FOUND" "$APPIMAGE_PATH"
chmod +x "$APPIMAGE_PATH"

rm -rf "$APPDIR"
rm -f "$ROOT"/Markloto-*.AppImage
if [[ "${MARKLOTO_CLEAN_DIST:-}" == "1" ]]; then
  rm -rf "$BUILT" "$ROOT/build/loterias"
fi

echo ""
echo "AppImage listo:"
echo "  $APPIMAGE_PATH"
echo ""
echo "Usar (sin instalar):"
echo "  chmod +x \"$APPIMAGE_PATH\" && \"$APPIMAGE_PATH\""
echo ""
echo "Datos de usuario: ~/.markloto/data/"