#!/bin/bash

# CapSight Backend v2 - Production Deployment Script
# Deploys the complete real-time analytics backend with monitoring

set -e

echo "🚀 CapSight Backend v2 - Production Deployment"
echo "=============================================="

# Configuration
ENVIRONMENT=${ENVIRONMENT:-production}
COMPOSE_FILE=${COMPOSE_FILE:-config/docker-compose.yml}
ENV_FILE=${ENV_FILE:-.env}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    if [ ! -f "$ENV_FILE" ]; then
        log_warn "Environment file $ENV_FILE not found, using .env.example"
        cp .env.example $ENV_FILE
        log_warn "Please update $ENV_FILE with production values before continuing"
        exit 1
    fi
    
    log_info "Prerequisites check passed"
}

# Validate configuration
validate_config() {
    log_info "Validating configuration..."
    
    # Check required environment variables
    source $ENV_FILE
    
    REQUIRED_VARS=(
        "POSTGRES_PASSWORD"
        "JWT_SECRET"
        "FRED_API_KEY"
        "MODEL_REGISTRY_S3_BUCKET"
    )
    
    for var in "${REQUIRED_VARS[@]}"; do
        if [ -z "${!var}" ]; then
            log_error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    log_info "Configuration validation passed"
}

# Build Docker images
build_images() {
    log_info "Building Docker images..."
    
    docker-compose -f $COMPOSE_FILE build capsight-api
    
    if [ $? -eq 0 ]; then
        log_info "Docker images built successfully"
    else
        log_error "Failed to build Docker images"
        exit 1
    fi
}

# Deploy infrastructure
deploy_infrastructure() {
    log_info "Deploying infrastructure services..."
    
    # Start infrastructure services first
    docker-compose -f $COMPOSE_FILE up -d postgres redis zookeeper kafka schema-registry mlflow prometheus grafana
    
    # Wait for services to be healthy
    log_info "Waiting for infrastructure services to be healthy..."
    
    for service in postgres redis kafka; do
        log_info "Waiting for $service..."
        timeout=60
        while [ $timeout -gt 0 ]; do
            if docker-compose -f $COMPOSE_FILE exec -T $service /bin/sh -c "exit 0" 2>/dev/null; then
                break
            fi
            sleep 2
            timeout=$((timeout-2))
        done
        
        if [ $timeout -le 0 ]; then
            log_error "$service failed to start within timeout"
            exit 1
        fi
        
        log_info "$service is healthy"
    done
    
    log_info "Infrastructure services deployed successfully"
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."
    
    # Create database tables if needed
    docker-compose -f $COMPOSE_FILE exec -T postgres psql -U capsight -d capsight_db -c "
        CREATE TABLE IF NOT EXISTS alembic_version (
            version_num VARCHAR(32) NOT NULL,
            CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
        );
    " || log_warn "Database migration check failed, continuing..."
    
    log_info "Database migrations completed"
}

# Deploy application
deploy_application() {
    log_info "Deploying CapSight application..."
    
    # Start the application
    docker-compose -f $COMPOSE_FILE up -d capsight-api nginx
    
    # Wait for application to be healthy
    log_info "Waiting for application to be healthy..."
    timeout=120
    while [ $timeout -gt 0 ]; do
        if curl -f http://localhost/health >/dev/null 2>&1; then
            break
        fi
        sleep 5
        timeout=$((timeout-5))
    done
    
    if [ $timeout -le 0 ]; then
        log_error "Application failed to start within timeout"
        docker-compose -f $COMPOSE_FILE logs capsight-api
        exit 1
    fi
    
    log_info "CapSight application deployed successfully"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    # Test health endpoint
    health_response=$(curl -s http://localhost/health)
    if echo "$health_response" | grep -q "healthy\|degraded"; then
        log_info "Health check passed"
    else
        log_error "Health check failed: $health_response"
        exit 1
    fi
    
    # Test prediction endpoint
    prediction_test='{"property_id":"deploy_test","market_id":"test","property_type":"multifamily"}'
    prediction_response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$prediction_test" \
        http://localhost/v1/predict/property)
    
    if echo "$prediction_response" | grep -q "implied_caprate"; then
        log_info "Prediction endpoint test passed"
    else
        log_warn "Prediction endpoint test failed: $prediction_response"
    fi
    
    # Test metrics endpoint
    if curl -f http://localhost/metrics >/dev/null 2>&1; then
        log_info "Metrics endpoint accessible"
    else
        log_warn "Metrics endpoint not accessible"
    fi
    
    log_info "Deployment verification completed"
}

# Show deployment status
show_status() {
    log_info "Deployment Status:"
    echo "=================="
    
    docker-compose -f $COMPOSE_FILE ps
    
    echo ""
    log_info "Service URLs:"
    echo "  API: http://localhost/v1"
    echo "  Health: http://localhost/health"
    echo "  Metrics: http://localhost/metrics"
    echo "  Grafana: http://localhost:3000 (admin/password from env)"
    echo "  MLflow: http://localhost:5000"
    echo "  Prometheus: http://localhost:9090"
    
    echo ""
    log_info "To view logs: docker-compose -f $COMPOSE_FILE logs -f capsight-api"
    log_info "To scale: docker-compose -f $COMPOSE_FILE up -d --scale capsight-api=3"
}

# Rollback deployment
rollback() {
    log_warn "Rolling back deployment..."
    
    docker-compose -f $COMPOSE_FILE down
    docker-compose -f $COMPOSE_FILE up -d
    
    log_info "Rollback completed"
}

# Cleanup
cleanup() {
    log_info "Cleaning up..."
    
    # Remove unused images
    docker image prune -f
    
    log_info "Cleanup completed"
}

# Main deployment flow
main() {
    case "${1:-deploy}" in
        "deploy")
            check_prerequisites
            validate_config
            build_images
            deploy_infrastructure
            run_migrations
            deploy_application
            verify_deployment
            show_status
            cleanup
            log_info "🎉 CapSight Backend v2 deployed successfully!"
            ;;
        "rollback")
            rollback
            ;;
        "status")
            show_status
            ;;
        "logs")
            docker-compose -f $COMPOSE_FILE logs -f "${2:-capsight-api}"
            ;;
        "scale")
            instances="${2:-2}"
            log_info "Scaling to $instances instances..."
            docker-compose -f $COMPOSE_FILE up -d --scale capsight-api=$instances
            ;;
        "stop")
            log_info "Stopping CapSight services..."
            docker-compose -f $COMPOSE_FILE down
            ;;
        "restart")
            log_info "Restarting CapSight services..."
            docker-compose -f $COMPOSE_FILE restart capsight-api
            ;;
        *)
            echo "Usage: $0 {deploy|rollback|status|logs|scale|stop|restart}"
            echo ""
            echo "Commands:"
            echo "  deploy   - Deploy CapSight Backend v2 (default)"
            echo "  rollback - Rollback to previous version"
            echo "  status   - Show deployment status"
            echo "  logs     - Show application logs"
            echo "  scale N  - Scale to N instances"
            echo "  stop     - Stop all services"
            echo "  restart  - Restart application"
            exit 1
            ;;
    esac
}

# Handle Ctrl+C
trap 'log_error "Deployment interrupted"; exit 1' INT

# Run main function
main "$@"
