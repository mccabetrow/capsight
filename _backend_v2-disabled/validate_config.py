#!/usr/bin/env python3
"""
CapSight Backend v2 - Configuration Validation Script
Validates all required environment variables and API keys are present
"""

import os
import sys
import re
from typing import List, Dict, Tuple
from datetime import datetime

# ANSI color codes
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
BOLD = '\033[1m'
END = '\033[0m'

def print_status(message: str, status: str = "INFO"):
    """Print colored status message"""
    colors = {
        "INFO": BLUE,
        "SUCCESS": GREEN, 
        "WARNING": YELLOW,
        "ERROR": RED
    }
    color = colors.get(status, BLUE)
    print(f"{color}[{status}]{END} {message}")

def check_required_vars() -> List[Tuple[str, str, str]]:
    """Check all required environment variables"""
    
    required_vars = [
        # Core Infrastructure
        ("DATABASE_URL", "Database connection string", "critical"),
        ("REDIS_URL", "Redis cache connection", "critical"),
        ("POSTGRES_PASSWORD", "Database password", "critical"),
        ("JWT_SECRET", "JWT signing secret", "critical"),
        
        # External APIs
        ("FRED_API_KEY", "Federal Reserve Economic Data API", "high"),
        ("BLOOMBERG_API_KEY", "Bloomberg Terminal API", "medium"),
        ("REFINITIV_API_KEY", "Refinitiv Market Data", "medium"),
        ("SAFEGRAPH_API_KEY", "SafeGraph Mobility Data", "low"),
        ("GOOGLE_TRENDS_API_KEY", "Google Trends API", "low"),
        
        # Monitoring & Alerts
        ("PAGERDUTY_API_KEY", "PagerDuty alerting", "high"),
        ("SENTRY_DSN", "Sentry error tracking", "medium"),
        ("GRAFANA_PASSWORD", "Grafana admin password", "high"),
        
        # ML & Feature Store
        ("MLFLOW_TRACKING_URI", "MLflow model registry", "high"),
        ("MODEL_REGISTRY_S3_BUCKET", "Model artifact storage", "high"),
        ("FEAST_REPO_PATH", "Feature store repository", "medium"),
        
        # Cloud & Storage
        ("AWS_ACCESS_KEY_ID", "AWS access credentials", "medium"),
        ("AWS_SECRET_ACCESS_KEY", "AWS secret key", "medium"),
    ]
    
    results = []
    
    for var_name, description, priority in required_vars:
        value = os.getenv(var_name, "").strip()
        
        if not value:
            results.append((var_name, description, f"MISSING ({priority} priority)"))
        elif value.startswith(("your_", "REPLACE_WITH_", "dummy_", "change_")):
            results.append((var_name, description, f"PLACEHOLDER ({priority} priority)"))
        elif len(value) < 8:
            results.append((var_name, description, f"TOO_SHORT ({priority} priority)"))
        else:
            results.append((var_name, description, "OK"))
    
    return results

def validate_api_key_format() -> Dict[str, str]:
    """Validate API key formats"""
    
    format_checks = {
        "FRED_API_KEY": r"^[a-f0-9]{32,64}$",
        "JWT_SECRET": r"^.{64,}$",  # At least 64 characters
        "PAGERDUTY_API_KEY": r"^[a-zA-Z0-9_-]{20,}$",
    }
    
    results = {}
    
    for var_name, pattern in format_checks.items():
        value = os.getenv(var_name, "")
        if value and not re.match(pattern, value):
            results[var_name] = "INVALID_FORMAT"
        elif value:
            results[var_name] = "VALID_FORMAT"
        else:
            results[var_name] = "NOT_SET"
    
    return results

def check_sla_configuration() -> Dict[str, str]:
    """Check SLA target configuration"""
    
    sla_vars = {
        "ACCURACY_CAPRATE_MAE_BPS": (50.0, 100.0),  # 50-100 basis points
        "ACCURACY_NOI_MAPE_PERCENT": (8.0, 20.0),   # 8-20% MAPE
        "FRESHNESS_INTRADAY_RATES_MINUTES": (5, 30), # 5-30 minutes
        "FRESHNESS_HOURLY_MORTGAGE_MINUTES": (30, 120), # 30-120 minutes
    }
    
    results = {}
    
    for var_name, (min_val, max_val) in sla_vars.items():
        value_str = os.getenv(var_name, "")
        
        try:
            value = float(value_str)
            if min_val <= value <= max_val:
                results[var_name] = f"OK ({value})"
            else:
                results[var_name] = f"OUT_OF_RANGE ({value}, expected {min_val}-{max_val})"
        except (ValueError, TypeError):
            results[var_name] = f"INVALID ({value_str})"
    
    return results

def test_database_connection() -> bool:
    """Test database connectivity"""
    try:
        import asyncpg
        import asyncio
        
        async def test_db():
            database_url = os.getenv("DATABASE_URL", "")
            if not database_url:
                return False
            
            try:
                conn = await asyncpg.connect(database_url)
                await conn.execute("SELECT 1")
                await conn.close()
                return True
            except Exception:
                return False
        
        return asyncio.run(test_db())
    except ImportError:
        print_status("asyncpg not installed - skipping database test", "WARNING")
        return None

