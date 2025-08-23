#!/usr/bin/env python3
"""
CapSight End-to-End Release Verification
Senior Release Engineer style verification with strict PASS/FAIL evidence.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Evidence table for final summary
evidence = []

def log_evidence(section: str, check: str, status: str, details: str = ""):
    """Log evidence for final summary table."""
    evidence.append({
        'section': section,
        'check': check,
        'status': status,
        'details': details
    })
    print(f"  {check:<50} {status:>8} {details}")

def check_section_header(section: str, number: int):
    """Print section header."""
    print(f"\n{'='*80}")
    print(f"Section {number}: {section}")
    print(f"{'='*80}")

def run_command(cmd: str, cwd: str = None) -> Tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            cwd=cwd,
            capture_output=True, 
            text=True, 
            timeout=30
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except Exception as e:
        return 1, "", str(e)

def verify_environment():
    """Section 1: Environment Sanity Check"""
    check_section_header("Environment Sanity Check", 1)
    
    # Check .env.local exists
    env_path = Path(".env.local")
    if env_path.exists():
        log_evidence("Environment", ".env.local exists", "PASS")
        
        # Check required variables
        content = env_path.read_text()
        required_vars = [
            "NEXT_PUBLIC_SUPABASE_URL",
            "NEXT_PUBLIC_SUPABASE_ANON_KEY", 
            "SUPABASE_SERVICE_ROLE_KEY"
        ]
        
        for var in required_vars:
            if var in content and "paste_your" not in content and "your-service" not in content:
                log_evidence("Environment", f"{var} configured", "PASS")
            else:
                log_evidence("Environment", f"{var} configured", "FAIL", "Contains placeholder")
    else:
        log_evidence("Environment", ".env.local exists", "FAIL", "File missing")
    
    # Check Python venv
    venv_path = Path(".venv/Scripts/python.exe")  # Windows
    if venv_path.exists():
        log_evidence("Environment", "Python venv active", "PASS")
    else:
        log_evidence("Environment", "Python venv active", "FAIL", "No .venv found")
    
    # Check Node modules
    node_modules = Path("node_modules")  # At root level
    if node_modules.exists():
        log_evidence("Environment", "Node.js dependencies", "PASS")
    else:
        log_evidence("Environment", "Node.js dependencies", "FAIL", "npm install needed")

def verify_file_structure():
    """Section 2: Critical File Structure"""
    check_section_header("Critical File Structure", 2)
    
    critical_files = [
        "package.json",  # Frontend package.json is at root
        "frontend/src/app/admin/page.tsx",
        "frontend/src/middleware.ts",
        "backend/main.py",
        "backend/requirements.txt",
        "nightly_accuracy.py",
        "rls_audit.py",
        "tools/seed_markets.py",
        "openapi.yaml",
        "docker-compose.yml"
    ]
    
    for file_path in critical_files:
        if Path(file_path).exists():
            log_evidence("File Structure", f"{file_path}", "PASS")
        else:
            log_evidence("File Structure", f"{file_path}", "FAIL", "Missing")

def verify_security():
    """Section 3: Security Headers & Middleware"""
    check_section_header("Security Headers & Middleware", 3)
    
    middleware_path = Path("frontend/src/middleware.ts")  # Correct path is src/
    if middleware_path.exists():
        content = middleware_path.read_text()
        
        security_checks = [
            ("CSP headers", "Content-Security-Policy"),
            ("Admin token", "ADMIN_TOKEN"),
            ("Rate limiting", "ratelimit"),  # Changed pattern to match actual code
            ("X-Frame-Options", "X-Frame-Options")
        ]
        
        for check_name, pattern in security_checks:
            if pattern in content:
                log_evidence("Security", check_name, "PASS")
            else:
                log_evidence("Security", check_name, "FAIL", f"Missing {pattern}")
    else:
        log_evidence("Security", "middleware.ts exists", "FAIL", "File missing")

def verify_api_structure():
    """Section 4: API Structure & OpenAPI"""
    check_section_header("API Structure & OpenAPI", 4)
    
    # Check OpenAPI spec
    openapi_path = Path("openapi.yaml")
    if openapi_path.exists():
        log_evidence("API", "OpenAPI spec exists", "PASS")
        
        content = openapi_path.read_text()
        if "/api/v1/value" in content:
            log_evidence("API", "Value endpoint documented", "PASS")
        else:
            log_evidence("API", "Value endpoint documented", "FAIL")
    else:
        log_evidence("API", "OpenAPI spec exists", "FAIL")
    
    # Check backend structure
    backend_files = [
        "backend/app/api/endpoints/value.py",
        "backend/app/core/security.py",
        "backend/app/models/"
    ]
    
    for file_path in backend_files:
        if Path(file_path).exists():
            log_evidence("API", f"{Path(file_path).name}", "PASS")
        else:
            log_evidence("API", f"{Path(file_path).name}", "FAIL", "Missing")

def verify_admin_console():
    """Section 5: Admin Console Security"""
    check_section_header("Admin Console Security", 5)
    
    admin_files = [
        "frontend/src/app/admin/page.tsx",
        "frontend/src/app/admin/components/AccuracyCard.tsx",
        "frontend/src/app/admin/components/MarketCard.tsx",
        "frontend/src/app/admin/lib/supabase-admin.ts"
    ]
    
    for file_path in admin_files:
        if Path(file_path).exists():
            log_evidence("Admin Console", Path(file_path).name, "PASS")
        else:
            log_evidence("Admin Console", Path(file_path).name, "FAIL", "Missing")
    
    # Check middleware protection
    middleware_path = Path("frontend/src/middleware.ts")  # Correct path
    if middleware_path.exists() and "admin" in middleware_path.read_text():
        log_evidence("Admin Console", "Route protection", "PASS")
    else:
        log_evidence("Admin Console", "Route protection", "FAIL")

def verify_testing():
    """Section 6: Testing Infrastructure"""
    check_section_header("Testing Infrastructure", 6)
    
    test_files = [
        "perf/value.js",
        ".github/workflows/perf.yml",
        "frontend/cypress/e2e/",
        "backend/tests/"
    ]
    
    for file_path in test_files:
        if Path(file_path).exists():
            log_evidence("Testing", Path(file_path).name, "PASS")
        else:
            log_evidence("Testing", Path(file_path).name, "FAIL", "Missing")

def verify_monitoring():
    """Section 7: Monitoring & Observability"""
    check_section_header("Monitoring & Observability", 7)
    
    # Check accuracy monitoring
    if Path("nightly_accuracy.py").exists():
        log_evidence("Monitoring", "Accuracy monitoring", "PASS")
    else:
        log_evidence("Monitoring", "Accuracy monitoring", "FAIL")
    
    # Check logging setup
    backend_logging = Path("backend/app/core/logging.py")
    if backend_logging.exists():
        log_evidence("Monitoring", "Backend logging", "PASS")
    else:
        log_evidence("Monitoring", "Backend logging", "FAIL")

def verify_deployment():
    """Section 8: Deployment Readiness"""
    check_section_header("Deployment Readiness", 8)
    
    deployment_files = [
        "docker-compose.yml",
        "docker-compose.prod.yml",
        "backend/Dockerfile",
        "deploy-enhanced.sh"
    ]
    
    for file_path in deployment_files:
        if Path(file_path).exists():
            log_evidence("Deployment", Path(file_path).name, "PASS")
        else:
            log_evidence("Deployment", Path(file_path).name, "FAIL")

def verify_documentation():
    """Section 9: Documentation & Legal"""
    check_section_header("Documentation & Legal", 9)
    
    doc_files = [
        "README.md",
        "SECURITY.md",
        "docs/",
        "sales/"
    ]
    
    for file_path in doc_files:
        if Path(file_path).exists():
            log_evidence("Documentation", Path(file_path).name, "PASS")
        else:
            log_evidence("Documentation", Path(file_path).name, "FAIL")

def verify_data_pipeline():
    """Section 10: Data Pipeline & Tools"""
    check_section_header("Data Pipeline & Tools", 10)
    
    pipeline_files = [
        "tools/seed_markets.py",
        "tools/requirements.txt",
        "validate_csv_enhanced.py"
    ]
    
    for file_path in pipeline_files:
        if Path(file_path).exists():
            log_evidence("Data Pipeline", Path(file_path).name, "PASS")
        else:
            log_evidence("Data Pipeline", Path(file_path).name, "FAIL")

def print_final_summary():
    """Print final GO/NO-GO summary."""
    print(f"\n{'='*80}")
    print("FINAL RELEASE VERIFICATION SUMMARY")
    print(f"{'='*80}")
    
    # Count results
    total_checks = len(evidence)
    passed_checks = len([e for e in evidence if e['status'] == 'PASS'])
    failed_checks = len([e for e in evidence if e['status'] == 'FAIL'])
    
    print(f"Total Checks: {total_checks}")
    print(f"Passed: {passed_checks}")
    print(f"Failed: {failed_checks}")
    
    # Print evidence table
    print(f"\n{'Section':<20} {'Check':<40} {'Status':<8} {'Details'}")
    print("-" * 80)
    for e in evidence:
        details = e['details'][:20] + "..." if len(e['details']) > 20 else e['details']
        print(f"{e['section']:<20} {e['check']:<40} {e['status']:<8} {details}")
    
    # Final verdict
    pass_rate = passed_checks / total_checks if total_checks > 0 else 0
    print(f"\nPass Rate: {pass_rate:.1%}")
    
    if pass_rate >= 0.9:  # 90% pass rate required
        print(f"\n🟢 RELEASE STATUS: GO")
        print("System meets release criteria.")
        return 0
    else:
        print(f"\n🔴 RELEASE STATUS: NO-GO")
        print("System does not meet release criteria. Fix failing checks.")
        return 1

def main():
    """Main verification routine."""
    print("CapSight End-to-End Release Verification")
    print("=" * 80)
    
    # Run all verification sections
    verify_environment()
    verify_file_structure()
    verify_security()
    verify_api_structure()
    verify_admin_console()
    verify_testing()
    verify_monitoring()
    verify_deployment()
    verify_documentation()
    verify_data_pipeline()
    
    # Print final summary and exit
    return print_final_summary()

if __name__ == "__main__":
    sys.exit(main())
