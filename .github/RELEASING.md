# Publicar una versión en GitHub

## 1. Preparar el repositorio (solo la primera vez)

```bash
cd /ruta/a/Loterías
git init
git add .
git commit -m "Initial commit: Markloto"
git branch -M main
git remote add origin https://github.com/kraso/Markloto.git
git push -u origin main
```

Si `origin` ya existe con una URL incorrecta:  
`git remote set-url origin https://github.com/kraso/Markloto.git`

## 2. Comprobar la versión

Edita el archivo `VERSION` (por ejemplo `1.0.0`). Debe coincidir con la etiqueta que vas a crear (`v1.0.0`).

## 3. Crear release automática

```bash
git add .
git commit -m "Release 1.0.0"
git push origin main
git tag v1.0.0
git push origin v1.0.0
```

Al subir la etiqueta `v*`, se ejecuta el workflow **Release**:

1. Genera (o restaura desde caché) la base semilla SELAE.
2. Construye `markloto_*_amd64.deb` en Linux.
3. Construye `Markloto-*-win64-Setup.exe` en Windows.
4. Construye el APK Android (Flet).
5. Publica los archivos y `SHA256SUMS.txt` en **GitHub Releases** (incluye `.apk` arm64-v8a recomendado para móviles actuales).

La primera vez, el paso de semilla puede tardar bastante (histórico completo de los tres juegos).

## 4. Build manual (sin publicar Release)

En GitHub: **Actions → Release → Run workflow**

- Marca **Omitir semilla** si solo quieres probar el empaquetado (instaladores sin histórico embebido).
- Los `.deb` y `.exe` quedan como artefactos descargables en esa ejecución (no crea Release).

Para publicar después, crea y sube la etiqueta:

```bash
git tag v1.0.0
git push origin v1.0.0
```

## 5. CI en cada push

El workflow **CI** valida imports y sintaxis en Ubuntu en cada push/PR a `main`.
