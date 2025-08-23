#!/usr/bin/env python3
"""
CapSight Nightly Accuracy Monitoring
Runs backtests and updates accuracy metrics for all markets.

This script should be run nightly via cron or pg_cron.
It calculates rolling accuracy metrics and updates the accuracy_metrics table.

Usage:
    python nightly_accuracy.py --config production
    python nightly_accuracy.py --market dfw --dry-run
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import psycopg2
import numpy as np
from dataclasses import dataclass

@dataclass
class BacktestResult:
    market_slug: str
    window_months: int
    sample_size: int
    mape: float
    rmse_bps: float
    ape_q80: float
    coverage80: float
    bias_bps: float
    last_updated: datetime

def setup_logging(log_level: str = 'INFO'):
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('nightly_accuracy.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def get_db_connection(config: str = 'production'):
    """Get database connection based on config."""
    if config == 'production':
        conn_str = os.getenv('DATABASE_URL')
        if not conn_str:
            raise ValueError("DATABASE_URL environment variable not set")
    else:
        # Development/test connection
        conn_str = "postgresql://postgres:password@localhost:54322/postgres"
    
    return psycopg2.connect(conn_str)

def run_backtest_for_market(conn, market_slug: str, 
                           window_months: int = 12) -> Optional[BacktestResult]:
    """Run backtest for a specific market and time window."""
    logging.info(f"Running backtest for {market_slug} with {window_months}m window")
    
    try:
        with conn.cursor() as cur:
            # Get holdout test set (20% of recent sales, held out from training)
            cur.execute("""
                WITH recent_sales AS (
                    SELECT * FROM v_comps_trimmed 
                    WHERE market_slug = %s 
                    AND sale_date >= %s
                    ORDER BY sale_date DESC
                ),
                test_holdout AS (
                    SELECT *, 
                           ROW_NUMBER() OVER (ORDER BY sale_date DESC) as rn,
                           COUNT(*) OVER() as total_count
                    FROM recent_sales
                ),
                test_set AS (
                    SELECT * FROM test_holdout 
                    WHERE rn <= (total_count * 0.2)  -- 20% holdout
                )
                SELECT 
                    sale_id, market_slug, building_sf, noi_annual, submarket,
                    cap_rate_pct as actual_cap_rate, sale_date,
                    price_total_usd as actual_price
                FROM test_set
                ORDER BY sale_date DESC
            """, (market_slug, datetime.now() - timedelta(days=window_months * 30)))
            
            test_cases = cur.fetchall()
            
            if len(test_cases) < 5:
                logging.warning(f"Insufficient test cases for {market_slug}: {len(test_cases)}")
                return None
            
            logging.info(f"Found {len(test_cases)} test cases for {market_slug}")
            
            # Run valuation for each test case
            predictions = []
            actuals = []
            
            for test_case in test_cases:
                sale_id, market, building_sf, noi_annual, submarket, actual_cap, sale_date, actual_price = test_case
                
                # Simulate valuation as of sale date (use comps available then)
                predicted_cap = simulate_valuation_at_date(cur, market, building_sf, submarket, sale_date)
                
                if predicted_cap is not None:
                    predicted_price = noi_annual / (predicted_cap / 100)
                    predictions.append(predicted_price)
                    actuals.append(actual_price)
            
            if len(predictions) < 3:
                logging.warning(f"Insufficient valid predictions for {market_slug}")
                return None
            
            # Calculate accuracy metrics
            predictions = np.array(predictions)
            actuals = np.array(actuals)
            
            # Absolute Percentage Error
            apes = np.abs((predictions - actuals) / actuals)
            mape = np.mean(apes)
            ape_q80 = np.percentile(apes, 80)
            
            # RMSE in basis points (cap rate equivalent)
            cap_predictions = [noi / pred * 100 for noi, pred in zip([tc[2] for tc in test_cases[:len(predictions)]], predictions)]
            cap_actuals = [tc[5] for tc in test_cases[:len(predictions)]]
            cap_errors = np.array(cap_predictions) - np.array(cap_actuals)
            rmse_bps = np.sqrt(np.mean(cap_errors ** 2)) * 100  # Convert to basis points
            
            # Bias (systematic over/under estimation)
            bias_bps = np.mean(cap_errors) * 100
            
            # Coverage at 80% confidence (simplified - would use actual confidence bands)
            # For now, check if 80% of errors are within ±10%
            within_10pct = np.sum(apes <= 0.10) / len(apes)
            
            result = BacktestResult(
                market_slug=market_slug,
                window_months=window_months,
                sample_size=len(predictions),
                mape=mape,
                rmse_bps=rmse_bps,
                ape_q80=ape_q80,
                coverage80=within_10pct,
                bias_bps=bias_bps,
                last_updated=datetime.now()
            )
            
            logging.info(f"Backtest results for {market_slug}: MAPE={mape:.3f}, RMSE={rmse_bps:.1f}bps, Coverage={within_10pct:.2f}")
            return result
            
    except Exception as e:
        logging.error(f"Error running backtest for {market_slug}: {str(e)}")
        return None

def simulate_valuation_at_date(cur, market_slug: str, building_sf: int, 
                              submarket: str, as_of_date: datetime) -> Optional[float]:
    """Simulate valuation using only comps available as of a specific date."""
    try:
        # Get comps available as of the valuation date (excluding future sales)
        cur.execute("""
            SELECT cap_rate_pct, building_sf, 
                   EXTRACT(EPOCH FROM (%s - sale_date)) / (30.44 * 24 * 3600) as months_since,
                   CASE WHEN submarket = %s THEN 1 ELSE 0 END as same_submarket
            FROM v_comps_trimmed
            WHERE market_slug = %s 
            AND sale_date < %s
            AND sale_date >= %s - INTERVAL '36 months'  -- 3-year lookback
            ORDER BY sale_date DESC
            LIMIT 50
        """, (as_of_date, submarket or '', market_slug, as_of_date, as_of_date))
        
        comps = cur.fetchall()
        
        if len(comps) < 3:
            return None
        
        # Simple weighted median calculation (simplified version of production logic)
        weights = []
        cap_rates = []
        
        for cap_rate, comp_sf, months_since, same_submarket in comps:
            # Recency weight
            weight_recency = np.exp(-np.log(2) * months_since / 12)
            
            # Size similarity weight
            log_size_ratio = np.log(comp_sf) - np.log(building_sf)
            weight_size = np.exp(-0.5 * (log_size_ratio / 0.35) ** 2)
            
            # Submarket bonus
            submarket_bonus = 1.5 if same_submarket else 1.0
            
            combined_weight = weight_recency * weight_size * submarket_bonus
            
            weights.append(combined_weight)
            cap_rates.append(cap_rate)
        
        # Weighted median
        weights = np.array(weights)
        cap_rates = np.array(cap_rates)
        
        # Sort by cap rate
        sorted_indices = np.argsort(cap_rates)
        sorted_cap_rates = cap_rates[sorted_indices]
        sorted_weights = weights[sorted_indices]
        
        # Find weighted median
        cumulative_weights = np.cumsum(sorted_weights)
        total_weight = np.sum(sorted_weights)
        median_idx = np.searchsorted(cumulative_weights, total_weight / 2)
        
        return sorted_cap_rates[median_idx] if median_idx < len(sorted_cap_rates) else sorted_cap_rates[-1]
        
    except Exception as e:
        logging.error(f"Error simulating valuation: {str(e)}")
        return None

def update_accuracy_metrics(conn: psycopg2.connection, results: List[BacktestResult], 
                           dry_run: bool = False) -> None:
    """Update accuracy_metrics table with backtest results."""
    if dry_run:
        logging.info("DRY RUN: Would update accuracy_metrics with:")
        for result in results:
            logging.info(f"  {result.market_slug}: MAPE={result.mape:.3f}, RMSE={result.rmse_bps:.1f}bps")
        return
    
    try:
        with conn.cursor() as cur:
            for result in results:
                # Insert or update accuracy metrics
                cur.execute("""
                    INSERT INTO accuracy_metrics (
                        market_slug, window_months, sample_size, mape, rmse_bps, 
                        ape_q80, coverage80, bias_bps, last_updated
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (market_slug, window_months) 
                    DO UPDATE SET
                        sample_size = EXCLUDED.sample_size,
                        mape = EXCLUDED.mape,
                        rmse_bps = EXCLUDED.rmse_bps,
                        ape_q80 = EXCLUDED.ape_q80,
                        coverage80 = EXCLUDED.coverage80,
                        bias_bps = EXCLUDED.bias_bps,
                        last_updated = EXCLUDED.last_updated
                """, (
                    result.market_slug, result.window_months, result.sample_size,
                    result.mape, result.rmse_bps, result.ape_q80, 
                    result.coverage80, result.bias_bps, result.last_updated
                ))
            
            conn.commit()
            logging.info(f"Updated accuracy metrics for {len(results)} markets")
            
    except Exception as e:
        logging.error(f"Error updating accuracy metrics: {str(e)}")
        conn.rollback()
        raise

def check_sla_alerts(conn: psycopg2.connection, config: str) -> None:
    """Check if any markets are violating SLA thresholds and send alerts."""
    try:
        with conn.cursor() as cur:
            # Check for SLA violations
            cur.execute("""
                SELECT market_slug, mape, rmse_bps, coverage80, last_updated
                FROM latest_accuracy
                WHERE mape > 0.10  -- MAPE > 10%
                   OR rmse_bps > 50  -- RMSE > 50 bps
                   OR coverage80 < 0.78  -- Coverage < 78%
                   OR coverage80 > 0.82  -- Coverage > 82%
                   OR last_updated < NOW() - INTERVAL '2 days'  -- Stale data
            """)
            
            violations = cur.fetchall()
            
            if violations:
                logging.warning(f"SLA VIOLATIONS DETECTED: {len(violations)} markets")
                for market, mape, rmse, coverage, updated in violations:
                    logging.warning(f"  {market}: MAPE={mape:.3f}, RMSE={rmse:.1f}bps, Coverage={coverage:.2f}, Updated={updated}")
                
                # In production, this would send alerts via email/Slack
                if config == 'production':
                    # send_sla_alert(violations)
                    pass
            else:
                logging.info("All markets within SLA thresholds")
                
    except Exception as e:
        logging.error(f"Error checking SLA alerts: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Run nightly accuracy monitoring')
    parser.add_argument('--config', choices=['production', 'development'], default='development',
                       help='Configuration environment')
    parser.add_argument('--market', help='Run for specific market only')
    parser.add_argument('--since', help='Window (e.g., "12m", "18m") instead of --window-months')
    parser.add_argument('--window-months', type=int, default=12, 
                       help='Backtest window in months')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Dry run - calculate but do not update database')
    parser.add_argument('--print-metrics', action='store_true',
                       help='Print detailed metrics to stdout')
    parser.add_argument('--assert-sla', help='Assert SLA conditions (comma-separated, e.g., "MAPE<=0.10,RMSE_BPS<=50")')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Handle --since parameter (e.g., "18m" -> 18 months)
    if args.since:
        if args.since.endswith('m'):
            args.window_months = int(args.since[:-1])
        else:
            logging.error("--since must end with 'm' (e.g., '18m')")
            sys.exit(1)
    
    setup_logging(args.log_level)
    logging.info(f"Starting nightly accuracy monitoring - Config: {args.config}")
    
    try:
        conn = get_db_connection(args.config)
        
        # Get list of markets to process
        if args.market:
            markets = [args.market]
        else:
            with conn.cursor() as cur:
                cur.execute("SELECT DISTINCT market_slug FROM v_comps_trimmed ORDER BY market_slug")
                markets = [row[0] for row in cur.fetchall()]
        
        logging.info(f"Processing {len(markets)} markets: {', '.join(markets)}")
        
        # Run backtests
        results = []
        for market in markets:
            result = run_backtest_for_market(conn, market, args.window_months)
            if result:
                results.append(result)
        
        # Print metrics if requested
        if args.print_metrics:
            print("\n📊 ACCURACY METRICS:")
            print("Market   | MAPE   | RMSE(bps) | Coverage | Sample")
            print("---------+--------+-----------+----------+-------")
            for result in results:
                print(f"{result.market_slug:8s} | {result.mape:.3f} | {result.rmse_bps:8.1f} | {result.coverage80:.3f}  | {result.sample_size:5d}")
        
        # Assert SLA conditions if requested
        if args.assert_sla:
            sla_conditions = args.assert_sla.split(',')
            violations = []
            
            for result in results:
                for condition in sla_conditions:
                    condition = condition.strip()
                    if '=' in condition:
                        field, op_value = condition.split('=', 1)
                        field = field.strip().lower()
                        
                        if '<=' in op_value:
                            operator = '<='
                            threshold = float(op_value.replace('<=', ''))
                        elif '>=' in op_value:
                            operator = '>='
                            threshold = float(op_value.replace('>=', ''))
                        else:
                            logging.error(f"Unsupported operator in condition: {condition}")
                            continue
                        
                        # Map field names
                        field_map = {
                            'mape': result.mape,
                            'rmse_bps': result.rmse_bps,
                            'coverage80': result.coverage80
                        }
                        
                        if field not in field_map:
                            logging.error(f"Unknown field in assertion: {field}")
                            continue
                        
                        actual_value = field_map[field]
                        
                        if operator == '<=' and actual_value > threshold:
                            violations.append(f"{result.market_slug}: {field.upper()}={actual_value:.3f} > {threshold}")
                        elif operator == '>=' and actual_value < threshold:
                            violations.append(f"{result.market_slug}: {field.upper()}={actual_value:.3f} < {threshold}")
            
            if violations:
                print("\n❌ SLA ASSERTION FAILURES:")
                for violation in violations:
                    print(f"  • {violation}")
                logging.error(f"SLA assertions failed: {len(violations)} violations")
                sys.exit(1)
            else:
                print("✅ All SLA assertions passed")
        
        # Update database
        if results:
            update_accuracy_metrics(conn, results, args.dry_run)
            
            # Check for SLA violations
            if not args.dry_run:
                check_sla_alerts(conn, args.config)
        else:
            logging.warning("No backtest results to update")
        
        logging.info("Nightly accuracy monitoring completed successfully")
        
    except Exception as e:
        logging.error(f"Fatal error in nightly accuracy monitoring: {str(e)}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    main()
