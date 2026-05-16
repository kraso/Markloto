# Genera el instalador Windows x64 de Markloto (Setup.exe con todo incluido).
# Requisitos:
#   - Python 3.11+ x64
#   - Inno Setup 6 (https://jrsoftware.org/isdl.php) -> ISCC.exe en PATH o ruta habitual
# Salida:
#   dist\installers\windows-x64\Markloto-VERSION-win64-Setup.exe

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Version = (Get-Content "VERSION" -Raw).Trim()
$OutBase = Join-Path $Root "dist\installers\windows-x64"
$SetupName = "Markloto-$Version-win64-Setup.exe"
$SetupPath = Join-Path $OutBase $SetupName
$StagingDir = Join-Path $Root "build\windows-staging"

function Find-ISCC {
    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    foreach ($p in $candidates) {
        if (Test-Path $p) { return $p }
    }
    $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

Write-Host "==> Markloto $Version - instalador Windows x64" -ForegroundColor Cyan

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "No se encuentra 'py'. Instala Python 3.11+ x64."
}

$Iscc = Find-ISCC
if (-not $Iscc) {
    throw @"
No se encuentra Inno Setup 6 (ISCC.exe).
Instalalo desde https://jrsoftware.org/isdl.php
Durante la instalacion marca 'Inno Setup Preprocessor' y anade ISCC al PATH.
"@
}

Write-Host "==> Entorno virtual de build..." -ForegroundColor Yellow
$Venv = Join-Path $Root ".venv-build"
if (-not (Test-Path $Venv)) {
    py -3 -m venv $Venv
}
$Py = Join-Path $Venv "Scripts\python.exe"

& $Py -m pip install -q --upgrade pip
& $Py -m pip install -q -r requirements.txt -r requirements-build.txt

$SeedDb = Join-Path $Root "data\seed\loterias.sqlite"
if ($env:MARKLOTO_SKIP_SEED -eq "1") {
    Write-Host "==> Semilla: omitida (MARKLOTO_SKIP_SEED=1)" -ForegroundColor Yellow
} elseif (-not (Test-Path $SeedDb)) {
    Write-Host "==> Generando base semilla SELAE (primera vez, varios minutos)..." -ForegroundColor Yellow
    & $Py (Join-Path $Root "scripts\build_seed_db.py")
    if (-not (Test-Path $SeedDb)) {
        throw "No se genero data\seed\loterias.sqlite. Ejecuta: py -3 scripts\build_seed_db.py"
    }
} else {
    Write-Host "==> Semilla existente: data\seed\loterias.sqlite" -ForegroundColor Green
}

Write-Host "==> PyInstaller (aplicacion embebida)..." -ForegroundColor Yellow
& (Join-Path $Venv "Scripts\pyinstaller.exe") "packaging\pyinstaller\loterias.spec" --clean --noconfirm

$Built = Join-Path $Root "dist\Markloto"
if (-not (Test-Path (Join-Path $Built "Markloto.exe"))) {
    throw "No se genero dist\Markloto\Markloto.exe"
}

Write-Host "==> Preparando archivos para Inno Setup..." -ForegroundColor Yellow
if (Test-Path $StagingDir) {
    Remove-Item $StagingDir -Recurse -Force
}
New-Item -ItemType Directory -Path $StagingDir -Force | Out-Null
Copy-Item -Path (Join-Path $Built "*") -Destination $StagingDir -Recurse

Write-Host "==> Compilando instalador ($SetupName)..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path $OutBase -Force | Out-Null
$Iss = Join-Path $Root "packaging\inno-setup\markloto.iss"
& $Iscc $Iss "/DAppVersion=$Version"

if (-not (Test-Path $SetupPath)) {
    throw "No se genero el instalador en $SetupPath"
}

# Limpiar artefactos intermedios
if (Test-Path $StagingDir) {
    Remove-Item $StagingDir -Recurse -Force
}
if (Test-Path $Built) {
    Remove-Item $Built -Recurse -Force
}
$PyBuild = Join-Path $Root "build\loterias"
if (Test-Path $PyBuild) {
    Remove-Item $PyBuild -Recurse -Force
}

# Quitar paquetes portables antiguos si existen
Get-ChildItem $OutBase -Filter "Markloto-*-win64.zip" -ErrorAction SilentlyContinue | Remove-Item -Force
Get-ChildItem $OutBase -Directory -Filter "Markloto-*-win64" -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -notmatch "Setup" } |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem $OutBase -Directory -Filter "Loterias-*" -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Instalador listo." -ForegroundColor Green
Write-Host "  $SetupPath"
Write-Host ""
Write-Host "Distribuye ese .exe: instala en Program Files, menu Inicio y desinstalador." -ForegroundColor Cyan
Write-Host "Datos del usuario: %LOCALAPPDATA%\Markloto\data\" -ForegroundColor Cyan
