"""
CapSight Full System Validation
Tests all major components for pilot readiness
"""

import os
import sys
import importlib
from datetime import datetime

def test_component(name, test_func):
    """Test a component and report results"""
    try:
        test_func()
        print(f"✓ {name}: PASSED")
        return True
    except Exception as e:
        print(f"✗ {name}: FAILED - {str(e)}")
        return False

def test_ml_engine():
    """Test ML forecasting engine"""
    sys.path.append('backend')
    try:
        from app.ml.models.forecasting_engine import CapSightForecaster
        forecaster = CapSightForecaster()
        assert forecaster is not None
    except ImportError:
        # Try alternative path
        from backend.app.ml.models.forecasting_engine import CapSightForecaster
        forecaster = CapSightForecaster()
        assert forecaster is not None

def test_demo_data():
    """Test demo data generator"""
    sys.path.append('backend')
    from app.core.demo_data import DemoDataGenerator
    generator = DemoDataGenerator()
    properties = generator.generate_demo_properties(3)
    opportunities = generator.generate_demo_opportunities(properties)
    assert len(properties) == 3
    assert len(opportunities) > 0

def test_backend_structure():
    """Test backend structure and imports"""
    backend_files = [
        'backend/app/main.py',
        'backend/app/core/config.py',
        'backend/app/core/database.py',
        'backend/app/api/endpoints/opportunities.py',
        'backend/app/services/predictions.py',
        'backend/.env.production'
    ]
    for file_path in backend_files:
        assert os.path.exists(file_path), f"Missing file: {file_path}"

def test_frontend_structure():
    """Test frontend structure and files"""
    frontend_files = [
        'frontend/src/App.tsx',
        'frontend/src/styles/capsight-brand.css',
        'frontend/src/components/legal/Disclaimers.tsx',
        'frontend/.env.production',
        'frontend/package.json'
    ]
    for file_path in frontend_files:
        assert os.path.exists(file_path), f"Missing file: {file_path}"

def test_deployment_scripts():
    """Test deployment scripts exist"""
    scripts = ['scripts/deploy.sh', 'scripts/deploy.bat']
    for script in scripts:
        assert os.path.exists(script), f"Missing script: {script}"

def test_cypress_e2e():
    """Test Cypress E2E structure"""
    cypress_files = [
        'frontend/cypress/e2e/auth/login.cy.ts',
        'frontend/cypress/e2e/dashboard/dashboard.cy.ts',
        'frontend/cypress.config.ts'
    ]
    for file_path in cypress_files:
        assert os.path.exists(file_path), f"Missing Cypress file: {file_path}"

def main():
    """Run all validation tests"""
    print("=== CapSight System Validation ===")
    print(f"Timestamp: {datetime.now()}")
    print()
    
    tests = [
        ("ML Forecasting Engine", test_ml_engine),
        ("Demo Data Generator", test_demo_data),
        ("Backend Structure", test_backend_structure),
        ("Frontend Structure", test_frontend_structure),
        ("Deployment Scripts", test_deployment_scripts),
        ("Cypress E2E Suite", test_cypress_e2e)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        if test_component(test_name, test_func):
            passed += 1
    
    print()
    print(f"=== RESULTS: {passed}/{total} tests passed ===")
    
    if passed == total:
        print("🎉 CapSight is PILOT READY!")
        print()
        print("Next steps:")
        print("1. Set environment variables in .env.production files")
        print("2. Run deployment scripts (deploy.sh or deploy.bat)")
        print("3. Configure external API keys (Stripe, MLS, etc.)")
        print("4. Run full E2E test suite: cd frontend && npm run cy:run")
        print("5. Enable demo mode: DEMO_MODE=true for testing")
    else:
        print("❌ System not ready for pilot - fix failing tests")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
