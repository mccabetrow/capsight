#!/usr/bin/env python3
"""
CapSight Production Scheduler Setup

Sets up automated backtesting schedules for production use:
1. Nightly health checks (quick validation)
2. Weekly full backtests (comprehensive validation)
3. Monthly prospect proof pack generation
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent / "backend_v2"))

try:
    from app.backtest import BacktestConfig
    from app.backtest.jobs.scheduler import BacktestScheduler
    from app.backtest.data_access import BacktestDataAccess
    from app.backtest.schemas import JobConfig, ScheduleType
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure backend_v2 is set up correctly")
    sys.exit(1)


class ProductionScheduler:
    """Setup production scheduling for CapSight backtests."""
    
    def __init__(self):
        self.data_access = BacktestDataAccess()
        self.scheduler = BacktestScheduler(self.data_access)
        self.jobs_config = self._create_job_configs()
    
    def _create_job_configs(self):
        """Create standard job configurations."""
        
        # Nightly health check - quick validation
        nightly_config = BacktestConfig(
            name="nightly_health_check",
            model_version="v2.1.0",
            start_date=datetime.now() - timedelta(days=7),  # Last week
            end_date=datetime.now() - timedelta(days=1),    # Yesterday
            time_slice_hours=24,
            feature_sets=["property_features", "market_features"],
            prediction_targets=["price_change", "investment_score"],
            metrics=["accuracy", "roc_auc"],
            sla_max_runtime_minutes=30  # Quick check
        )
        
        # Weekly comprehensive backtest
        weekly_config = BacktestConfig(
            name="weekly_comprehensive_validation",
            model_version="v2.1.0",
            start_date=datetime.now() - timedelta(days=90),  # Last 90 days
            end_date=datetime.now() - timedelta(days=1),
            time_slice_hours=24,
            feature_sets=["property_features", "market_features", "neighborhood_features"],
            prediction_targets=["price_change", "investment_score", "days_on_market"],
            metrics=["accuracy", "precision", "recall", "roc_auc", "sharpe_ratio", "max_drawdown"],
            sla_max_runtime_minutes=180  # Full analysis
        )
        
        # Monthly market analysis
        monthly_config = BacktestConfig(
            name="monthly_market_analysis",
            model_version="v2.1.0", 
            start_date=datetime.now() - timedelta(days=365),  # Full year
            end_date=datetime.now() - timedelta(days=1),
            time_slice_hours=24,
            feature_sets=["property_features", "market_features", "neighborhood_features", "economic_indicators"],
            prediction_targets=["price_change", "investment_score", "days_on_market", "cap_rate"],
            metrics=["accuracy", "precision", "recall", "roc_auc", "sharpe_ratio", "max_drawdown"],
            sla_max_runtime_minutes=300,  # Comprehensive
            parallel_workers=8
        )
        
        return {
            'nightly_health': JobConfig(
                name="nightly_health_check",
                schedule_type=ScheduleType.DAILY,
                schedule_params={"hour": 2, "minute": 15},  # 2:15 AM
                backtest_config=nightly_config.dict(),
                enabled=True,
                retry_on_failure=True,
                max_retries=3
            ),
            'weekly_validation': JobConfig(
                name="weekly_comprehensive_validation", 
                schedule_type=ScheduleType.WEEKLY,
                schedule_params={"day_of_week": 6, "hour": 3, "minute": 0},  # Saturday 3:00 AM
                backtest_config=weekly_config.dict(),
                enabled=True,
                retry_on_failure=True,
                max_retries=2
            ),
            'monthly_analysis': JobConfig(
                name="monthly_market_analysis",
                schedule_type=ScheduleType.MONTHLY,
                schedule_params={"day": 1, "hour": 1, "minute": 0},  # 1st of month, 1:00 AM
                backtest_config=monthly_config.dict(),
                enabled=True,
                retry_on_failure=True,
                max_retries=1
            )
        }
    
    async def setup_production_schedule(self):
        """Setup all production schedules."""
        print("🗓️  Setting up CapSight production schedules...")
        
        try:
            # Start scheduler
            await self.scheduler.start()
            print("✅ Scheduler started")
            
            scheduled_jobs = []
            
            for job_name, job_config in self.jobs_config.items():
                try:
                    job_id = await self.scheduler.schedule_backtest(job_config)
                    scheduled_jobs.append({
                        'name': job_name,
                        'id': job_id,
                        'config': job_config
                    })
                    print(f"✅ Scheduled: {job_name} (ID: {job_id})")
                    
                except Exception as e:
                    print(f"❌ Failed to schedule {job_name}: {str(e)}")
            
            # List all jobs
            all_jobs = await self.scheduler.list_jobs()
            print(f"\n📋 Total scheduled jobs: {len(all_jobs)}")
            
            for job in all_jobs:
                print(f"   • {job.get('name', 'Unknown')} - Next run: {job.get('next_run_time', 'Unknown')}")
            
            # Save schedule summary
            schedule_summary = {
                'setup_time': datetime.now().isoformat(),
                'scheduled_jobs': scheduled_jobs,
                'total_jobs': len(all_jobs)
            }
            
            with open('production_schedule_summary.json', 'w') as f:
                json.dump(schedule_summary, f, indent=2, default=str)
            
            print(f"\n💾 Schedule summary saved to: production_schedule_summary.json")
            
            # Print next steps
            self._print_next_steps()
            
            return scheduled_jobs
            
        except Exception as e:
            print(f"❌ Failed to setup production schedule: {str(e)}")
            raise
    
    def _print_next_steps(self):
        """Print next steps for production setup."""
        print(f"\n🚀 PRODUCTION SETUP COMPLETE")
        print("=" * 50)
        
        print(f"\n📅 Scheduled Jobs:")
        print(f"   • Nightly Health Check: Every day at 2:15 AM")
        print(f"   • Weekly Validation: Every Saturday at 3:00 AM") 
        print(f"   • Monthly Analysis: 1st of each month at 1:00 AM")
        
        print(f"\n🔧 Management Commands:")
        print(f"   # List all jobs")
        print(f"   python -m app.backtest.jobs.cli list-jobs")
        
        print(f"\n   # Check job status")
        print(f"   python -m app.backtest.jobs.cli job-status --job-id <JOB_ID>")
        
        print(f"\n   # Cancel a job")
        print(f"   python -m app.backtest.jobs.cli cancel-job --job-id <JOB_ID>")
        
        print(f"\n   # Manual backtest")
        print(f"   python -m app.backtest.jobs.cli run-backtest --name 'manual_test'")
        
        print(f"\n📊 Monitoring:")
        print(f"   • Grafana Dashboard: Import backtest_dashboard.json")
        print(f"   • Prometheus Metrics: http://localhost:8000/metrics")
        print(f"   • Job Logs: Check scheduler logs for execution details")
        
        print(f"\n📧 Prospect Generation:")
        print(f"   # Generate proof pack from any backtest")
        print(f"   python generate_proof_pack.py --run-id <RUN_ID> --prospect 'Client Name'")
        
        print(f"\n⚡ ROI Calculator (for sales calls):")
        print(f"   Estimated value = Deals/yr × Avg EV × (bps improvement / 10,000)")
        print(f"   Example: 20 deals × $12M × 40 bps ≈ $960k/year value creation")


async def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("CapSight Production Scheduler Setup")
        print("\nUsage: python setup_production_schedule.py")
        print("\nSets up automated backtesting schedules:")
        print("• Nightly health checks (2:15 AM)")
        print("• Weekly full validation (Saturday 3:00 AM)")
        print("• Monthly comprehensive analysis (1st @ 1:00 AM)")
        return
    
    scheduler = ProductionScheduler()
    
    try:
        scheduled_jobs = await scheduler.setup_production_schedule()
        print(f"\n🎉 SUCCESS: {len(scheduled_jobs)} jobs scheduled for production")
        
    except Exception as e:
        print(f"\n❌ FAILED: {str(e)}")
        print("\nTroubleshooting:")
        print("• Ensure database is accessible")
        print("• Check if Redis is running (for job persistence)")
        print("• Verify backend_v2 module is properly configured")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
