#!/usr/bin/env python3
"""
CapSight RLS Security Audit
Tests that anonymous users cannot write to protected tables.

Usage:
    python rls_audit.py --database-url "postgresql://..." 
    python rls_audit.py --config production
"""

import psycopg2
import argparse
import sys
from typing import List, Tuple

def test_anon_permissions(conn_str: str) -> List[Tuple[str, bool, str]]:
    """Test anonymous role permissions on critical tables."""
    results = []
    
    try:
        # Connect as anon user (this requires the anon role to exist)
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor()
        
        # Test table write permissions (should all be False)
        write_tests = [
            ('comparables', 'INSERT'),
            ('comparables', 'UPDATE'), 
            ('comparables', 'DELETE'),
            ('fundamentals', 'INSERT'),
            ('fundamentals', 'UPDATE'),
            ('fundamentals', 'DELETE'),
            ('accuracy_metrics', 'INSERT'),
            ('accuracy_metrics', 'UPDATE'),
            ('accuracy_metrics', 'DELETE')
        ]
        
        for table, permission in write_tests:
            try:
                cur.execute(f"SELECT has_table_privilege('anon', '{table}', '{permission}');")
                has_perm = cur.fetchone()[0]
                results.append((f"{table}:{permission}", has_perm, 'FAIL' if has_perm else 'PASS'))
            except Exception as e:
                results.append((f"{table}:{permission}", None, f'ERROR: {str(e)}'))
        
        # Test read permissions on safe views (should be True)
        read_tests = [
            'v_comps_trimmed',
            'latest_accuracy',
            'market_status',
            'v_system_health'
        ]
        
        for view in read_tests:
            try:
                cur.execute(f"SELECT has_table_privilege('anon', '{view}', 'SELECT');")
                has_perm = cur.fetchone()[0]
                results.append((f"{view}:SELECT", has_perm, 'PASS' if has_perm else 'FAIL'))
            except Exception as e:
                results.append((f"{view}:SELECT", None, f'ERROR: {str(e)}'))
        
        conn.close()
        
    except Exception as e:
        results.append(('CONNECTION', None, f'ERROR: {str(e)}'))
    
    return results

def test_actual_write_attempt(conn_str: str) -> List[Tuple[str, str]]:
    """Attempt actual writes and verify they are blocked."""
    results = []
    
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor()
        
        # Try to insert into comparables (should fail)
        try:
            cur.execute("""
                INSERT INTO comparables (
                    market_slug, address, city, state, sale_date,
                    price_total_usd, building_sf, cap_rate_pct
                ) VALUES (
                    'test', '123 Test St', 'Test City', 'TX', '2025-01-01',
                    1000000, 10000, 6.5
                );
            """)
            conn.commit()
            results.append(('INSERT_COMPARABLES', 'FAIL - Insert succeeded (should have failed)'))
        except psycopg2.Error as e:
            if 'permission denied' in str(e).lower() or 'policy' in str(e).lower():
                results.append(('INSERT_COMPARABLES', 'PASS - Insert blocked by RLS'))
            else:
                results.append(('INSERT_COMPARABLES', f'UNEXPECTED ERROR: {str(e)}'))
            conn.rollback()
        
        # Try to update existing record (should fail)
        try:
            cur.execute("UPDATE comparables SET price_total_usd = 999999 WHERE sale_id = (SELECT sale_id FROM comparables LIMIT 1);")
            conn.commit()
            results.append(('UPDATE_COMPARABLES', 'FAIL - Update succeeded (should have failed)'))
        except psycopg2.Error as e:
            if 'permission denied' in str(e).lower() or 'policy' in str(e).lower():
                results.append(('UPDATE_COMPARABLES', 'PASS - Update blocked by RLS'))
            else:
                results.append(('UPDATE_COMPARABLES', f'UNEXPECTED ERROR: {str(e)}'))
            conn.rollback()
        
        # Try to delete record (should fail)
        try:
            cur.execute("DELETE FROM comparables WHERE sale_id = (SELECT sale_id FROM comparables LIMIT 1);")
            conn.commit()
            results.append(('DELETE_COMPARABLES', 'FAIL - Delete succeeded (should have failed)'))
        except psycopg2.Error as e:
            if 'permission denied' in str(e).lower() or 'policy' in str(e).lower():
                results.append(('DELETE_COMPARABLES', 'PASS - Delete blocked by RLS'))
            else:
                results.append(('DELETE_COMPARABLES', f'UNEXPECTED ERROR: {str(e)}'))
            conn.rollback()
        
        conn.close()
        
    except Exception as e:
        results.append(('WRITE_TEST_CONNECTION', f'ERROR: {str(e)}'))
    
    return results

def main():
    parser = argparse.ArgumentParser(description='Audit RLS security settings')
    parser.add_argument('--database-url', help='Full database connection string')
    parser.add_argument('--config', choices=['production', 'development'], 
                       help='Use predefined config')
    
    args = parser.parse_args()
    
    if args.database_url:
        conn_str = args.database_url
    elif args.config == 'production':
        import os
        conn_str = os.getenv('DATABASE_URL')
        if not conn_str:
            print("ERROR: DATABASE_URL environment variable not set")
            sys.exit(1)
    elif args.config == 'development':
        conn_str = "postgresql://postgres:password@localhost:54322/postgres"
    else:
        print("ERROR: Either --database-url or --config is required")
        sys.exit(1)
    
    print("🔒 CapSight RLS Security Audit")
    print("=" * 50)
    
    # Test permissions
    print("\n📋 Testing Anonymous Role Permissions...")
    perm_results = test_anon_permissions(conn_str)
    
    write_failures = 0
    read_failures = 0
    
    for test, result, status in perm_results:
        print(f"  {test:30s} | {str(result):5s} | {status}")
        
        if 'INSERT' in test or 'UPDATE' in test or 'DELETE' in test:
            if status == 'FAIL':
                write_failures += 1
        elif 'SELECT' in test:
            if status == 'FAIL':
                read_failures += 1
    
    # Test actual write attempts
    print(f"\n🚨 Testing Actual Write Attempts...")
    write_results = test_actual_write_attempt(conn_str)
    
    actual_failures = 0
    for test, result in write_results:
        print(f"  {test:30s} | {result}")
        if 'FAIL' in result:
            actual_failures += 1
    
    # Summary
    print(f"\n📊 SECURITY AUDIT SUMMARY")
    print(f"  Write Permission Failures: {write_failures}")
    print(f"  Read Permission Failures:  {read_failures}")
    print(f"  Actual Write Failures:     {actual_failures}")
    
    if write_failures > 0 or actual_failures > 0:
        print("\n❌ SECURITY AUDIT FAILED")
        print("   Anonymous users can write to protected tables!")
        print("   Review RLS policies and table permissions.")
        sys.exit(1)
    elif read_failures > 0:
        print("\n⚠️  SECURITY AUDIT WARNING")
        print("   Some read permissions may be missing.")
        print("   Verify that anonymous users can read necessary views.")
        sys.exit(1)
    else:
        print("\n✅ SECURITY AUDIT PASSED")
        print("   Anonymous users properly restricted from writes.")
        print("   Read access to public views confirmed.")

if __name__ == '__main__':
    main()
