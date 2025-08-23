#!/bin/bash

# CapSight Production Deployment Script
# This script builds and deploys CapSight to production environment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="CapSight"
BUILD_DIR="dist"
BACKEND_DIR="backend"
FRONTEND_DIR="frontend"

echo -e "${BLUE}🚀 Starting CapSight Production Deployment${NC}"
echo "=================================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check required tools
echo -e "${YELLOW}🔍 Checking required tools...${NC}"

if ! command_exists node; then
    echo -e "${RED}❌ Node.js is not installed${NC}"
    exit 1
fi

if ! command_exists npm; then
    echo -e "${RED}❌ npm is not installed${NC}"
    exit 1
fi

if ! command_exists python3; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All required tools are available${NC}"

# Environment setup
echo -e "${YELLOW}⚙️  Setting up environment...${NC}"

# Check if we're in demo mode
if [ "${DEMO_MODE:-false}" = "true" ]; then
    echo -e "${BLUE}📋 Running in DEMO MODE${NC}"
    export VITE_DEMO_MODE=true
    export DEMO_MODE=true
else
    echo -e "${BLUE}📋 Running in PRODUCTION MODE${NC}"
    export VITE_DEMO_MODE=false
    export DEMO_MODE=false
fi

# Frontend build
echo -e "${YELLOW}🏗️  Building frontend...${NC}"
cd $FRONTEND_DIR

# Install dependencies
echo "Installing frontend dependencies..."
npm ci --production=false

# Type checking
echo "Running type checks..."
npm run type-check

# Linting
echo "Running linter..."
npm run lint

# Build
echo "Building production bundle..."
npm run build

# Check build size
BUILD_SIZE=$(du -sh $BUILD_DIR | cut -f1)
echo -e "${GREEN}✅ Frontend build completed. Size: $BUILD_SIZE${NC}"

cd ..

# Backend setup
echo -e "${YELLOW}🐍 Setting up backend...${NC}"
cd $BACKEND_DIR

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing backend dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# ML dependencies (if not in demo mode)
if [ "$DEMO_MODE" != "true" ]; then
    echo "Installing ML dependencies..."
    cd ../ml
    pip install -r requirements.txt
    cd ../backend
fi

# Run database migrations
echo "Running database migrations..."
if [ "$DEMO_MODE" != "true" ]; then
    alembic upgrade head
fi

# Run tests
echo "Running backend tests..."
python -m pytest tests/ -v

echo -e "${GREEN}✅ Backend setup completed${NC}"

cd ..

# Security checks
echo -e "${YELLOW}🔒 Running security checks...${NC}"

# Frontend security audit
cd $FRONTEND_DIR
npm audit --audit-level=high
cd ..

# Backend security check
cd $BACKEND_DIR
pip-audit
cd ..

echo -e "${GREEN}✅ Security checks completed${NC}"

# Generate deployment summary
echo -e "${BLUE}📊 Deployment Summary${NC}"
echo "=================================================="
echo "Project: $PROJECT_NAME"
echo "Build Time: $(date)"
echo "Demo Mode: $DEMO_MODE"
echo "Frontend Build Size: $BUILD_SIZE"
echo "Node Version: $(node --version)"
echo "Python Version: $(python3 --version)"

# Environment variables check
echo -e "${YELLOW}🔧 Environment Configuration${NC}"
if [ "$DEMO_MODE" = "true" ]; then
    echo "✅ DEMO_MODE enabled"
    echo "✅ Sample data will be loaded"
    echo "✅ ML models will use fallback mode"
else
    echo "⚠️  PRODUCTION_MODE enabled"
    echo "⚠️  Database connection required"
    echo "⚠️  ML models training required"
    echo "⚠️  Stripe keys must be configured"
fi

# Final deployment steps
echo -e "${YELLOW}🚀 Final deployment steps...${NC}"

if [ "$DEMO_MODE" = "true" ]; then
    echo "Demo Mode Checklist:"
    echo "✅ Frontend built with demo data enabled"
    echo "✅ Backend configured for demo mode"
    echo "✅ Sample data will be auto-generated"
    echo "✅ No external API dependencies"
    
    echo -e "${GREEN}🎉 Demo deployment ready!${NC}"
    echo "To start the demo:"
    echo "1. Frontend: cd frontend && npm run preview"
    echo "2. Backend: cd backend && source venv/bin/activate && uvicorn app.main:app"
else
    echo "Production Checklist:"
    echo "⚠️  Configure environment variables (.env files)"
    echo "⚠️  Set up database connection"
    echo "⚠️  Configure Stripe payment processing"
    echo "⚠️  Set up Mapbox integration"
    echo "⚠️  Configure email service"
    echo "⚠️  Set up monitoring and logging"
    echo "⚠️  Configure SSL certificates"
    echo "⚠️  Set up backup procedures"
    
    echo -e "${YELLOW}📋 Production deployment requires additional configuration${NC}"
fi

echo ""
echo -e "${GREEN}✨ CapSight deployment completed successfully! ✨${NC}"
echo "=================================================="
