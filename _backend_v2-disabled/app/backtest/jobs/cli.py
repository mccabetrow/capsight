#!/usr/bin/env python3
"""
Command-line interface for backtest operations
Usage: python -m backend_v2.app.backtest.jobs.cli [command] [options]
"""
import asyncio
import argparse
import sys
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from backend_v2.app.backtest.config import config
from backend_v2.app.backtest.schemas import (
    BacktestRun, BacktestJobConfig, BacktestSchedule, ReplayScenario
)
from backend_v2.app.backtest.data_access import BacktestDataAccess
from backend_v2.app.backtest.time_slicer import time_slicer
from backend_v2.app.backtest.feature_loader import feature_loader
from backend_v2.app.backtest.replay import replay_engine
from backend_v2.app.backtest.metrics import metrics_calculator
from backend_v2.app.backtest.uplift import uplift_analyzer
from backend_v2.app.backtest.reports.renderer import report_renderer
from backend_v2.app.backtest.jobs.scheduler import job_scheduler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BacktestCLI:
    """Command-line interface for backtest operations"""
    
    def __init__(self):
        self.data_access = BacktestDataAccess()
    
    async def run_backtest(self, args) -> None:
        """Run a new backtest"""
        
        try:
            # Parse prediction date
            if args.prediction_date:
                prediction_date = datetime.strptime(args.prediction_date, "%Y-%m-%d").date()
            else:
                prediction_date = date.today()
            
            # Generate time window
            time_window = time_slicer.asof_window(
                asof_date=prediction_date,
                horizon_months=args.horizon_months
            )
            
            # Create backtest run
            run_id = f"cli_backtest_{int(datetime.now().timestamp())}"
            backtest_run = BacktestRun(
                run_id=run_id,
                run_name=args.name,
                created_at=datetime.now(),
                prediction_date=datetime.combine(prediction_date, datetime.min.time()),
                horizon_months=args.horizon_months,
                model_version=args.model_version,
                feature_set={"feature_views": args.feature_views},
                status="running",
                config={
                    "cli_args": vars(args),
                    "training_window": {
                        "start": time_window.train_start.isoformat(),
                        "end": time_window.train_end.isoformat()
                    }
                }
            )
            
            await self.data_access.create_backtest_run(backtest_run)
            logger.info(f"Created backtest run: {run_id}")
            
            # Load entity IDs
            if args.entity_ids:
                entity_ids = args.entity_ids
            elif args.entity_file:
                entity_ids = self._load_entity_ids_from_file(args.entity_file)
            else:
                entity_ids = [f"property_{i}" for i in range(1, args.entity_count + 1)]
            
            logger.info(f"Running backtest on {len(entity_ids)} entities")
            
            # Load features
            logger.info("Loading features...")
            feature_data = await feature_loader.create_training_dataset(
                entity_ids=entity_ids,
                training_window=time_window,
                feature_views=args.feature_views
            )
            
            # Generate predictions (mock)
            logger.info("Generating predictions...")
            predictions = await self._generate_predictions(run_id, entity_ids, args.model_version)
            
            # Save predictions
            for pred in predictions:
                await self.data_access.create_prediction_snapshot(pred)
            
            # Update run status
            backtest_run.status = "completed"
            await self.data_access.update_backtest_run(backtest_run)
            
            logger.info(f"Backtest completed: {run_id}")
            logger.info(f"Generated {len(predictions)} predictions")
            
            # Generate report if requested
            if args.generate_report:
                await self._generate_cli_report(run_id, args.report_format)
            
            print(f"SUCCESS: Backtest completed with run_id: {run_id}")
            
        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            print(f"ERROR: {e}")
            sys.exit(1)
    
    async def replay_analysis(self, args) -> None:
        """Run replay analysis"""
        
        try:
            # Create replay scenario
            scenario_params = {}
            if args.scenario_params:
                scenario_params = json.loads(args.scenario_params)
            
            feature_overrides = {}
            if args.feature_overrides:
                feature_overrides = json.loads(args.feature_overrides)
            
            threshold_overrides = {}
            if args.threshold_overrides:
                threshold_overrides = json.loads(args.threshold_overrides)
            
            replay_scenario = ReplayScenario(
                scenario_name=args.scenario_name,
                replay_mode=args.replay_mode,
                entity_ids=args.entity_ids,
                model_version=args.model_version,
                scenario_params=scenario_params,
                feature_overrides=feature_overrides,
                threshold_overrides=threshold_overrides
            )
            
            logger.info(f"Running replay analysis on {args.original_run_id}")
            
            # Execute replay
            replay_run = await replay_engine.replay_historical_predictions(
                original_run_id=args.original_run_id,
                replay_scenario=replay_scenario
            )
            
            logger.info(f"Replay completed: {replay_run.run_id}")
            
            # Generate comparison report if requested
            if args.generate_comparison:
                comparison = await replay_engine.compare_replay_results(
                    original_run_id=args.original_run_id,
                    replay_run_id=replay_run.run_id
                )
                
                print("\\n=== REPLAY COMPARISON ===")
                print(f"Original Run: {args.original_run_id}")
                print(f"Replay Run: {replay_run.run_id}")
                print(f"Prediction Agreement: {comparison['comparison_metrics']['prediction_agreement']:.3f}")
                print(f"Probability Correlation: {comparison['comparison_metrics']['probability_correlation']:.3f}")
                print(f"Mean Probability Difference: {comparison['comparison_metrics']['mean_probability_difference']:.4f}")
            
            print(f"SUCCESS: Replay analysis completed with run_id: {replay_run.run_id}")
            
        except Exception as e:
            logger.error(f"Replay analysis failed: {e}")
            print(f"ERROR: {e}")
            sys.exit(1)
    
    async def uplift_analysis(self, args) -> None:
        """Run uplift analysis"""
        
        try:
            logger.info(f"Running uplift analysis on {args.treatment_run_id}")
            
            # Generate uplift report
            uplift_report = await uplift_analyzer.generate_uplift_report(
                treatment_run_id=args.treatment_run_id,
                baseline_strategy=args.baseline_strategy,
                outcome_column=args.outcome_column
            )
            
            # Print results
            print("\\n=== UPLIFT ANALYSIS RESULTS ===")
            print(f"Treatment Run: {args.treatment_run_id}")
            print(f"Baseline Strategy: {args.baseline_strategy}")
            print(f"Relative Uplift: {uplift_report['overall_uplift']['relative_uplift_pct']:.1f}%")
            print(f"Statistical Significance: {'Yes' if uplift_report['overall_uplift']['statistical_significance'] else 'No'}")
            print(f"P-Value: {uplift_report['overall_uplift']['p_value']:.4f}")
            print(f"Incremental Profit: ${uplift_report['roi_analysis']['incremental_profit']:,.0f}")
            print(f"Treatment ROI: {uplift_report['roi_analysis']['treatment_roi']:.2f}")
            print(f"Baseline ROI: {uplift_report['roi_analysis']['baseline_roi']:.2f}")
            
            # Cohort analysis
            if uplift_report['cohort_analysis']:
                print("\\n=== COHORT ANALYSIS ===")
                for cohort in uplift_report['cohort_analysis']:
                    significance = "✓" if cohort['significant'] else "✗"
                    print(f"  {cohort['cohort_name']}: {cohort['uplift']:.4f} [{significance}] (n={cohort['sample_size']})")
            
            # Feature impacts
            if uplift_report['feature_impacts']:
                print("\\n=== FEATURE IMPACTS ===")
                sorted_features = sorted(
                    uplift_report['feature_impacts'].items(),
                    key=lambda x: x[1],
                    reverse=True
                )
                for feature, impact in sorted_features[:10]:  # Top 10
                    print(f"  {feature}: {impact:.4f}")
            
            # Save detailed report if requested
            if args.output_file:
                output_path = Path(args.output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w') as f:
                    json.dump(uplift_report, f, indent=2, default=str)
                print(f"\\nDetailed report saved to: {output_path}")
            
            print("SUCCESS: Uplift analysis completed")
            
        except Exception as e:
            logger.error(f"Uplift analysis failed: {e}")
            print(f"ERROR: {e}")
            sys.exit(1)
    
    async def generate_report(self, args) -> None:
        """Generate report for a backtest run"""
        
        try:
            logger.info(f"Generating report for {args.run_id}")
            
            # Determine output path
            if args.output:
                output_path = args.output
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"backtest_report_{args.run_id}_{timestamp}.{args.format}"
            
            # Generate report
            report_path = await report_renderer.generate_comprehensive_report(
                run_id=args.run_id,
                output_format=args.format,
                include_charts=args.include_charts,
                include_uplift=args.include_uplift,
                include_sample_predictions=args.include_samples,
                output_path=output_path
            )
            
            print(f"SUCCESS: Report generated at {report_path}")
            
            # Generate executive summary if requested
            if args.executive_summary:
                summary = await report_renderer.generate_executive_summary(
                    run_id=args.run_id,
                    target_audience="executive"
                )
                print("\\n=== EXECUTIVE SUMMARY ===")
                print(summary)
            
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            print(f"ERROR: {e}")
            sys.exit(1)
    
    async def list_runs(self, args) -> None:
        """List backtest runs"""
        
        try:
            # Get recent runs (mock implementation)
            runs = await self._get_recent_runs(args.limit)
            
            if not runs:
                print("No backtest runs found")
                return
            
            print("\\n=== BACKTEST RUNS ===")
            print(f"{'Run ID':<30} {'Name':<20} {'Status':<10} {'Created':<20} {'Horizon':<8}")
            print("-" * 90)
            
            for run in runs:
                created_str = run['created_at'][:19] if len(run['created_at']) > 19 else run['created_at']
                print(f"{run['run_id']:<30} {run['run_name']:<20} {run['status']:<10} {created_str:<20} {run['horizon_months']:<8}")
            
        except Exception as e:
            logger.error(f"Failed to list runs: {e}")
            print(f"ERROR: {e}")
            sys.exit(1)
    
    async def schedule_job(self, args) -> None:
        """Schedule a recurring backtest job"""
        
        try:
            # Create job config
            job_config = BacktestJobConfig(
                job_name=args.job_name,
                job_type=args.job_type,
                model_version=args.model_version,
                prediction_date=datetime.strptime(args.prediction_date, "%Y-%m-%d").date() if args.prediction_date else None,
                horizon_months=args.horizon_months,
                entity_ids=args.entity_ids,
                feature_config=json.loads(args.feature_config) if args.feature_config else {},
                feature_views=args.feature_views,
                generate_reports=args.generate_reports,
                notifications=json.loads(args.notifications) if args.notifications else {}
            )
            
            # Create schedule config
            schedule_config = BacktestSchedule(
                schedule_type=args.schedule_type,
                cron_expression=args.cron_expression,
                interval_seconds=args.interval_seconds
            )
            
            # Start scheduler if not running
            await job_scheduler.start_scheduler()
            
            # Schedule job
            job_id = await job_scheduler.schedule_recurring_backtest(
                schedule_config=schedule_config,
                job_config=job_config
            )
            
            print(f"SUCCESS: Scheduled job with ID: {job_id}")
            logger.info(f"Scheduled recurring job: {job_id}")
            
        except Exception as e:
            logger.error(f"Job scheduling failed: {e}")
            print(f"ERROR: {e}")
            sys.exit(1)
    
    async def list_jobs(self, args) -> None:
        """List scheduled jobs"""
        
        try:
            jobs = await job_scheduler.list_scheduled_jobs()
            
            if not jobs:
                print("No scheduled jobs found")
                return
            
            print("\\n=== SCHEDULED JOBS ===")
            print(f"{'Job ID':<30} {'Status':<10} {'Next Run':<20} {'Run ID':<25}")
            print("-" * 85)
            
            for job in jobs:
                next_run = job.get('next_run', 'N/A')
                if next_run and next_run != 'N/A':
                    next_run = next_run[:19]  # Truncate timestamp
                
                run_id = job.get('run_id', 'N/A')
                status = job.get('status', 'scheduled')
                
                print(f"{job['job_id']:<30} {status:<10} {next_run:<20} {run_id:<25}")
            
        except Exception as e:
            logger.error(f"Failed to list jobs: {e}")
            print(f"ERROR: {e}")
            sys.exit(1)
    
    async def cancel_job(self, args) -> None:
        """Cancel a scheduled job"""
        
        try:
            success = await job_scheduler.cancel_job(args.job_id)
            
            if success:
                print(f"SUCCESS: Cancelled job {args.job_id}")
            else:
                print(f"WARNING: Job {args.job_id} not found or already completed")
                
        except Exception as e:
            logger.error(f"Job cancellation failed: {e}")
            print(f"ERROR: {e}")
            sys.exit(1)
    
    def _load_entity_ids_from_file(self, file_path: str) -> List[str]:
        """Load entity IDs from file"""
        path = Path(file_path)
        
        if not path.exists():
            raise ValueError(f"Entity file not found: {file_path}")
        
        if path.suffix.lower() == '.json':
            with open(path) as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                elif 'entity_ids' in data:
                    return data['entity_ids']
                else:
                    raise ValueError("Invalid JSON format for entity IDs")
        else:
            # Assume text file with one ID per line
            with open(path) as f:
                return [line.strip() for line in f if line.strip()]
    
    async def _generate_predictions(self, run_id: str, entity_ids: List[str], model_version: str) -> List:
        """Generate mock predictions"""
        from backend_v2.app.backtest.schemas import PredictionSnapshot
        import numpy as np
        
        predictions = []
        
        for entity_id in entity_ids:
            prediction_value = np.random.randint(0, 2)
            positive_prob = np.random.random()
            
            pred = PredictionSnapshot(
                snapshot_id=f"pred_{run_id}_{entity_id}",
                backtest_run_id=run_id,
                entity_id=entity_id,
                prediction_value=prediction_value,
                prediction_proba={
                    "negative_class_prob": 1 - positive_prob,
                    "positive_class_prob": positive_prob
                },
                feature_values={
                    "sqft": np.random.normal(2000, 500),
                    "bedrooms": np.random.choice([2, 3, 4, 5]),
                    "median_price_zip": np.random.normal(400000, 100000)
                },
                model_version=model_version,
                created_at=datetime.now()
            )
            predictions.append(pred)
        
        return predictions
    
    async def _generate_cli_report(self, run_id: str, format: str):
        """Generate report from CLI"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"cli_report_{run_id}_{timestamp}.{format}"
        
        await report_renderer.generate_comprehensive_report(
            run_id=run_id,
            output_format=format,
            output_path=output_path
        )
        
        print(f"Report generated: {output_path}")
    
    async def _get_recent_runs(self, limit: int) -> List[Dict[str, Any]]:
        """Get recent backtest runs (mock implementation)"""
        # Mock data - in production would query database
        runs = []
        for i in range(min(limit, 10)):
            run_id = f"run_{i+1}_{int(datetime.now().timestamp())}"
            runs.append({
                "run_id": run_id,
                "run_name": f"Test Run {i+1}",
                "status": "completed",
                "created_at": (datetime.now() - timedelta(days=i)).isoformat(),
                "horizon_months": 6
            })
        return runs

def create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser"""
    
    parser = argparse.ArgumentParser(
        description="CapSight Backtest CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a simple backtest
  python -m backend_v2.app.backtest.jobs.cli run-backtest \\
    --name "Monthly Backtest" \\
    --model-version "v1.2.0" \\
    --horizon-months 6 \\
    --generate-report

  # Run replay analysis
  python -m backend_v2.app.backtest.jobs.cli replay \\
    --original-run-id "run_123" \\
    --scenario-name "Interest Rate +1%" \\
    --replay-mode "market_scenario" \\
    --scenario-params '{"interest_rate_change": 0.01}'

  # Generate uplift analysis
  python -m backend_v2.app.backtest.jobs.cli uplift \\
    --treatment-run-id "run_123" \\
    --baseline-strategy "random" \\
    --outcome-column "actual_success"

  # Schedule recurring backtest
  python -m backend_v2.app.backtest.jobs.cli schedule \\
    --job-name "Daily Backtest" \\
    --schedule-type "cron" \\
    --cron-expression "0 2 * * *" \\
    --job-type "standard_backtest"
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Run backtest command
    run_parser = subparsers.add_parser('run-backtest', help='Run a new backtest')
    run_parser.add_argument('--name', required=True, help='Backtest run name')
    run_parser.add_argument('--model-version', required=True, help='Model version to use')
    run_parser.add_argument('--prediction-date', help='Prediction date (YYYY-MM-DD)')
    run_parser.add_argument('--horizon-months', type=int, default=6, help='Forecast horizon in months')
    run_parser.add_argument('--entity-ids', nargs='*', help='Specific entity IDs to test')
    run_parser.add_argument('--entity-file', help='File containing entity IDs')
    run_parser.add_argument('--entity-count', type=int, default=100, help='Number of entities to test')
    run_parser.add_argument('--feature-views', nargs='*', 
                           default=['property_features', 'market_features'], 
                           help='Feature views to include')
    run_parser.add_argument('--generate-report', action='store_true', help='Generate report after completion')
    run_parser.add_argument('--report-format', default='html', choices=['html', 'pdf', 'markdown'], 
                           help='Report format')
    
    # Replay analysis command
    replay_parser = subparsers.add_parser('replay', help='Run replay analysis')
    replay_parser.add_argument('--original-run-id', required=True, help='Original run ID to replay')
    replay_parser.add_argument('--scenario-name', required=True, help='Replay scenario name')
    replay_parser.add_argument('--replay-mode', required=True, 
                              choices=['model_swap', 'parameter_change', 'feature_ablation', 'threshold_change', 'market_scenario'],
                              help='Replay mode')
    replay_parser.add_argument('--entity-ids', nargs='*', help='Specific entity IDs for replay')
    replay_parser.add_argument('--model-version', help='Model version for replay')
    replay_parser.add_argument('--scenario-params', help='Scenario parameters (JSON string)')
    replay_parser.add_argument('--feature-overrides', help='Feature overrides (JSON string)')
    replay_parser.add_argument('--threshold-overrides', help='Threshold overrides (JSON string)')
    replay_parser.add_argument('--generate-comparison', action='store_true', help='Generate comparison report')
    
    # Uplift analysis command
    uplift_parser = subparsers.add_parser('uplift', help='Run uplift analysis')
    uplift_parser.add_argument('--treatment-run-id', required=True, help='Treatment run ID')
    uplift_parser.add_argument('--baseline-strategy', default='random', 
                              choices=['random', 'always_invest', 'never_invest', 'market_average'],
                              help='Baseline strategy')
    uplift_parser.add_argument('--outcome-column', default='actual_success', 
                              choices=['actual_success', 'actual_appreciation', 'actual_rental_yield'],
                              help='Outcome column for analysis')
    uplift_parser.add_argument('--output-file', help='Save detailed results to file')
    
    # Generate report command
    report_parser = subparsers.add_parser('report', help='Generate report for existing run')
    report_parser.add_argument('--run-id', required=True, help='Run ID to generate report for')
    report_parser.add_argument('--format', default='html', choices=['html', 'pdf', 'markdown'], 
                              help='Report format')
    report_parser.add_argument('--output', help='Output file path')
    report_parser.add_argument('--include-charts', action='store_true', default=True, help='Include charts')
    report_parser.add_argument('--include-uplift', action='store_true', default=True, help='Include uplift analysis')
    report_parser.add_argument('--include-samples', action='store_true', default=True, help='Include sample predictions')
    report_parser.add_argument('--executive-summary', action='store_true', help='Print executive summary')
    
    # List runs command
    list_parser = subparsers.add_parser('list-runs', help='List backtest runs')
    list_parser.add_argument('--limit', type=int, default=20, help='Maximum number of runs to show')
    
    # Schedule job command
    schedule_parser = subparsers.add_parser('schedule', help='Schedule recurring backtest job')
    schedule_parser.add_argument('--job-name', required=True, help='Job name')
    schedule_parser.add_argument('--job-type', default='standard_backtest', 
                                choices=['standard_backtest', 'replay_analysis', 'uplift_analysis', 'model_comparison'],
                                help='Job type')
    schedule_parser.add_argument('--schedule-type', required=True, choices=['cron', 'interval'], help='Schedule type')
    schedule_parser.add_argument('--cron-expression', help='Cron expression (for cron schedule)')
    schedule_parser.add_argument('--interval-seconds', type=int, help='Interval in seconds (for interval schedule)')
    schedule_parser.add_argument('--model-version', required=True, help='Model version')
    schedule_parser.add_argument('--prediction-date', help='Prediction date (YYYY-MM-DD)')
    schedule_parser.add_argument('--horizon-months', type=int, default=6, help='Forecast horizon')
    schedule_parser.add_argument('--entity-ids', nargs='*', help='Entity IDs')
    schedule_parser.add_argument('--feature-config', help='Feature configuration (JSON string)')
    schedule_parser.add_argument('--feature-views', nargs='*', 
                                default=['property_features', 'market_features'],
                                help='Feature views')
    schedule_parser.add_argument('--generate-reports', action='store_true', help='Generate reports automatically')
    schedule_parser.add_argument('--notifications', help='Notification configuration (JSON string)')
    
    # List jobs command
    subparsers.add_parser('list-jobs', help='List scheduled jobs')
    
    # Cancel job command
    cancel_parser = subparsers.add_parser('cancel-job', help='Cancel scheduled job')
    cancel_parser.add_argument('--job-id', required=True, help='Job ID to cancel')
    
    return parser

async def main():
    """Main CLI entry point"""
    
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    cli = BacktestCLI()
    
    try:
        if args.command == 'run-backtest':
            await cli.run_backtest(args)
        elif args.command == 'replay':
            await cli.replay_analysis(args)
        elif args.command == 'uplift':
            await cli.uplift_analysis(args)
        elif args.command == 'report':
            await cli.generate_report(args)
        elif args.command == 'list-runs':
            await cli.list_runs(args)
        elif args.command == 'schedule':
            await cli.schedule_job(args)
        elif args.command == 'list-jobs':
            await cli.list_jobs(args)
        elif args.command == 'cancel-job':
            await cli.cancel_job(args)
        else:
            print(f"Unknown command: {args.command}")
            parser.print_help()
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"FATAL ERROR: {e}")
        sys.exit(1)

if __name__ == '__main__':
    # Import numpy here to avoid issues with CLI parsing
    import numpy as np
    asyncio.run(main())
