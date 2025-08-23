# CapSight Production Deployment Guide

## Prerequisites Setup

Since Docker is not currently installed, you'll need to set up your environment first:

### 1. Install Docker Desktop (Required)
```powershell
# Download and install Docker Desktop from:
# https://www.docker.com/products/docker-desktop

# After installation, verify:
docker --version
docker compose version
```

### 2. Install Python Dependencies (for validation scripts)
```powershell
# Install required packages for validation
pip install requests httpx python-dotenv
```

## Deployment Process

### Step 1: Configuration Validation
```powershell
# Navigate to backend_v2 directory
cd "c:\Users\mccab\New folder (2)\backend_v2"

# Validate configuration
python validate_config.py
```

### Step 2: Deploy Services
```powershell
# Option A: Using PowerShell script (recommended for Windows)
.\deploy\deploy.ps1 deploy

# Option B: Using Docker Compose directly
docker compose -f config/docker-compose.yml up -d --build
```

### Step 3: Verify Deployment
```powershell
# Check service status
.\deploy\deploy.ps1 status

# Or check manually
docker compose -f config/docker-compose.yml ps

# Test API endpoints
python ..\validate_deployment.py
```

### Step 4: Access Services
- **API Documentation**: http://localhost:8000/docs
- **Grafana Dashboards**: http://localhost:3000 (admin/admin)
- **Prometheus Metrics**: http://localhost:9090
- **API Health Check**: http://localhost:8000/health

## Demo Mode Setup

### Enable Demo Mode
```powershell
# Switch to demo configuration
copy .env.demo .env

# Restart services with demo data
docker compose -f config/docker-compose.yml restart
```

### Demo Validation
```powershell
# Run comprehensive API validation
python ..\validate_api.py

# Test specific demo endpoints
curl http://localhost:8000/api/v1/demo/properties
curl http://localhost:8000/api/v1/demo/predictions
```

## Monitoring & Alerts

### Grafana Setup
1. Open http://localhost:3000
2. Login: admin/admin
3. Import pre-configured dashboards from `/deploy/grafana/dashboards/`

### Prometheus Targets
- API metrics: http://localhost:8000/metrics
- System metrics: Various exporters
- Custom business metrics: Real-time accuracy, freshness

### Alert Testing
```powershell
# Generate test alerts
python test_alerts.py

# Check PagerDuty integration (if configured)
python test_pagerduty.py
```

## Sales Demo Script

### 1. Real-time Property Analysis
```bash
# Show live property valuation with confidence intervals
POST /api/v1/analyze
{
  "address": "123 Main St, Seattle, WA",
  "property_type": "single_family",
  "bedrooms": 3,
  "bathrooms": 2,
  "square_feet": 1800
}
```

### 2. Speed Demonstration
- Target: <100ms response time
- Show Grafana dashboard with real-time latency
- Demonstrate burst capacity

### 3. Accuracy Tracking
- Show model performance metrics
- Display confidence intervals
- Demonstrate drift detection

### 4. Data Freshness
- Show last update timestamps
- Demonstrate streaming data ingestion
- Display freshness SLA compliance

## Troubleshooting

### Common Issues
1. **Port conflicts**: Ensure ports 8000, 3000, 9090, 5432, 6379 are available
2. **Memory issues**: Ensure at least 8GB RAM available for Docker
3. **API key errors**: Verify all placeholders in .env are replaced

### Logs Access
```powershell
# All services
docker compose -f config/docker-compose.yml logs

# Specific service
docker compose -f config/docker-compose.yml logs api

# Follow logs in real-time
docker compose -f config/docker-compose.yml logs -f
```

### Reset Deployment
```powershell
# Stop all services
.\deploy\deploy.ps1 stop

# Clean up containers and volumes
docker compose -f config/docker-compose.yml down -v

# Remove all images (if needed)
docker system prune -a
```

## Production Checklist

- [ ] Docker Desktop installed and running
- [ ] All API keys replaced in .env
- [ ] Configuration validation passed
- [ ] All containers started successfully
- [ ] Health endpoints responding
- [ ] Grafana dashboards accessible
- [ ] Prometheus collecting metrics
- [ ] Demo mode tested and working
- [ ] API response times < 100ms
- [ ] Alert mechanisms verified

## Next Steps

1. **Production Deployment**: Use Terraform scripts for AWS/Azure
2. **Domain Setup**: Configure custom domain and SSL certificates
3. **Scaling**: Set up horizontal pod autoscaling
4. **Monitoring**: Configure production alerting thresholds
5. **Backup**: Set up automated database backups

For production deployment to AWS/Azure, see the Terraform configurations in `/deploy/terraform/`.