def test_redis_connection() -> bool:
    """Test Redis connectivity"""
    try:
        import redis
        
        redis_url = os.getenv("REDIS_URL", "")
        if not redis_url:
            return False
        
        r = redis.from_url(redis_url)
        r.ping()
        return True
    except ImportError:
        print_status("redis not installed - skipping Redis test", "WARNING")
        return None
    except Exception:
        return False

def generate_validation_report() -> Dict[str, any]:
    """Generate comprehensive validation report"""
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "environment": os.getenv("ENVIRONMENT", "unknown"),
        "validation_results": {}
    }
    
    # Check required variables
    print_status("Checking required environment variables...", "INFO")
    var_results = check_required_vars()
    
    missing_critical = []
    missing_high = []
    placeholders = []
    
    for var_name, description, status in var_results:
        if "MISSING" in status and "critical" in status:
            missing_critical.append(var_name)
        elif "MISSING" in status and "high" in status:
            missing_high.append(var_name)
        elif "PLACEHOLDER" in status:
            placeholders.append(var_name)
    
    report["validation_results"]["required_vars"] = {
        "total_checked": len(var_results),
        "missing_critical": missing_critical,
        "missing_high_priority": missing_high,
        "placeholders": placeholders,
        "details": var_results
    }
    
    # Check API key formats
    print_status("Validating API key formats...", "INFO")
    format_results = validate_api_key_format()
    report["validation_results"]["api_key_formats"] = format_results
    
    # Check SLA configuration
    print_status("Validating SLA configuration...", "INFO")
    sla_results = check_sla_configuration()
    report["validation_results"]["sla_targets"] = sla_results
    
    # Test connectivity
    print_status("Testing database connectivity...", "INFO")
    db_result = test_database_connection()
    report["validation_results"]["database_connection"] = db_result
    
    print_status("Testing Redis connectivity...", "INFO")
    redis_result = test_redis_connection()
    report["validation_results"]["redis_connection"] = redis_result
    
    return report

def main():
    """Main validation function"""
    
    print(f"{BOLD}CapSight Backend v2 - Configuration Validation{END}")
    print("=" * 60)
    
    # Load .env file if present
    env_file = ".env"
    if os.path.exists(env_file):
        print_status(f"Loading environment from {env_file}", "INFO")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
    else:
        print_status(f"No {env_file} file found", "WARNING")
    
    # Generate validation report
    report = generate_validation_report()
    
    # Print results
    print("\n" + "="*60)
    print(f"{BOLD}VALIDATION RESULTS{END}")
    print("="*60)
    
    # Required variables summary
    req_vars = report["validation_results"]["required_vars"]
    if req_vars["missing_critical"]:
        print_status(f"CRITICAL: {len(req_vars['missing_critical'])} critical variables missing", "ERROR")
        for var in req_vars["missing_critical"]:
            print(f"  - {var}")
    
    if req_vars["missing_high_priority"]:
        print_status(f"HIGH PRIORITY: {len(req_vars['missing_high_priority'])} high priority variables missing", "WARNING")
        for var in req_vars["missing_high_priority"]:
            print(f"  - {var}")
    
    if req_vars["placeholders"]:
        print_status(f"PLACEHOLDERS: {len(req_vars['placeholders'])} variables still have placeholder values", "WARNING")
        for var in req_vars["placeholders"]:
            print(f"  - {var}")
    
    # API key format validation
    format_results = report["validation_results"]["api_key_formats"]
    invalid_formats = [k for k, v in format_results.items() if v == "INVALID_FORMAT"]
    if invalid_formats:
        print_status(f"FORMAT ISSUES: {len(invalid_formats)} API keys have invalid formats", "WARNING")
        for var in invalid_formats:
            print(f"  - {var}")
    
    # SLA configuration
    sla_results = report["validation_results"]["sla_targets"]
    sla_issues = [k for k, v in sla_results.items() if not v.startswith("OK")]
    if sla_issues:
        print_status(f"SLA CONFIG: {len(sla_issues)} SLA targets need attention", "WARNING")
        for var in sla_issues:
            print(f"  - {var}: {sla_results[var]}")
    
    # Connectivity tests
    db_conn = report["validation_results"]["database_connection"]
    redis_conn = report["validation_results"]["redis_connection"]
    
    if db_conn is True:
        print_status("Database connection: SUCCESS", "SUCCESS")
    elif db_conn is False:
        print_status("Database connection: FAILED", "ERROR")
    else:
        print_status("Database connection: SKIPPED", "INFO")
    
    if redis_conn is True:
        print_status("Redis connection: SUCCESS", "SUCCESS")
    elif redis_conn is False:
        print_status("Redis connection: FAILED", "ERROR")
    else:
        print_status("Redis connection: SKIPPED", "INFO")
    
    # Overall assessment
    print("\n" + "="*60)
    
    critical_issues = len(req_vars["missing_critical"])
    high_issues = len(req_vars["missing_high_priority"])
    connection_issues = sum([
        1 for conn in [db_conn, redis_conn] 
        if conn is False
    ])
    
    if critical_issues > 0:
        print_status("DEPLOYMENT STATUS: NOT READY (Critical issues found)", "ERROR")
        print("   Fix critical configuration issues before deployment")
        return 1
    elif high_issues > 2 or connection_issues > 0:
        print_status("DEPLOYMENT STATUS: DEGRADED (Issues found)", "WARNING")  
        print("   System may deploy but with reduced functionality")
        return 2
    else:
        print_status("DEPLOYMENT STATUS: READY", "SUCCESS")
        print("   All critical configurations validated successfully")
        return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
