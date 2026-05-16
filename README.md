# Markloto

Aplicación de escritorio para **análisis histórico** de Euromillones, Bonoloto y La Primitiva (datos [SELAE](https://www.loteriasyapuestas.es)). No predice resultados ni garantiza premios.

- **Python 3.11+** · CustomTkinter · SQLite · sincronización SELAE (`curl_cffi`)
- **Plataformas:** Windows (instalador `.exe`), Linux (paquete `.deb`)

## Uso en desarrollo

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux:   source .venv/bin/activate
pip install -r requirements.txt
python run_gui.py
```

Base de datos local en desarrollo: `data/loterias.sqlite`

## Empaquetado local

| Plataforma | Comando | Salida |
|------------|---------|--------|
| Windows | `.\scripts\build_windows.ps1` | `dist/installers/windows-x64/Markloto-*-Setup.exe` |
| Linux | `./scripts/build_linux_deb.sh` | `dist/installers/linux-x64/markloto_*_amd64.deb` |

Detalles: [`packaging/README.txt`](packaging/README.txt)

### Base semilla (recomendado antes de release)

```bash
python scripts/build_seed_db.py
```

Genera `data/seed/loterias.sqlite` para que la primera instalación no descargue décadas de histórico.

## CI / Releases en GitHub

| Workflow | Cuándo | Qué hace |
|----------|--------|----------|
| [CI](.github/workflows/ci.yml) | Push / PR a `main` | Sintaxis e imports |
| [Release](.github/workflows/release.yml) | Etiqueta `v*` | `.deb` + Setup.exe + GitHub Release |

```bash
git tag v1.0.0
git push origin v1.0.0
```

Guía detallada: [`.github/RELEASING.md`](.github/RELEASING.md)

En la primera release, el job de semilla puede tardar **30–90 minutos** (histórico SELAE); luego la caché de Actions acelera los builds.

## Estructura

```
app/              Interfaz (pestañas, widgets)
loteria_hist/     BD, SELAE, análisis, exportación Excel
packaging/        PyInstaller, Inno Setup, Debian
scripts/          Build semilla, Windows, Linux
```

## Datos del usuario (instalado)

| SO | Ubicación |
|----|-----------|
| Windows | `%LOCALAPPDATA%\Markloto\data\` |
| Linux | `~/.markloto/data/` |

## Autor

Marcos Calabrés Ibáñez — markbiophysicist@gmail.com

Versión actual: ver archivo [`VERSION`](VERSION).
