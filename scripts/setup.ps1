# Setup ClosetAI su Windows (PowerShell):
#   - installa uv se mancante
#   - installa Python 3.14 via uv
#   - sincronizza le dipendenze del backend
#   - installa le dipendenze del frontend (se presente)
$ErrorActionPreference = "Stop"

$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir    = Resolve-Path (Join-Path $ScriptDir "..")
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"

Write-Host "==> ClosetAI setup (root: $RootDir)"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "==> uv non trovato, installo via script ufficiale"
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    # uv viene installato in %USERPROFILE%\.local\bin: aggiungilo al PATH della sessione corrente
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
} else {
    Write-Host "==> uv già installato: $(uv --version)"
}

Write-Host "==> Installo Python 3.14 via uv"
uv python install 3.14

if (Test-Path (Join-Path $BackendDir "pyproject.toml")) {
    Write-Host "==> Sincronizzo dipendenze backend"
    Push-Location $BackendDir
    try { uv sync } finally { Pop-Location }
} else {
    Write-Host "==> Backend non ancora inizializzato (manca pyproject.toml) — salto uv sync"
}

if (Test-Path (Join-Path $FrontendDir "package.json")) {
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        Write-Host "==> Installo dipendenze frontend"
        Push-Location $FrontendDir
        try { npm install } finally { Pop-Location }
    } else {
        Write-Host "!! npm non trovato. Installa Node.js >= 20 da https://nodejs.org/ e riesegui."
        exit 1
    }
} else {
    Write-Host "==> Frontend non ancora inizializzato (manca package.json) — salto npm install"
}

Write-Host "==> Setup completato."
