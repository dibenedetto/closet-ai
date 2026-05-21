@echo off
REM Setup ClosetAI su Windows (cmd.exe):
REM   - installa uv se mancante
REM   - installa Python 3.14 via uv
REM   - sincronizza le dipendenze del backend
REM   - installa le dipendenze del frontend (se presente)
REM Nota cmd.exe: NON usare parentesi tonde nei messaggi echo dentro blocchi
REM if/else (...), chiudono il blocco e causano il classico errore di parser.
setlocal enableextensions

set "SCRIPT_DIR=%~dp0"
REM Normalizza ROOT_DIR (toglie il \.. finale) usando pushd/popd
pushd "%SCRIPT_DIR%.." >nul
set "ROOT_DIR=%CD%"
popd >nul
set "BACKEND_DIR=%ROOT_DIR%\backend"
set "FRONTEND_DIR=%ROOT_DIR%\frontend"

echo ==^> ClosetAI setup root: %ROOT_DIR%

where uv >nul 2>nul
if errorlevel 1 (
    echo ==^> uv non trovato, installo via script ufficiale
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    if errorlevel 1 (
        echo !! Installazione uv fallita.
        exit /b 1
    )
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
) else (
    echo ==^> uv gia' installato
)

echo ==^> Installo Python 3.14 via uv
uv python install 3.14
if errorlevel 1 (
    echo !! uv python install 3.14 fallito.
    exit /b 1
)

if exist "%BACKEND_DIR%\pyproject.toml" (
    echo ==^> Sincronizzo dipendenze backend
    pushd "%BACKEND_DIR%"
    uv sync
    if errorlevel 1 (
        popd
        echo !! uv sync fallito.
        exit /b 1
    )
    popd
) else (
    echo ==^> Backend non ancora inizializzato: manca pyproject.toml -- salto uv sync
)

if exist "%FRONTEND_DIR%\package.json" (
    where npm >nul 2>nul
    if errorlevel 1 (
        echo !! npm non trovato. Installa Node.js ^>= 20 da https://nodejs.org/ e riesegui.
        exit /b 1
    )
    echo ==^> Installo dipendenze frontend
    pushd "%FRONTEND_DIR%"
    npm install
    if errorlevel 1 (
        popd
        echo !! npm install fallito.
        exit /b 1
    )
    popd
) else (
    echo ==^> Frontend non ancora inizializzato: manca package.json -- salto npm install
)

echo ==^> Setup completato.
endlocal
