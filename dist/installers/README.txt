Instaladores por plataforma
==========================

Cada subcarpeta contiene el paquete listo para esa plataforma.
No hace falta instalar Python: va incluido en el ejecutable (escritorio).

  windows-x64\     Windows 10/11 — Markloto-x.x.x-win64-Setup.exe
                   (scripts\build_windows.ps1 + Inno Setup 6)

  linux-x64\       Debian/Ubuntu amd64 — markloto_x.x.x_amd64.deb
  linux-arm64\     Debian/Ubuntu arm64 — markloto_x.x.x_arm64.deb
                   (scripts/build_linux_deb.sh en Linux o WSL2)

  macos\           macOS — pendiente
  android\         Android — pendiente (app distinta)
  ios\             iOS — pendiente (app distinta)

Compilar: ver packaging\README.txt
