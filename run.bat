@echo off
REM Q-GREEN CORRIDOR — one-command startup for Windows (double-click friendly)
setlocal

set ROOT_DIR=%~dp0
set BACKEND_DIR=%ROOT_DIR%backend
set FRONTEND_DIR=%ROOT_DIR%frontend

echo ==============================================
echo  Q-GREEN CORRIDOR - starting local prototype
echo ==============================================

if not exist "%BACKEND_DIR%\.venv" (
    echo [backend] creating virtual environment...
    python -m venv "%BACKEND_DIR%\.venv"
)

echo [backend] installing Python dependencies...
call "%BACKEND_DIR%\.venv\Scripts\pip.exe" install -q -r "%ROOT_DIR%requirements.txt"

if not exist "%BACKEND_DIR%\data\city_network.json" (
    echo [backend] generating simulated city network...
    pushd "%BACKEND_DIR%\data"
    call "%BACKEND_DIR%\.venv\Scripts\python.exe" generate_city.py
    popd
)

echo [backend] starting FastAPI server on http://localhost:8000 ...
start "QGC-Backend" cmd /k "cd /d %BACKEND_DIR% && %BACKEND_DIR%\.venv\Scripts\uvicorn.exe main:app --host 0.0.0.0 --port 8000 --reload"

echo [frontend] installing npm dependencies (first run only)...
pushd "%FRONTEND_DIR%"
call npm install --silent
echo [frontend] starting Vite dev server on http://localhost:5173 ...
start "QGC-Frontend" cmd /k "npm run dev -- --host"
popd

echo.
echo ==============================================
echo  Backend:  http://localhost:8000/docs
echo  Frontend: http://localhost:5173
echo ==============================================
echo  Two new terminal windows have opened.
echo  Close them to stop the servers.
echo.
pause
