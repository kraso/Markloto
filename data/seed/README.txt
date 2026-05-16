Base de datos semilla (loterias.sqlite)
======================================

Para que la instalación sea rápida, genera la semilla antes de compilar el instalador:

  py -3 scripts/build_seed_db.py

Eso descarga todo el histórico SELAE (varios minutos) y crea:

  - loterias.sqlite
  - seed_info.json

Si no existe loterias.sqlite aquí, la app creará una BD vacía y hará la
primera sincronización completa en segundo plano (más lenta).

El instalador empaqueta estos archivos si están presentes al ejecutar
scripts\build_windows.ps1
