#!/usr/bin/env python3
"""
CapSight API Validation Script

This script validates that the CapSight backend is properly configured
and all endpoints are working correctly.

Usage:
    python validate_api.py [--host http://localhost:8000]
"""

import asyncio
import argparse
import json
from typing import Dict, List, Any
import httpx
import sys


class APIValidator:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
        self.token = None
        
    async def validate_health(self) -> Dict[str, Any]:
        """Validate health endpoint."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return {
                "endpoint": "/health",
                "status": "✅ PASS" if response.status_code == 200 else "❌ FAIL",
                "response_time": f"{response.elapsed.total_seconds():.2f}s",
                "data": response.json() if response.status_code == 200 else None
            }
        except Exception as e:
            return {
                "endpoint": "/health",
                "status": "❌ FAIL",
                "error": str(e)
            }
    
    async def validate_openapi(self) -> Dict[str, Any]:
        """Validate OpenAPI schema."""
        try:
            response = await self.client.get(f"{self.base_url}/openapi.json")
            if response.status_code == 200:
                schema = response.json()
                paths = list(schema.get("paths", {}).keys())
                return {
                    "endpoint": "/openapi.json",
                    "status": "✅ PASS",
                    "response_time": f"{response.elapsed.total_seconds():.2f}s",
                    "api_paths_count": len(paths),
                    "sample_paths": paths[:10]
                }
            else:
                return {
                    "endpoint": "/openapi.json",
                    "status": "❌ FAIL",
                    "status_code": response.status_code
                }
        except Exception as e:
            return {
                "endpoint": "/openapi.json",
                "status": "❌ FAIL",
                "error": str(e)
            }
    
    async def validate_auth(self) -> Dict[str, Any]:
        """Validate authentication endpoints."""
        import time
        test_email = f"test_{int(time.time())}@example.com"
        
        try:
            # Register
            register_data = {
                "email": test_email,
                "password": "TestPassword123!",
                "full_name": "Test User"
            }
            
            reg_response = await self.client.post(
                f"{self.base_url}/api/v1/auth/register",
                json=register_data
            )
            
            if reg_response.status_code != 201:
                return {
                    "endpoint": "/api/v1/auth/register",
                    "status": "❌ FAIL",
                    "status_code": reg_response.status_code,
                    "response": reg_response.text
                }
            
            # Login
            login_data = {
                "username": test_email,
                "password": "TestPassword123!"
            }
            
            login_response = await self.client.post(
                f"{self.base_url}/api/v1/auth/login",
                data=login_data
            )
            
            if login_response.status_code == 200:
                token_data = login_response.json()
                self.token = token_data.get("access_token")
                return {
                    "endpoint": "/api/v1/auth/*",
                    "status": "✅ PASS",
                    "response_time": f"{login_response.elapsed.total_seconds():.2f}s",
                    "token_received": bool(self.token)
                }
            else:
                return {
                    "endpoint": "/api/v1/auth/login",
                    "status": "❌ FAIL",
                    "status_code": login_response.status_code,
                    "response": login_response.text
                }
                
        except Exception as e:
            return {
                "endpoint": "/api/v1/auth/*",
                "status": "❌ FAIL",
                "error": str(e)
            }
    
    async def validate_protected_endpoints(self) -> List[Dict[str, Any]]:
        """Validate protected endpoints that require authentication."""
        if not self.token:
            return [{
                "endpoint": "protected_endpoints",
                "status": "❌ SKIP",
                "reason": "No authentication token available"
            }]
        
        headers = {"Authorization": f"Bearer {self.token}"}
        endpoints_to_test = [
            ("/api/v1/users/me", "GET"),
            ("/api/v1/opportunities/", "GET"),
            ("/api/v1/predictions/", "GET"),
            ("/api/v1/subscriptions/tiers", "GET")
        ]
        
        results = []
        
        for endpoint, method in endpoints_to_test:
            try:
                if method == "GET":
                    response = await self.client.get(f"{self.base_url}{endpoint}", headers=headers)
                else:
                    response = await self.client.request(method, f"{self.base_url}{endpoint}", headers=headers)
                
                results.append({
                    "endpoint": endpoint,
                    "method": method,
                    "status": "✅ PASS" if response.status_code in [200, 404] else "❌ FAIL",
                    "status_code": response.status_code,
                    "response_time": f"{response.elapsed.total_seconds():.2f}s"
                })
                
            except Exception as e:
                results.append({
                    "endpoint": endpoint,
                    "method": method,
                    "status": "❌ FAIL",
                    "error": str(e)
                })
        
        return results
    
    async def list_all_api_routes(self) -> Dict[str, Any]:
        """Get all available API routes from OpenAPI spec."""
        try:
            response = await self.client.get(f"{self.base_url}/openapi.json")
            if response.status_code == 200:
                schema = response.json()
                paths = schema.get("paths", {})
                
                routes = []
                for path, methods in paths.items():
                    for method, details in methods.items():
                        if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                            routes.append({
                                "method": method.upper(),
                                "path": path,
                                "summary": details.get("summary", ""),
                                "tags": details.get("tags", [])
                            })
                
                return {
                    "total_routes": len(routes),
                    "routes": sorted(routes, key=lambda x: (x["path"], x["method"]))
                }
            else:
                return {"error": "Could not fetch OpenAPI schema"}
        except Exception as e:
            return {"error": str(e)}
    
    async def run_validation(self) -> Dict[str, Any]:
        """Run all validations."""
        print("🚀 CapSight API Validation Starting...")
        print(f"🔍 Testing: {self.base_url}")
        print("=" * 60)
        
        results = {
            "base_url": self.base_url,
            "timestamp": asyncio.get_event_loop().time(),
            "tests": {}
        }
        
        # Test 1: Health Check
        print("1. 🏥 Health Check...")
        results["tests"]["health"] = await self.validate_health()
        print(f"   {results['tests']['health']['status']} {results['tests']['health']['endpoint']}")
        
        # Test 2: OpenAPI Schema
        print("2. 📋 OpenAPI Schema...")
        results["tests"]["openapi"] = await self.validate_openapi()
        print(f"   {results['tests']['openapi']['status']} {results['tests']['openapi']['endpoint']}")
        
        # Test 3: Authentication
        print("3. 🔐 Authentication...")
        results["tests"]["auth"] = await self.validate_auth()
        print(f"   {results['tests']['auth']['status']} {results['tests']['auth']['endpoint']}")
        
        # Test 4: Protected Endpoints
        print("4. 🛡️  Protected Endpoints...")
        results["tests"]["protected"] = await self.validate_protected_endpoints()
        for test in results["tests"]["protected"]:
            print(f"   {test['status']} {test['method']} {test['endpoint']}")
        
        # Test 5: List all routes
        print("5. 🗺️  API Routes Discovery...")
        routes_info = await self.list_all_api_routes()
        results["api_routes"] = routes_info
        
        if "routes" in routes_info:
            print(f"   ✅ Found {routes_info['total_routes']} API endpoints")
            
            # Group by tags
            by_tags = {}
            for route in routes_info["routes"]:
                for tag in route.get("tags", ["Untagged"]):
                    if tag not in by_tags:
                        by_tags[tag] = []
                    by_tags[tag].append(f"{route['method']} {route['path']}")
            
            print("\n📍 Available API Endpoints by Category:")
            for tag, endpoints in by_tags.items():
                print(f"\n   🏷️  {tag}:")
                for endpoint in endpoints[:5]:  # Show first 5
                    print(f"      • {endpoint}")
                if len(endpoints) > 5:
                    print(f"      ... and {len(endpoints) - 5} more")
        
        print("\n" + "=" * 60)
        
        # Summary
        passed_tests = 0
        total_tests = 0
        
        for test_name, test_result in results["tests"].items():
            if isinstance(test_result, list):
                for sub_test in test_result:
                    total_tests += 1
                    if "✅" in sub_test.get("status", ""):
                        passed_tests += 1
            else:
                total_tests += 1
                if "✅" in test_result.get("status", ""):
                    passed_tests += 1
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"🎯 Validation Results: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
        
        if success_rate >= 80:
            print("🎉 CapSight API is healthy and ready!")
        elif success_rate >= 60:
            print("⚠️  CapSight API has some issues but is partially functional")
        else:
            print("❌ CapSight API has significant issues - please check configuration")
        
        await self.client.aclose()
        return results


async def main():
    parser = argparse.ArgumentParser(description="Validate CapSight API")
    parser.add_argument(
        "--host", 
        default="http://localhost:8000",
        help="Base URL of the CapSight API"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    
    args = parser.parse_args()
    
    validator = APIValidator(args.host)
    results = await validator.run_validation()
    
    if args.json:
        print(json.dumps(results, indent=2))
    
    # Exit with error code if validation failed
    failed_tests = any(
        "❌" in str(test_result) 
        for test_result in results["tests"].values()
    )
    
    if failed_tests:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
