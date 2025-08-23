@echo off
REM CapSight Development Setup Script for Windows

echo 🚀 Setting up CapSight development environment...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is required but not installed. Please install Python 3.9+ and try again.
    pause
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js is required but not installed. Please install Node.js 18+ and try again.
    pause
    exit /b 1
)

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is required but not installed. Please install Docker Desktop and try again.
    pause
    exit /b 1
)

REM Create environment file if it doesn't exist
if not exist .env (
    echo 📝 Creating .env file from template...
    copy .env.example .env
    echo ⚠️  Please update .env with your API keys and configuration
)

REM Setup backend
echo 🐍 Setting up Python backend...
cd backend

REM Create virtual environment if it doesn't exist
if not exist venv (
    echo Creating Python virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing Python dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Run initial ML model training
echo Training initial ML models...
cd ..\ml\models
python arbitrage_predictor.py

cd ..\..\backend

REM Deactivate virtual environment
deactivate

cd ..

REM Setup frontend
echo ⚛️  Setting up React frontend...
cd frontend

REM Install dependencies
echo Installing Node.js dependencies...
npm install

cd ..

REM Setup database with Docker
echo 🐘 Starting database services...
docker-compose -f docker\docker-compose.yml up -d postgres redis

REM Wait for database to be ready
echo Waiting for database to be ready...
timeout /t 10

echo ✅ Setup complete!
echo.
echo 🎯 Next steps:
echo 1. Update .env file with your API keys
echo 2. Start the development servers:
echo    Backend:  cd backend ^&^& venv\Scripts\activate ^&^& python main.py
echo    Frontend: cd frontend ^&^& npm start
echo.
echo 🐳 Or use Docker:
echo    docker-compose -f docker\docker-compose.yml up
echo.
echo 📖 Visit http://localhost:3000 for the frontend
echo 📊 Visit http://localhost:8000/docs for the API documentation

pause
