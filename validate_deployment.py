"""
CapSight Deployment Validation Script
Quick validation of deployed services
"""
import requests
import time
import json
from datetime import datetime
import sys

def test_endpoint(url, name, timeout=10):
    """Test a single endpoint"""
    try:
        start_time = time.time()
        response = requests.get(url, timeout=timeout)
        response_time = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            print(f"✓ {name}: OK ({response_time:.0f}ms)")
            return True, response_time
        else:
            print(f"✗ {name}: HTTP {response.status_code}")
            return False, response_time
            
    except requests.exceptions.ConnectTimeout:
        print(f"✗ {name}: Connection timeout")
        return False, None
    except requests.exceptions.ConnectionError:
        print(f"✗ {name}: Connection refused (service not running?)")
        return False, None
    except Exception as e:
        print(f"✗ {name}: {str(e)}")
        return False, None

def validate_deployment(base_url="http://localhost:8000"):
    """Validate CapSight deployment"""
    print("🚀 CAPSIGHT DEPLOYMENT VALIDATION")
    print("=" * 50)
    print(f"Testing: {base_url}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Core API endpoints
    print("🏥 Core API Endpoints:")
    endpoints = [
        ("/health", "Health Check"),
        ("/ready", "Readiness Check"),
        ("/docs", "API Documentation"),
        ("/openapi.json", "OpenAPI Schema"),
        ("/metrics", "Prometheus Metrics")
    ]
    
    api_results = []
    for path, name in endpoints:
        success, response_time = test_endpoint(f"{base_url}{path}", name)
        api_results.append(success)
    
    print()
    
    # Supporting services
    print("📊 Supporting Services:")
    services = [
        ("http://localhost:3000", "Grafana Dashboard"),
        ("http://localhost:9090", "Prometheus"),
        ("http://localhost:5432", "PostgreSQL", 2),  # Quick timeout for DB
        ("http://localhost:6379", "Redis", 2)        # Quick timeout for Redis
    ]
    
    service_results = []
    for service_info in services:
        if len(service_info) == 3:
            url, name, timeout = service_info
        else:
            url, name = service_info
            timeout = 10
            
        success, _ = test_endpoint(url, name, timeout)
        service_results.append(success)
    
    print()
    
    # Summary
    api_passed = sum(api_results)
    services_passed = sum(service_results)
    total_api = len(api_results)
    total_services = len(service_results)
    
    print("📋 VALIDATION SUMMARY")
    print("=" * 50)
    print(f"API Endpoints: {api_passed}/{total_api} passed")
    print(f"Services: {services_passed}/{total_services} passed")
    
    if api_passed == total_api and services_passed >= 2:  # At least Grafana + Prometheus
        print("✅ Deployment validation PASSED")
        return True
    else:
        print("❌ Deployment validation FAILED")
        print("\n💡 Troubleshooting:")
        if api_passed < total_api:
            print("  • Check if API container is running: docker ps")
            print("  • Check API logs: docker logs capsight-api")
        if services_passed < 2:
            print("  • Check if all containers started: docker compose ps")
            print("  • Check logs: docker compose logs")
        return False

if __name__ == "__main__":
    base_url = "http://localhost:8000"
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    success = validate_deployment(base_url)
    sys.exit(0 if success else 1)
