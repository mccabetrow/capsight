@echo off
echo =========================================
echo CapSight Production Deployment Script
echo =========================================

REM Check if Docker is running
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not installed or not running
    echo Please install Docker Desktop and try again
    pause
    exit /b 1
)

echo Step 1: Building and starting services...
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

echo Step 2: Waiting for services to start...
timeout /t 30 >nul

echo Step 3: Running database migrations...
docker-compose -f docker-compose.prod.yml exec -T backend alembic upgrade head

echo Step 4: Checking service health...
docker-compose -f docker-compose.prod.yml ps

echo Step 5: Testing API endpoint...
curl -f http://localhost:8000/health || (
    echo WARNING: Health check failed. Check logs with:
    echo docker-compose -f docker-compose.prod.yml logs backend
)

echo =========================================
echo Deployment Complete!
echo =========================================
echo API: http://localhost:8000
echo Docs: http://localhost:8000/docs
echo Health: http://localhost:8000/health
echo =========================================

echo To view logs: docker-compose -f docker-compose.prod.yml logs -f
echo To stop: docker-compose -f docker-compose.prod.yml down

pause
