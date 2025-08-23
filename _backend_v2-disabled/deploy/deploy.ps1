# CapSight Deployment Script for Windows
# Usage: .\deploy.ps1 [deploy|stop|status|logs]

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("deploy", "stop", "status", "logs")]
    [string]$Action
)

$ErrorActionPreference = "Stop"

function Write-Header {
    param([string]$Message)
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "  $Message" -ForegroundColor Yellow
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
}

function Test-DockerInstalled {
    try {
        $dockerVersion = docker --version
        Write-Host "✓ Docker found: $dockerVersion" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "✗ Docker is not installed or not in PATH" -ForegroundColor Red
        Write-Host "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
        return $false
    }
}

function Test-EnvFile {
    if (Test-Path ".env") {
        Write-Host "✓ Environment file (.env) found" -ForegroundColor Green
        
        # Check for placeholder values
        $envContent = Get-Content ".env" -Raw
        $placeholders = @("your_", "placeholder_", "change_me", "secret_key_here", "your-key-here")
        $found = $false
        
        foreach ($placeholder in $placeholders) {
            if ($envContent -match $placeholder) {
                Write-Host "⚠  Found placeholder '$placeholder' in .env file" -ForegroundColor Yellow
                $found = $true
            }
        }
        
        if (-not $found) {
            Write-Host "✓ No obvious placeholders found in .env" -ForegroundColor Green
        }
        return $true
    }
    else {
        Write-Host "✗ Environment file (.env) not found" -ForegroundColor Red
        Write-Host "Please copy .env.example to .env and configure your secrets" -ForegroundColor Yellow
        return $false
    }
}

function Deploy-Services {
    Write-Header "🚀 DEPLOYING CAPSIGHT SERVICES"
    
    if (-not (Test-DockerInstalled)) { return $false }
    if (-not (Test-EnvFile)) { return $false }
    
    try {
        Write-Host "📦 Building and starting services..." -ForegroundColor Blue
        docker compose -f config/docker-compose.yml up -d --build
        
        Write-Host "⏳ Waiting 30 seconds for services to initialize..." -ForegroundColor Blue
        Start-Sleep -Seconds 30
        
        Write-Host "🔍 Checking service status..." -ForegroundColor Blue
        docker compose -f config/docker-compose.yml ps
        
        Write-Host "`n✅ Deployment completed!" -ForegroundColor Green
        Write-Host "API will be available at: http://localhost:8000" -ForegroundColor Cyan
        Write-Host "Grafana dashboard: http://localhost:3000 (admin/admin)" -ForegroundColor Cyan
        Write-Host "Prometheus: http://localhost:9090" -ForegroundColor Cyan
        
        return $true
    }
    catch {
        Write-Host "✗ Deployment failed: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Stop-Services {
    Write-Header "🛑 STOPPING CAPSIGHT SERVICES"
    
    try {
        docker compose -f config/docker-compose.yml down
        Write-Host "✅ Services stopped successfully" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "✗ Failed to stop services: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Get-ServiceStatus {
    Write-Header "📊 SERVICE STATUS"
    
    try {
        docker compose -f config/docker-compose.yml ps
        
        Write-Host "`n🔍 Testing API endpoints..." -ForegroundColor Blue
        
        $endpoints = @(
            @{url="http://localhost:8000/health"; name="Health Check"},
            @{url="http://localhost:8000/ready"; name="Readiness Check"},
            @{url="http://localhost:8000/openapi.json"; name="OpenAPI Schema"}
        )
        
        foreach ($endpoint in $endpoints) {
            try {
                $response = Invoke-RestMethod -Uri $endpoint.url -TimeoutSec 5 -ErrorAction Stop
                Write-Host "✓ $($endpoint.name): OK" -ForegroundColor Green
            }
            catch {
                Write-Host "✗ $($endpoint.name): Failed - $($_.Exception.Message)" -ForegroundColor Red
            }
        }
        
        return $true
    }
    catch {
        Write-Host "✗ Status check failed: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Get-ServiceLogs {
    Write-Header "📋 SERVICE LOGS"
    
    try {
        Write-Host "Recent logs from all services:" -ForegroundColor Blue
        docker compose -f config/docker-compose.yml logs --tail=50
        return $true
    }
    catch {
        Write-Host "✗ Failed to get logs: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Main execution
switch ($Action) {
    "deploy" { 
        $success = Deploy-Services
        if ($success) {
            Write-Host "`n🎉 Next steps:" -ForegroundColor Magenta
            Write-Host "1. Run: .\deploy.ps1 status  # Check all services are healthy" -ForegroundColor White
            Write-Host "2. Open: http://localhost:8000/docs  # API documentation" -ForegroundColor White
            Write-Host "3. Open: http://localhost:3000  # Grafana dashboards" -ForegroundColor White
            Write-Host "4. Test: python ..\validate_api.py  # API validation" -ForegroundColor White
        }
    }
    "stop" { Stop-Services }
    "status" { Get-ServiceStatus }
    "logs" { Get-ServiceLogs }
}
