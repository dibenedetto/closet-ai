# Avvia il frontend Vite in modalità dev (default http://localhost:5173)
$ErrorActionPreference = "Stop"

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$FrontendDir = Resolve-Path (Join-Path $ScriptDir "..\frontend")

if (-not (Test-Path (Join-Path $FrontendDir "package.json"))) {
    Write-Host "!! Frontend non inizializzato in $FrontendDir (manca package.json)."
    Write-Host "   Esegui prima .\scripts\setup.ps1 oppure inizializza Vite+React."
    exit 1
}

Push-Location $FrontendDir
try {
    npm run dev
} finally {
    Pop-Location
}
