#!/usr/bin/env bash
# Genera el paquete .deb de Markloto (Linux x64 o arm64).
#
# Ejecutar EN LINUX (Debian, Ubuntu, WSL2, etc.):
#   chmod +x scripts/build_linux_deb.sh
#   ./scripts/build_linux_deb.sh
#
# Salida:
#   dist/installers/linux-<arch>/markloto-VERSION-<arch>.deb
#
# Requisitos (Debian/Ubuntu):
#   sudo apt install python3 python3-venv python3-dev build-essential \
#        dpkg-dev patchelf libssl-dev

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "ERROR: Este script debe ejecutarse en Linux (o WSL2)." >&2
  exit 1
fi

command -v dpkg-deb >/dev/null 2>&1 || {
  echo "ERROR: Instala dpkg-dev: sudo apt install dpkg-dev" >&2
  exit 1
}

VERSION="$(tr -d '\r\n' < VERSION)"
UNAME_M="$(uname -m)"
case "$UNAME_M" in
  x86_64)  DEB_ARCH="amd64"; OUT_DIR="linux-x64" ;;
  aarch64|arm64) DEB_ARCH="arm64"; OUT_DIR="linux-arm64" ;;
  *)
    echo "ERROR: Arquitectura no soportada: $UNAME_M" >&2
    exit 1
    ;;
esac

DEB_NAME="markloto_${VERSION}_${DEB_ARCH}.deb"
OUT_BASE="$ROOT/dist/installers/$OUT_DIR"
DEB_PATH="$OUT_BASE/$DEB_NAME"
STAGING="$ROOT/build/deb-staging"
VENV="$ROOT/.venv-build-linux"
BUILT="$ROOT/dist/Markloto"

echo "==> Markloto $VERSION — paquete .deb ($DEB_ARCH)"

echo "==> Entorno virtual de build..."
if [[ ! -d "$VENV" ]]; then
  python3 -m venv "$VENV"
fi
# shellcheck source=/dev/null
source "$VENV/bin/activate"
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt -r requirements-build.txt

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

echo "==> Montando árbol del paquete .deb..."
rm -rf "$STAGING"
mkdir -p "$STAGING/DEBIAN"
mkdir -p "$STAGING/usr/share/markloto"
mkdir -p "$STAGING/usr/bin"
mkdir -p "$STAGING/usr/share/applications"
mkdir -p "$STAGING/usr/share/doc/markloto"

cp -a "$BUILT"/. "$STAGING/usr/share/markloto/"
chmod -R a+rX "$STAGING/usr/share/markloto"
chmod +x "$STAGING/usr/share/markloto/Markloto"

cp packaging/debian/markloto.launcher.sh "$STAGING/usr/bin/markloto"
chmod 755 "$STAGING/usr/bin/markloto"

cp packaging/debian/markloto.desktop "$STAGING/usr/share/applications/markloto.desktop"
chmod 644 "$STAGING/usr/share/applications/markloto.desktop"

cp packaging/debian/copyright "$STAGING/usr/share/doc/markloto/copyright"
cp packaging/debian/LEEME-instalacion.txt "$STAGING/usr/share/doc/markloto/README.txt"

cp packaging/debian/postinst "$STAGING/DEBIAN/postinst"
cp packaging/debian/prerm "$STAGING/DEBIAN/prerm"
chmod 755 "$STAGING/DEBIAN/postinst" "$STAGING/DEBIAN/prerm"

INSTALLED_KB="$(du -sk "$STAGING/usr" | cut -f1)"
CONTROL="$STAGING/DEBIAN/control"
sed -e "s/@VERSION@/$VERSION/g" \
    -e "s/@ARCH@/$DEB_ARCH/g" \
    -e "s/@INSTALLED_SIZE@/$INSTALLED_KB/" \
    packaging/debian/control.template > "$CONTROL"

mkdir -p "$OUT_BASE"
rm -f "$DEB_PATH"
dpkg-deb --root-owner-group --build "$STAGING" "$DEB_PATH"

rm -rf "$STAGING"
# Mantener dist/Markloto para depuración; opcional limpiar build/pyinstaller
if [[ "${MARKLOTO_CLEAN_DIST:-}" == "1" ]]; then
  rm -rf "$BUILT" "$ROOT/build/loterias"
fi

echo ""
echo "Paquete listo:"
echo "  $DEB_PATH"
echo ""
echo "Instalar:"
echo "  sudo dpkg -i \"$DEB_PATH\""
echo "  sudo apt-get install -f"
echo ""
echo "Datos de usuario: ~/.markloto/data/"
