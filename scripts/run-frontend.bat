@echo off
REM Avvia il frontend Vite in modalita' dev (default http://localhost:5173)
setlocal enableextensions

set "SCRIPT_DIR=%~dp0"
set "FRONTEND_DIR=%SCRIPT_DIR%..\frontend"

if not exist "%FRONTEND_DIR%\package.json" (
    echo !! Frontend non inizializzato in %FRONTEND_DIR%: manca package.json.
    echo    Esegui prima scripts\setup.bat oppure inizializza Vite+React.
    exit /b 1
)

pushd "%FRONTEND_DIR%"
npm run dev
set "EXITCODE=%ERRORLEVEL%"
popd
endlocal & exit /b %EXITCODE%
