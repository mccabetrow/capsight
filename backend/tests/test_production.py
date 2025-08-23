"""
Production readiness tests for CapSight backend.

Run this after deployment to verify all systems are working.
"""
import asyncio
import httpx
import json
from typing import Dict, Any
import os


class CapSightProductionTest:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient()
        self.auth_token = None
        
    async def test_health_check(self) -> bool:
        """Test the health check endpoint."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200 and response.json().get("status") == "healthy"
        except Exception as e:
            print(f"Health check failed: {e}")
            return False
    
    async def test_openapi_docs(self) -> bool:
        """Test OpenAPI documentation is available."""
        try:
            response = await self.client.get(f"{self.base_url}/openapi.json")
            return response.status_code == 200 and "openapi" in response.json()
        except Exception as e:
            print(f"OpenAPI docs test failed: {e}")
            return False
    
    async def test_user_registration(self) -> bool:
        """Test user registration endpoint."""
        try:
            test_user = {
                "email": f"test_{asyncio.get_event_loop().time()}@example.com",
                "password": "TestPassword123!",
                "full_name": "Test User"
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/auth/register",
                json=test_user
            )
            
            if response.status_code == 201:
                # Test login with the same user
                login_response = await self.client.post(
                    f"{self.base_url}/api/v1/auth/login",
                    data={
                        "username": test_user["email"],
                        "password": test_user["password"]
                    }
                )
                
                if login_response.status_code == 200:
                    token_data = login_response.json()
                    self.auth_token = token_data.get("access_token")
                    return True
                    
            return False
        except Exception as e:
            print(f"User registration test failed: {e}")
            return False
    
    async def test_opportunities_endpoint(self) -> bool:
        """Test opportunities endpoint with authentication."""
        if not self.auth_token:
            print("No auth token available for opportunities test")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = await self.client.get(
                f"{self.base_url}/api/v1/opportunities/",
                headers=headers
            )
            
            # Should return 200 with empty list for new user
            return response.status_code == 200
        except Exception as e:
            print(f"Opportunities endpoint test failed: {e}")
            return False
    
    async def test_database_connection(self) -> bool:
        """Test database connection via a simple query."""
        try:
            # Use the users endpoint which requires DB access
            if not self.auth_token:
                return False
                
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = await self.client.get(
                f"{self.base_url}/api/v1/users/me",
                headers=headers
            )
            
            return response.status_code == 200
        except Exception as e:
            print(f"Database connection test failed: {e}")
            return False
    
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all production tests and return results."""
        results = {}
        
        print("🚀 Running CapSight Production Tests...")
        print(f"Base URL: {self.base_url}")
        print("-" * 50)
        
        # Test 1: Health Check
        print("1. Testing health check endpoint...")
        results["health_check"] = await self.test_health_check()
        print(f"   ✅ Health check: {'PASSED' if results['health_check'] else '❌ FAILED'}")
        
        # Test 2: OpenAPI Documentation
        print("2. Testing OpenAPI documentation...")
        results["openapi_docs"] = await self.test_openapi_docs()
        print(f"   ✅ OpenAPI docs: {'PASSED' if results['openapi_docs'] else '❌ FAILED'}")
        
        # Test 3: User Registration & Login
        print("3. Testing user registration and login...")
        results["user_auth"] = await self.test_user_registration()
        print(f"   ✅ User auth: {'PASSED' if results['user_auth'] else '❌ FAILED'}")
        
        # Test 4: Database Connection
        print("4. Testing database connection...")
        results["database"] = await self.test_database_connection()
        print(f"   ✅ Database: {'PASSED' if results['database'] else '❌ FAILED'}")
        
        # Test 5: Opportunities Endpoint
        print("5. Testing opportunities endpoint...")
        results["opportunities"] = await self.test_opportunities_endpoint()
        print(f"   ✅ Opportunities: {'PASSED' if results['opportunities'] else '❌ FAILED'}")
        
        print("-" * 50)
        passed_tests = sum(results.values())
        total_tests = len(results)
        print(f"🎯 Results: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 All tests passed! CapSight is ready for production.")
        else:
            print("⚠️  Some tests failed. Please check the configuration.")
        
        await self.client.aclose()
        return results


async def main():
    """Main test runner."""
    # Get base URL from environment or use default
    base_url = os.getenv("CAPSIGHT_API_URL", "http://localhost:8000")
    
    tester = CapSightProductionTest(base_url)
    results = await tester.run_all_tests()
    
    # Return non-zero exit code if any tests failed
    if not all(results.values()):
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
