@echo off
REM ============================================================
REM Landslide Early Warning System - Start Script for Windows
REM ============================================================
REM This script handles all path issues automatically.
REM Run from anywhere - it will cd to the project root.

setlocal

REM Get the directory where this script lives
set "PROJECT_DIR=%~dp0"
REM Remove trailing backslash
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

echo ============================================================
echo  Landslide Early Warning System - NER
echo  Project: %PROJECT_DIR%
echo ============================================================

cd /d "%PROJECT_DIR%"

REM Activate virtual environment
if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: .venv not found. Run: python -m venv .venv
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

REM Check if .env exists
if not exist ".env" (
    echo Creating .env from .env.example...
    copy .env.example .env >nul
)

echo.
echo Step 1: Running database migrations...
cd backend
alembic upgrade head
if %ERRORLEVEL% neq 0 (
    echo.
    echo WARNING: Migration failed. Trying to continue anyway...
    echo If SpatiaLite is missing, install OSGeo4W and set SPATIALITE_PATH in .env
)
cd ..

echo.
echo Step 2: Seeding demo data...
python scripts\seed_demo.py
if %ERRORLEVEL% neq 0 (
    echo WARNING: Seed failed. You may need SpatiaLite installed.
)

echo.
echo Step 3: Starting FastAPI server (port 8000)...
echo.

REM Start API in a new window
start "Landslide API" cmd /k "cd /d %PROJECT_DIR% && .venv\Scripts\activate && cd backend && uvicorn app.main:app --port 8000 --host 127.0.0.1"

REM Wait a moment for API to start
timeout /t 3 /nobreak >nul

echo.
echo Step 4: Starting Streamlit UI (port 8501)...
echo.
echo ============================================================
echo  Both services are starting.
echo  API:  http://127.0.0.1:8000/docs
echo  UI:   http://localhost:8501
echo ============================================================
echo.

REM Start Streamlit in current window
cd /d %PROJECT_DIR%
streamlit run frontend\app.py

endlocal
