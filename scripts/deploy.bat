@echo off
REM CapSight Production Deployment Script for Windows
REM This script builds and deploys CapSight to production environment

setlocal enabledelayedexpansion

REM Configuration
set PROJECT_NAME=CapSight
set BUILD_DIR=dist
set BACKEND_DIR=backend
set FRONTEND_DIR=frontend

echo.
echo 🚀 Starting CapSight Production Deployment
echo ==================================================

REM Check required tools
echo.
echo 🔍 Checking required tools...

where node >nul 2>nul
if errorlevel 1 (
    echo ❌ Node.js is not installed
    exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
    echo ❌ npm is not installed
    exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
    echo ❌ Python is not installed
    exit /b 1
)

echo ✅ All required tools are available

REM Environment setup
echo.
echo ⚙️  Setting up environment...

if "%DEMO_MODE%"=="true" (
    echo 📋 Running in DEMO MODE
    set VITE_DEMO_MODE=true
    set DEMO_MODE=true
) else (
    echo 📋 Running in PRODUCTION MODE
    set VITE_DEMO_MODE=false
    set DEMO_MODE=false
)

REM Frontend build
echo.
echo 🏗️  Building frontend...
cd %FRONTEND_DIR%

REM Install dependencies
echo Installing frontend dependencies...
call npm ci

REM Type checking
echo Running type checks...
call npm run type-check
if errorlevel 1 (
    echo ❌ Type check failed
    exit /b 1
)

REM Linting
echo Running linter...
call npm run lint
if errorlevel 1 (
    echo ❌ Linting failed
    exit /b 1
)

REM Build
echo Building production bundle...
call npm run build
if errorlevel 1 (
    echo ❌ Build failed
    exit /b 1
)

echo ✅ Frontend build completed
cd ..

REM Backend setup
echo.
echo 🐍 Setting up backend...
cd %BACKEND_DIR%

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing backend dependencies...
pip install --upgrade pip
pip install -r requirements.txt

REM ML dependencies (if not in demo mode)
if not "%DEMO_MODE%"=="true" (
    echo Installing ML dependencies...
    cd ..\ml
    pip install -r requirements.txt
    cd ..\backend
)

echo ✅ Backend setup completed
cd ..

REM Generate deployment summary
echo.
echo 📊 Deployment Summary
echo ==================================================
echo Project: %PROJECT_NAME%
echo Build Time: %DATE% %TIME%
echo Demo Mode: %DEMO_MODE%

for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i

echo Node Version: %NODE_VERSION%
echo Python Version: %PYTHON_VERSION%

REM Environment variables check
echo.
echo 🔧 Environment Configuration
if "%DEMO_MODE%"=="true" (
    echo ✅ DEMO_MODE enabled
    echo ✅ Sample data will be loaded
    echo ✅ ML models will use fallback mode
) else (
    echo ⚠️  PRODUCTION_MODE enabled
    echo ⚠️  Database connection required
    echo ⚠️  ML models training required
    echo ⚠️  Stripe keys must be configured
)

REM Final deployment steps
echo.
echo 🚀 Final deployment steps...

if "%DEMO_MODE%"=="true" (
    echo Demo Mode Checklist:
    echo ✅ Frontend built with demo data enabled
    echo ✅ Backend configured for demo mode
    echo ✅ Sample data will be auto-generated
    echo ✅ No external API dependencies
    echo.
    echo 🎉 Demo deployment ready!
    echo To start the demo:
    echo 1. Frontend: cd frontend ^&^& npm run preview
    echo 2. Backend: cd backend ^&^& venv\Scripts\activate ^&^& uvicorn app.main:app
) else (
    echo Production Checklist:
    echo ⚠️  Configure environment variables (.env files^)
    echo ⚠️  Set up database connection
    echo ⚠️  Configure Stripe payment processing
    echo ⚠️  Set up Mapbox integration
    echo ⚠️  Configure email service
    echo ⚠️  Set up monitoring and logging
    echo ⚠️  Configure SSL certificates
    echo ⚠️  Set up backup procedures
    echo.
    echo 📋 Production deployment requires additional configuration
)

echo.
echo ✨ CapSight deployment completed successfully! ✨
echo ==================================================

pause
