# Spec de rpm para Markloto (Fedora / cualquier distro RPM).
# Generado por scripts/build_linux_rpm.sh sustituyendo @VERSION@ y @ARCH@.
#
# La app se distribuye como binario PyInstaller ya compilado (dist/Markloto)
# empaquetado en SOURCES/markloto-dist.tar.gz. Aquí solo se instala en FHS.

Name:           markloto
Version:        @VERSION@
Release:        1%{?dist}
Summary:        Markloto — análisis histórico de loterías SELAE

License:        Proprietary
URL:            https://github.com/kraso/Markloto
BuildArch:      @ARCH@

Source0:        markloto-dist.tar.gz
Source1:        markloto.launcher.sh
Source2:        markloto.desktop
Source3:        copyright
Source4:        LEEME-instalacion.txt

# El binario PyInstaller ya embebe tkinter, libX11, libssl, sqlite, etc.
# Solo se requieren bibliotecas base del sistema.
Requires:       glibc, fontconfig, libgcc

%description
Markloto es una aplicación de escritorio para consultar estadísticas
históricas de Euromillones, Bonoloto y La Primitiva (datos SELAE).

No predice resultados ni garantiza premios. Uso informativo.

%prep
%setup -q -c -n markloto-src

%build
# Nada que compilar: el binario llega ya compilado en la tar.

%install
mkdir -p %{buildroot}/usr/share/markloto
cp -a Markloto/. %{buildroot}/usr/share/markloto/
chmod -R a+rX %{buildroot}/usr/share/markloto
chmod +x %{buildroot}/usr/share/markloto/Markloto

mkdir -p %{buildroot}/usr/bin
install -m 0755 %{SOURCE1} %{buildroot}/usr/bin/markloto

mkdir -p %{buildroot}/usr/share/applications
install -m 0644 %{SOURCE2} %{buildroot}/usr/share/applications/markloto.desktop

mkdir -p %{buildroot}/usr/share/doc/markloto
install -m 0644 %{SOURCE3} %{buildroot}/usr/share/doc/markloto/copyright
install -m 0644 %{SOURCE4} %{buildroot}/usr/share/doc/markloto/README.txt

%post
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database -q /usr/share/applications 2>/dev/null || true
fi
exit 0

%preun
if [ "$1" -eq 0 ]; then
  if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications 2>/dev/null || true
  fi
fi
exit 0

%files
%defattr(-,root,root,-)
/usr/share/markloto/*
/usr/bin/markloto
/usr/share/applications/markloto.desktop
/usr/share/doc/markloto/copyright
/usr/share/doc/markloto/README.txt

%changelog
* Thu Sep 10 2026 Marcos Calabrés Ibáñez <markbiophysicist@gmail.com> - 1.0.5-1
- Primer paquete rpm Markloto 1.0.5 (Flet/Android fijado y paquete de escritorio).