#!/bin/bash
# CapSight Development Setup Script

set -e

echo "🚀 Setting up CapSight development environment..."

# Check if required tools are installed
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 is required but not installed. Aborting." >&2; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ Node.js is required but not installed. Aborting." >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed. Aborting." >&2; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose is required but not installed. Aborting." >&2; exit 1; }

# Create environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please update .env with your API keys and configuration"
fi

# Setup backend
echo "🐍 Setting up Python backend..."
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Run initial ML model training
echo "Training initial ML models..."
cd ../ml/models
python arbitrage_predictor.py

cd ../../backend

# Generate database migration
echo "Setting up database..."
alembic init alembic || echo "Alembic already initialized"

cd ..

# Setup frontend
echo "⚛️  Setting up React frontend..."
cd frontend

# Install dependencies
echo "Installing Node.js dependencies..."
npm install

cd ..

# Setup database with Docker
echo "🐘 Starting database services..."
docker-compose -f docker/docker-compose.yml up -d postgres redis

# Wait for database to be ready
echo "Waiting for database to be ready..."
sleep 10

# Run database initialization
docker-compose -f docker/docker-compose.yml exec postgres psql -U capsight -d capsight_db -f /docker-entrypoint-initdb.d/init.sql || echo "Database already initialized"

echo "✅ Setup complete!"
echo ""
echo "🎯 Next steps:"
echo "1. Update .env file with your API keys"
echo "2. Start the development servers:"
echo "   Backend:  cd backend && source venv/bin/activate && python main.py"
echo "   Frontend: cd frontend && npm start"
echo ""
echo "🐳 Or use Docker:"
echo "   docker-compose -f docker/docker-compose.yml up"
echo ""
echo "📖 Visit http://localhost:3000 for the frontend"
echo "📊 Visit http://localhost:8000/docs for the API documentation"
