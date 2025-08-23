#!/bin/bash
set -e

echo "========================================="
echo "CapSight Production Deployment Script"
echo "========================================="

# Check if Docker is running
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "ERROR: Docker daemon is not running"
    exit 1
fi

echo "Step 1: Building and starting services..."
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

echo "Step 2: Waiting for services to start..."
sleep 30

echo "Step 3: Running database migrations..."
docker-compose -f docker-compose.prod.yml exec -T backend alembic upgrade head

echo "Step 4: Checking service health..."
docker-compose -f docker-compose.prod.yml ps

echo "Step 5: Testing API endpoint..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Health check passed"
else
    echo "⚠️  WARNING: Health check failed. Check logs with:"
    echo "docker-compose -f docker-compose.prod.yml logs backend"
fi

echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo "API: http://localhost:8000"
echo "Docs: http://localhost:8000/docs"
echo "Health: http://localhost:8000/health"
echo "========================================="

echo "To view logs: docker-compose -f docker-compose.prod.yml logs -f"
echo "To stop: docker-compose -f docker-compose.prod.yml down"
