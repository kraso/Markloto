#!/usr/bin/env bash
# Genera el paquete .rpm de Markloto (Linux x64 o arm64).
#
# Ejecutar EN LINUX con rpmbuild (Fedora, RHEL, CentOS, openSUSE, etc.):
#   chmod +x scripts/build_linux_rpm.sh
#   ./scripts/build_linux_rpm.sh
#
# Salida:
#   dist/installers/linux-<arch>/markloto-<VERSION>-1.<arch>.rpm
#
# Requisitos (Fedora):
#   sudo dnf install python3 python3-venv python3-devel python3-tkinter \
#        gcc binutils patch libffi-devel openssl-devel rpm-build \
#        (patchelf, si resuelve dependencias de librerías)
#   El script usa el mismo binario PyInstaller que el .deb.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "ERROR: Este script debe ejecutarse en Linux." >&2
  exit 1
fi

command -v rpmbuild >/dev/null 2>&1 || {
  echo "ERROR: Instala rpm-build (Fedora: sudo dnf install rpm-build)." >&2
  exit 1
}

VERSION="$(tr -d '\r\n' < VERSION)"
UNAME_M="$(uname -m)"
case "$UNAME_M" in
  x86_64)            RPM_ARCH="x86_64"; OUT_DIR="linux-x64" ;;
  aarch64|arm64)     RPM_ARCH="aarch64"; OUT_DIR="linux-arm64" ;;
  *)
    echo "ERROR: Arquitectura no soportada: $UNAME_M" >&2
    exit 1
    ;;
esac

RPM_NAME="markloto-${VERSION}-1.${RPM_ARCH}.rpm"
OUT_BASE="$ROOT/dist/installers/$OUT_DIR"
RPM_PATH="$OUT_BASE/$RPM_NAME"

# rpmbuild necesita una estructura SOURCES/SPECS. En /tmp evita permisos 777 en /mnt/c.
TOPDIR="$ROOT/build/rpmbuild"
if [[ "$(uname -r 2>/dev/null)" == *microsoft* ]] && [[ "$ROOT" == /mnt/* ]]; then
  TOPDIR="/tmp/markloto-rpmbuild-$$"
  echo "AVISO: árbol rpmbuild en $TOPDIR (evita permisos 777 en /mnt/c)."
fi

VENV="$ROOT/.venv-build-linux"
BUILT="$ROOT/dist/Markloto"

echo "==> Markloto $VERSION — paquete rpm ($RPM_ARCH)"

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

echo "==> Preparando árbol rpmbuild..."
rm -rf "$TOPDIR"
mkdir -p "$TOPDIR"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}

# Tar con el árbol PyInstaller (raíz 'Markloto').
tar -C "$ROOT/dist" -czf "$TOPDIR/SOURCES/markloto-dist.tar.gz" Markloto

# Recursos del paquete: normalizar LF (CRLF rompería los shebangs).
for f in markloto.launcher.sh markloto.desktop copyright LEEME-instalacion.txt; do
  sed 's/\r$//' "packaging/rpm/$f" > "$TOPDIR/SOURCES/$f"
done

# Icono de la app (Icon=markloto en el .desktop).
cp assets/icon.png "$TOPDIR/SOURCES/markloto.png"

sed -e "s/@VERSION@/$VERSION/g" \
    -e "s/@ARCH@/$RPM_ARCH/g" \
    packaging/rpm/markloto.spec > "$TOPDIR/SPECS/markloto.spec"

echo "==> rpmbuild..."
rpmbuild --define "_topdir $TOPDIR" --define "_binary_payload w9.gzdio" \
    -bb "$TOPDIR/SPECS/markloto.spec"

mkdir -p "$OUT_BASE"
rm -f "$RPM_PATH"
cp -f "$TOPDIR"/RPMS/"$RPM_ARCH"/"$RPM_NAME" "$RPM_PATH"

rm -rf "$TOPDIR"
if [[ "${MARKLOTO_CLEAN_DIST:-}" == "1" ]]; then
  rm -rf "$BUILT" "$ROOT/build/loterias"
fi

echo ""
echo "Paquete listo:"
echo "  $RPM_PATH"
echo ""
echo "Instalar:"
echo "  sudo dnf install \"$RPM_PATH\""
echo ""
echo "Datos de usuario: ~/.markloto/data/"