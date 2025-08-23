#!/usr/bin/env python3
"""
CapSight Production Readiness Checklist
Automated verification of all production requirements.

Usage:
    python production_checklist.py --config production
    python production_checklist.py --skip-tests  # Skip long-running tests
"""

import subprocess
import argparse
import sys
import os
import json
from datetime import datetime
from typing import List, Tuple, Dict

def run_command(cmd: str, capture_output=True) -> Tuple[bool, str]:
    """Run a shell command and return success status and output."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=capture_output, 
            text=True, timeout=300
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)

def check_item(name: str, check_func, critical=True) -> Dict:
    """Run a check and return result."""
    print(f"🔍 {name}...")
    try:
        success, message = check_func()
        status = "✅ PASS" if success else ("❌ FAIL" if critical else "⚠️  WARN")
        print(f"   {status}: {message}")
        return {
            "name": name,
            "success": success,
            "critical": critical,
            "message": message,
            "status": status
        }
    except Exception as e:
        status = "❌ ERROR"
        message = str(e)
        print(f"   {status}: {message}")
        return {
            "name": name,
            "success": False,
            "critical": critical,
            "message": message,
            "status": status
        }

def check_csv_validation() -> Tuple[bool, str]:
    """Check CSV validation with all markets."""
    success, output = run_command("python validate_csv_enhanced.py --all-markets --strict")
    return success, "All market data validated" if success else f"Validation failed: {output}"

def check_nightly_backtest() -> Tuple[bool, str]:
    """Check nightly backtest dry run."""
    success, output = run_command("python nightly_accuracy.py --since 18m --dry-run --print-metrics")
    return success, "Backtest dry-run passed" if success else f"Backtest failed: {output}"

def check_sla_gates() -> Tuple[bool, str]:
    """Check SLA compliance."""
    success, output = run_command('python nightly_accuracy.py --since 18m --dry-run --assert-sla "MAPE<=0.10,RMSE_BPS<=50,COVERAGE80>=0.78,COVERAGE80<=0.82"')
    return success, "SLA requirements met" if success else f"SLA not met: {output}"

def check_database_connectivity() -> Tuple[bool, str]:
    """Check database connection."""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        return False, "DATABASE_URL not set"
    
    success, output = run_command(f'psql "{db_url}" -c "SELECT 1;"')
    return success, "Database connected" if success else f"Database connection failed: {output}"

def check_accuracy_tables() -> Tuple[bool, str]:
    """Check that accuracy tables exist."""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        return False, "DATABASE_URL not set"
    
    success, output = run_command(f'psql "{db_url}" -c "SELECT COUNT(*) FROM accuracy_metrics;"')
    if success and "SELECT 1" not in output:
        return True, "accuracy_metrics table exists"
    return False, f"accuracy_metrics table missing: {output}"

def check_rls_security() -> Tuple[bool, str]:
    """Check RLS security audit."""
    success, output = run_command("python rls_audit.py --config production")
    return success, "RLS security audit passed" if success else f"Security issues: {output}"

def check_api_health() -> Tuple[bool, str]:
    """Check API health endpoint."""
    success, output = run_command("curl -f http://localhost:3000/api/health")
    if success:
        try:
            health = json.loads(output)
            if health.get('status') == 'healthy':
                return True, "API health check passed"
        except:
            pass
    return False, f"API health check failed: {output}"

def check_rate_limiting() -> Tuple[bool, str]:
    """Test rate limiting."""
    # Make multiple rapid requests
    for i in range(5):
        success, _ = run_command("curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:3000/api/value -H 'Content-Type: application/json' -d '{\"market_slug\":\"dfw\",\"noi_annual\":1000000,\"building_sf\":100000}'")
    
    # Make one more that should be rate limited
    success, output = run_command("curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:3000/api/value -H 'Content-Type: application/json' -d '{\"market_slug\":\"dfw\",\"noi_annual\":1000000,\"building_sf\":100000}'")
    
    if success and output.strip() == "429":
        return True, "Rate limiting working"
    return False, f"Rate limiting not working: got {output}"

def check_frontend_build() -> Tuple[bool, str]:
    """Check frontend builds successfully."""
    os.chdir('frontend')
    success, output = run_command("npm run build")
    os.chdir('..')
    return success, "Frontend build successful" if success else f"Build failed: {output}"

def check_e2e_tests() -> Tuple[bool, str]:
    """Run E2E tests."""
    os.chdir('frontend')
    success, output = run_command("npx playwright test")
    os.chdir('..')
    return success, "E2E tests passed" if success else f"E2E tests failed: {output}"

def check_env_vars() -> Tuple[bool, str]:
    """Check required environment variables."""
    required_vars = [
        'DATABASE_URL',
        'NEXT_PUBLIC_SUPABASE_URL',
        'NEXT_PUBLIC_SUPABASE_ANON_KEY',
        'SUPABASE_SERVICE_ROLE_KEY'
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        return False, f"Missing env vars: {', '.join(missing)}"
    return True, "All required env vars present"

def check_methodology_docs() -> Tuple[bool, str]:
    """Check methodology documentation exists."""
    if os.path.exists('VALUATION_METHOD.md'):
        return True, "Methodology documentation present"
    return False, "VALUATION_METHOD.md missing"

def check_backup_config() -> Tuple[bool, str]:
    """Check backup configuration."""
    if os.path.exists('backup_strategy.md'):
        return True, "Backup strategy documented"
    return False, "Backup strategy not documented"

def main():
    parser = argparse.ArgumentParser(description='Run production readiness checklist')
    parser.add_argument('--config', choices=['production', 'development'], default='development')
    parser.add_argument('--skip-tests', action='store_true', help='Skip long-running tests')
    parser.add_argument('--output', help='Save results to JSON file')
    
    args = parser.parse_args()
    
    print("🚀 CapSight Production Readiness Checklist")
    print("=" * 60)
    print(f"Configuration: {args.config}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("")
    
    # Define all checks
    checks = [
        ("Environment Variables", check_env_vars, True),
        ("Database Connectivity", check_database_connectivity, True),
        ("Accuracy Tables", check_accuracy_tables, True),
        ("CSV Data Validation", check_csv_validation, True),
        ("Nightly Backtest Dry-Run", check_nightly_backtest, True),
        ("SLA Gate Compliance", check_sla_gates, True),
        ("RLS Security Audit", check_rls_security, True),
        ("Frontend Build", check_frontend_build, True),
        ("API Health Check", check_api_health, False),  # Non-critical if server not running
        ("Rate Limiting", check_rate_limiting, False),
        ("Methodology Documentation", check_methodology_docs, True),
        ("Backup Configuration", check_backup_config, False),
    ]
    
    if not args.skip_tests:
        checks.append(("E2E Truth Tests", check_e2e_tests, True))
    
    # Run all checks
    results = []
    for name, check_func, critical in checks:
        result = check_item(name, check_func, critical)
        results.append(result)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 CHECKLIST SUMMARY")
    print("=" * 60)
    
    total = len(results)
    passed = sum(1 for r in results if r['success'])
    critical_failed = sum(1 for r in results if not r['success'] and r['critical'])
    warnings = sum(1 for r in results if not r['success'] and not r['critical'])
    
    print(f"Total Checks: {total}")
    print(f"Passed: {passed}")
    print(f"Critical Failures: {critical_failed}")
    print(f"Warnings: {warnings}")
    
    if critical_failed > 0:
        print(f"\n❌ PRODUCTION READINESS: FAILED")
        print("Critical issues must be resolved before deployment.")
        print("\nCritical Failures:")
        for r in results:
            if not r['success'] and r['critical']:
                print(f"  • {r['name']}: {r['message']}")
    elif warnings > 0:
        print(f"\n⚠️  PRODUCTION READINESS: WARNING")
        print("Non-critical issues detected but deployment may proceed.")
        print("\nWarnings:")
        for r in results:
            if not r['success'] and not r['critical']:
                print(f"  • {r['name']}: {r['message']}")
    else:
        print(f"\n✅ PRODUCTION READINESS: PASSED")
        print("All checks passed! System ready for deployment.")
    
    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'config': args.config,
                'summary': {
                    'total': total,
                    'passed': passed,
                    'critical_failed': critical_failed,
                    'warnings': warnings,
                    'ready': critical_failed == 0
                },
                'results': results
            }, f, indent=2)
        print(f"\n💾 Results saved to {args.output}")
    
    # Exit with appropriate code
    sys.exit(0 if critical_failed == 0 else 1)

if __name__ == '__main__':
    main()
