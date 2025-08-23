.PHONY: help dev install test lint format clean migrate migrate-auto migrate-upgrade migrate-downgrade docker-build docker-up docker-down

# Default target
help:
	@echo "CapSight Backend Development Commands"
	@echo "====================================="
	@echo ""
	@echo "Setup & Installation:"
	@echo "  install          Install dependencies"
	@echo "  dev              Run development server"
	@echo ""
	@echo "Database:"
	@echo "  migrate          Create new migration"
	@echo "  migrate-auto     Create automatic migration"
	@echo "  migrate-upgrade  Apply migrations"
	@echo "  migrate-downgrade Revert last migration"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint             Run linting checks"
	@echo "  format           Format code"
	@echo "  test             Run tests"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build     Build Docker image"
	@echo "  docker-up        Start services with docker-compose"
	@echo "  docker-down      Stop docker-compose services"
	@echo ""
	@echo "Utilities:"
	@echo "  clean            Clean cache and temp files"

# Installation and setup
install:
	pip install -r requirements.txt

# Development server
dev:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Database migrations
migrate:
	alembic revision --autogenerate -m "$(message)"

migrate-auto:
	alembic revision --autogenerate -m "Auto-generated migration"

migrate-upgrade:
	alembic upgrade head

migrate-downgrade:
	alembic downgrade -1

# Code quality
lint:
	flake8 app/
	mypy app/
	black --check app/
	isort --check-only app/

format:
	black app/
	isort app/

test:
	pytest tests/ -v --cov=app --cov-report=html

# Docker operations
docker-build:
	docker build -t capsight-backend .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

# Utilities
clean:
	find . -type d -name "__pycache__" -delete
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/

# Database setup (for initial setup)
db-setup:
	createdb capsight_db
	psql capsight_db -c "CREATE USER capsight_user WITH PASSWORD 'capsight_password';"
	psql capsight_db -c "GRANT ALL PRIVILEGES ON DATABASE capsight_db TO capsight_user;"

# Run all checks
check: lint test

# Development environment setup
setup: install migrate-upgrade
	@echo "Development environment setup complete!"
	@echo "Run 'make dev' to start the development server."
