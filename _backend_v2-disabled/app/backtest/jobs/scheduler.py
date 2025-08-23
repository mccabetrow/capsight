"""
Backtest job scheduler and automation
Handles scheduling, monitoring, and orchestration of backtest runs
"""
import asyncio
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Callable
import json
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import logging
from pathlib import Path

# APScheduler for job scheduling
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.date import DateTrigger
    from apscheduler.jobstores.memory import MemoryJobStore
    from apscheduler.executors.asyncio import AsyncIOExecutor
except ImportError:
    class AsyncIOScheduler: pass
    class CronTrigger: pass
    class IntervalTrigger: pass
    class DateTrigger: pass

from ..config import config
from ..schemas import BacktestRun, BacktestSchedule, BacktestJobConfig
from ..data_access import BacktestDataAccess
from ..time_slicer import TimeSlicer, time_slicer
from ..feature_loader import FeatureLoader, feature_loader
from ..replay import ReplayEngine, replay_engine
from ..metrics import MetricsCalculator, metrics_calculator
from ..reports.renderer import ReportRenderer, report_renderer

class JobStatus(Enum):
    """Status of scheduled jobs"""
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class JobResult:
    """Result of a scheduled job"""
    job_id: str
    status: JobStatus
    start_time: datetime
    end_time: Optional[datetime]
    result_data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    run_id: Optional[str]

