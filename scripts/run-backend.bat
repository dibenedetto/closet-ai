@echo off
REM Avvia il backend FastAPI in modalita' reload su http://localhost:8000
setlocal enableextensions

set "SCRIPT_DIR=%~dp0"
set "BACKEND_DIR=%SCRIPT_DIR%..\backend"

pushd "%BACKEND_DIR%"
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
set "EXITCODE=%ERRORLEVEL%"
popd
endlocal & exit /b %EXITCODE%
