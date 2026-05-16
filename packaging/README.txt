Empaquetado Markloto
====================

Windows x64 — INSTALADOR (.exe)
-------------------------------
  1. Instala Inno Setup 6: https://jrsoftware.org/isdl.php
  2. Ejecuta:  .\scripts\build_windows.ps1
  3. Salida: dist\installers\windows-x64\Markloto-VERSION-win64-Setup.exe

Linux x64 / arm64 — PAQUETE .deb
--------------------------------
  Ejecutar EN LINUX (o WSL2 con dpkg-deb):

    sudo apt install python3 python3-venv python3-dev build-essential \
         dpkg-dev patchelf libssl-dev
    chmod +x scripts/build_linux_deb.sh
    ./scripts/build_linux_deb.sh

  Salida:
    dist/installers/linux-x64/markloto_VERSION_amd64.deb
    dist/installers/linux-arm64/markloto_VERSION_arm64.deb  (en ARM64)

  Instalar: sudo dpkg -i markloto_*_amd64.deb && sudo apt-get install -f

Base semilla (histórico SELAE, acelera la primera instalación):

  python3 scripts/build_seed_db.py

  (build_windows.ps1 y build_linux_deb.sh la generan si falta)

Configuración:
  packaging\pyinstaller\loterias.spec  -> binarios PyInstaller
  packaging\inno-setup\markloto.iss      -> Windows Setup
  packaging\debian\                      -> plantillas .deb

Android — APK (Flet)
--------------------
  En Linux / WSL2:
    ./scripts/build_android_apk.sh
  Salida: dist\installers\android\*.apk
  Desarrollo: flet run run_mobile.py

Otras plataformas: dist\installers\<plataforma>\README.txt