class BacktestJobScheduler:
    """Schedules and manages backtest jobs"""
    
    def __init__(
        self,
        data_access: Optional[BacktestDataAccess] = None,
        time_slicer: Optional[TimeSlicer] = None,
        feature_loader: Optional[FeatureLoader] = None,
        replay_engine: Optional[ReplayEngine] = None,
        metrics_calculator: Optional[MetricsCalculator] = None,
        report_renderer: Optional[ReportRenderer] = None
    ):
        self.data_access = data_access or BacktestDataAccess()
        self.time_slicer = time_slicer or globals()['time_slicer']
        self.feature_loader = feature_loader or globals()['feature_loader']
        self.replay_engine = replay_engine or globals()['replay_engine']
        self.metrics_calculator = metrics_calculator or globals()['metrics_calculator']
        self.report_renderer = report_renderer or globals()['report_renderer']
        
        # Setup scheduler
        self.scheduler = None
        self.job_results: Dict[str, JobResult] = {}
        self.active_jobs: Dict[str, asyncio.Task] = {}
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
    
    async def start_scheduler(self):
        """Start the job scheduler"""
        try:
            jobstores = {'default': MemoryJobStore()}
            executors = {'default': AsyncIOExecutor()}
            job_defaults = {
                'coalesce': False,
                'max_instances': 3,
                'misfire_grace_time': 300  # 5 minutes
            }
            
            self.scheduler = AsyncIOScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults,
                timezone='UTC'
            )
            
            self.scheduler.start()
            self.logger.info("Backtest scheduler started")
            
        except Exception as e:
            self.logger.error(f"Failed to start scheduler: {e}")
            # Fallback to simple scheduling
            self.scheduler = None
    
    async def stop_scheduler(self):
        """Stop the job scheduler"""
        if self.scheduler:
            self.scheduler.shutdown()
            self.logger.info("Backtest scheduler stopped")
        
        # Cancel active jobs
        for job_id, task in self.active_jobs.items():
            if not task.done():
                task.cancel()
                self.logger.info(f"Cancelled job {job_id}")
    
    async def schedule_recurring_backtest(
        self,
        schedule_config: BacktestSchedule,
        job_config: BacktestJobConfig
    ) -> str:
        """
        Schedule a recurring backtest job
        
        Args:
            schedule_config: Schedule configuration (cron, interval, etc.)
            job_config: Backtest job parameters
            
        Returns:
            Scheduled job ID
        """
        job_id = f"backtest_{uuid.uuid4().hex[:8]}"
        
        if self.scheduler:
            # Use APScheduler
            if schedule_config.schedule_type == "cron":
                trigger = CronTrigger.from_crontab(schedule_config.cron_expression)
            elif schedule_config.schedule_type == "interval":
                trigger = IntervalTrigger(
                    seconds=schedule_config.interval_seconds
                )
            else:
                raise ValueError(f"Unsupported schedule type: {schedule_config.schedule_type}")
            
            self.scheduler.add_job(
                func=self._execute_backtest_job,
                trigger=trigger,
                args=[job_id, job_config],
                id=job_id,
                name=f"Backtest: {job_config.job_name}",
                misfire_grace_time=300
            )
            
        else:
            # Fallback: simple periodic execution
            asyncio.create_task(
                self._simple_periodic_job(job_id, schedule_config, job_config)
            )
        
        self.logger.info(f"Scheduled recurring backtest job: {job_id}")
        return job_id
    
    async def schedule_one_time_backtest(
        self,
        run_date: datetime,
        job_config: BacktestJobConfig
    ) -> str:
        """Schedule a one-time backtest job"""
        
        job_id = f"backtest_once_{uuid.uuid4().hex[:8]}"
        
        if self.scheduler:
            trigger = DateTrigger(run_date=run_date)
            
            self.scheduler.add_job(
                func=self._execute_backtest_job,
                trigger=trigger,
                args=[job_id, job_config],
                id=job_id,
                name=f"One-time Backtest: {job_config.job_name}"
            )
        else:
            # Schedule for immediate or delayed execution
            delay = (run_date - datetime.now()).total_seconds()
            
            async def delayed_execution():
                if delay > 0:
                    await asyncio.sleep(delay)
                await self._execute_backtest_job(job_id, job_config)
            
            asyncio.create_task(delayed_execution())
        
        self.logger.info(f"Scheduled one-time backtest job: {job_id}")
        return job_id
    
    async def _execute_backtest_job(
        self,
        job_id: str,
        job_config: BacktestJobConfig
    ) -> JobResult:
        """Execute a backtest job"""
        
        start_time = datetime.now()
        
        # Initialize job result
        job_result = JobResult(
            job_id=job_id,
            status=JobStatus.RUNNING,
            start_time=start_time,
            end_time=None,
            result_data=None,
            error_message=None,
            run_id=None
        )
        
        self.job_results[job_id] = job_result
        
        try:
            self.logger.info(f"Starting backtest job: {job_id}")
            
            # Execute the backtest
            if job_config.job_type == "standard_backtest":
                result = await self._run_standard_backtest(job_config)
            elif job_config.job_type == "replay_analysis":
                result = await self._run_replay_analysis(job_config)
            elif job_config.job_type == "uplift_analysis":
                result = await self._run_uplift_analysis(job_config)
            elif job_config.job_type == "model_comparison":
                result = await self._run_model_comparison(job_config)
            else:
                raise ValueError(f"Unknown job type: {job_config.job_type}")
            
            # Update job result
            job_result.status = JobStatus.COMPLETED
            job_result.end_time = datetime.now()
            job_result.result_data = result
            job_result.run_id = result.get("run_id")
            
            self.logger.info(f"Completed backtest job: {job_id}")
            
            # Generate reports if requested
            if job_config.generate_reports:
                await self._generate_scheduled_reports(job_result)
            
            # Send notifications if configured
            if job_config.notifications:
                await self._send_job_notifications(job_result, job_config.notifications)
            
        except Exception as e:
            job_result.status = JobStatus.FAILED
            job_result.end_time = datetime.now()
            job_result.error_message = str(e)
            
            self.logger.error(f"Backtest job {job_id} failed: {e}")
        
        return job_result
    
    async def _run_standard_backtest(self, job_config: BacktestJobConfig) -> Dict[str, Any]:
        """Run a standard backtest"""
        
        # Generate time window
        prediction_date = job_config.prediction_date or date.today()
        time_window = self.time_slicer.asof_window(
            asof_date=prediction_date,
            horizon_months=job_config.horizon_months or 6
        )
        
        # Create backtest run
        run_id = f"scheduled_{job_config.job_name}_{int(datetime.now().timestamp())}"
        backtest_run = BacktestRun(
            run_id=run_id,
            run_name=job_config.job_name,
            created_at=datetime.now(),
            prediction_date=datetime.combine(prediction_date, datetime.min.time()),
            horizon_months=job_config.horizon_months or 6,
            model_version=job_config.model_version,
            feature_set=job_config.feature_config or {},
            status="running",
            config=asdict(job_config)
        )
        
        await self.data_access.create_backtest_run(backtest_run)
        
        # Load features and generate predictions (mock implementation)
        entity_ids = job_config.entity_ids or await self._get_default_entity_ids()
        
        feature_data = await self.feature_loader.create_training_dataset(
            entity_ids=entity_ids,
            training_window=time_window,
            feature_views=job_config.feature_views or ["property_features", "market_features"]
        )
        
        # Generate mock predictions
        predictions = await self._generate_mock_predictions(
            run_id, entity_ids, job_config.model_version
        )
        
        # Save predictions
        for pred in predictions:
            await self.data_access.create_prediction_snapshot(pred)
        
        # Update run status
        backtest_run.status = "completed"
        await self.data_access.update_backtest_run(backtest_run)
        
        return {
            "run_id": run_id,
            "prediction_count": len(predictions),
            "status": "completed"
        }
    
    async def _run_replay_analysis(self, job_config: BacktestJobConfig) -> Dict[str, Any]:
        """Run replay analysis"""
        
        if not job_config.parent_run_id:
            raise ValueError("Parent run ID required for replay analysis")
        
        # Create replay scenario
        from ..schemas import ReplayScenario
        replay_scenario = ReplayScenario(
            scenario_name=job_config.job_name,
            replay_mode=job_config.replay_mode or "model_swap",
            entity_ids=job_config.entity_ids,
            model_version=job_config.model_version,
            scenario_params=job_config.scenario_params or {},
            feature_overrides=job_config.feature_overrides,
            threshold_overrides=job_config.threshold_overrides
        )
        
        # Execute replay
        replay_run = await self.replay_engine.replay_historical_predictions(
            original_run_id=job_config.parent_run_id,
            replay_scenario=replay_scenario
        )
        
        return {
            "run_id": replay_run.run_id,
            "original_run_id": job_config.parent_run_id,
            "replay_mode": job_config.replay_mode,
            "status": "completed"
        }
    
    async def _run_uplift_analysis(self, job_config: BacktestJobConfig) -> Dict[str, Any]:
        """Run uplift analysis"""
        
        if not job_config.parent_run_id:
            raise ValueError("Parent run ID required for uplift analysis")
        
        uplift_report = await self.uplift_analyzer.generate_uplift_report(
            treatment_run_id=job_config.parent_run_id,
            baseline_strategy=job_config.baseline_strategy or "random",
            outcome_column=job_config.outcome_column or "actual_success"
        )
        
        return {
            "treatment_run_id": job_config.parent_run_id,
            "uplift_report": uplift_report,
            "status": "completed"
        }
    
    async def _run_model_comparison(self, job_config: BacktestJobConfig) -> Dict[str, Any]:
        """Run model comparison analysis"""
        
        if not job_config.model_versions or len(job_config.model_versions) < 2:
            raise ValueError("At least 2 model versions required for comparison")
        
        comparison_results = {}
        
        for model_version in job_config.model_versions:
            # Create job config for each model
            model_job_config = BacktestJobConfig(
                job_name=f"{job_config.job_name}_{model_version}",
                job_type="standard_backtest",
                model_version=model_version,
                prediction_date=job_config.prediction_date,
                horizon_months=job_config.horizon_months,
                entity_ids=job_config.entity_ids,
                feature_config=job_config.feature_config,
                feature_views=job_config.feature_views
            )
            
            # Run backtest for this model
            result = await self._run_standard_backtest(model_job_config)
            comparison_results[model_version] = result
        
        return {
            "comparison_type": "model_comparison",
            "model_versions": job_config.model_versions,
            "results": comparison_results,
            "status": "completed"
        }
    
    async def _simple_periodic_job(
        self,
        job_id: str,
        schedule_config: BacktestSchedule,
        job_config: BacktestJobConfig
    ):
        """Simple periodic job execution (fallback)"""
        
        interval_seconds = schedule_config.interval_seconds or 3600  # Default 1 hour
        
        while True:
            try:
                await asyncio.sleep(interval_seconds)
                await self._execute_backtest_job(job_id, job_config)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Periodic job {job_id} failed: {e}")
    
    async def _get_default_entity_ids(self) -> List[str]:
        """Get default entity IDs for backtesting"""
        # Mock implementation - in production would query database
        return [f"property_{i}" for i in range(1, 101)]  # 100 properties
    
    async def _generate_mock_predictions(
        self,
        run_id: str,
        entity_ids: List[str],
        model_version: str
    ) -> List:
        """Generate mock predictions for testing"""
        from ..schemas import PredictionSnapshot
        
        predictions = []
        
        for entity_id in entity_ids:
            # Mock prediction values
            prediction_value = np.random.randint(0, 2)  # Binary classification
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
    
    async def _generate_scheduled_reports(self, job_result: JobResult):
        """Generate reports for completed job"""
        
        if not job_result.run_id or job_result.status != JobStatus.COMPLETED:
            return
        
        try:
            # Generate HTML report
            html_report_path = f"reports/{job_result.run_id}_report.html"
            await self.report_renderer.generate_comprehensive_report(
                run_id=job_result.run_id,
                output_format="html",
                output_path=html_report_path
            )
            
            # Generate executive summary
            summary = await self.report_renderer.generate_executive_summary(
                run_id=job_result.run_id,
                target_audience="executive"
            )
            
            self.logger.info(f"Generated reports for job {job_result.job_id}")
            
        except Exception as e:
            self.logger.error(f"Report generation failed for job {job_result.job_id}: {e}")
    
    async def _send_job_notifications(
        self,
        job_result: JobResult,
        notification_config: Dict[str, Any]
    ):
        """Send notifications for job completion"""
        
        try:
            # Mock notification sending
            if notification_config.get("email"):
                self.logger.info(f"Sending email notification for job {job_result.job_id}")
                # In production: send actual email
            
            if notification_config.get("slack"):
                self.logger.info(f"Sending Slack notification for job {job_result.job_id}")
                # In production: send Slack message
            
            if notification_config.get("webhook"):
                self.logger.info(f"Sending webhook notification for job {job_result.job_id}")
                # In production: send HTTP webhook
                
        except Exception as e:
            self.logger.error(f"Notification failed for job {job_result.job_id}: {e}")
    
    async def get_job_status(self, job_id: str) -> Optional[JobResult]:
        """Get status of a scheduled job"""
        return self.job_results.get(job_id)
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a scheduled job"""
        
        if self.scheduler and self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            self.logger.info(f"Cancelled scheduled job: {job_id}")
            return True
        
        # Cancel active task if running
        if job_id in self.active_jobs:
            task = self.active_jobs[job_id]
            if not task.done():
                task.cancel()
                
                # Update job result
                if job_id in self.job_results:
                    self.job_results[job_id].status = JobStatus.CANCELLED
                    self.job_results[job_id].end_time = datetime.now()
                
                self.logger.info(f"Cancelled running job: {job_id}")
                return True
        
        return False
    
    async def list_scheduled_jobs(self) -> List[Dict[str, Any]]:
        """List all scheduled jobs"""
        
        jobs = []
        
        if self.scheduler:
            for job in self.scheduler.get_jobs():
                jobs.append({
                    "job_id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger)
                })
        
        # Add job results
        for job_id, result in self.job_results.items():
            job_info = next((j for j in jobs if j["job_id"] == job_id), {})
            job_info.update({
                "job_id": job_id,
                "status": result.status.value,
                "start_time": result.start_time.isoformat(),
                "end_time": result.end_time.isoformat() if result.end_time else None,
                "run_id": result.run_id
            })
            
            if job_info not in jobs:
                jobs.append(job_info)
        
        return jobs
    
    async def cleanup_old_jobs(self, max_age_days: int = 30):
        """Clean up old job results"""
        
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        jobs_to_remove = []
        for job_id, result in self.job_results.items():
            if result.start_time < cutoff_date:
                jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            del self.job_results[job_id]
            self.logger.info(f"Cleaned up old job result: {job_id}")
    
    async def export_job_history(self, output_path: str):
        """Export job history to JSON file"""
        
        history = []
        for job_id, result in self.job_results.items():
            history.append({
                "job_id": job_id,
                "status": result.status.value,
                "start_time": result.start_time.isoformat(),
                "end_time": result.end_time.isoformat() if result.end_time else None,
                "run_id": result.run_id,
                "error_message": result.error_message,
                "result_data": result.result_data
            })
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(history, f, indent=2)
        
        self.logger.info(f"Exported job history to {output_path}")

# Global instance
job_scheduler = BacktestJobScheduler()

# Helper function to start scheduler
async def start_backtest_scheduler():
    """Start the global backtest scheduler"""
    await job_scheduler.start_scheduler()

# Helper function to stop scheduler
async def stop_backtest_scheduler():
    """Stop the global backtest scheduler"""
    await job_scheduler.stop_scheduler()
