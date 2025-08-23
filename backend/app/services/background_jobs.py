"""
Background Jobs & Scheduled Tasks
APScheduler integration for monitoring and maintenance tasks
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
import json

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.services.business_metrics import business_metrics
from app.services.anomaly_detection import monitoring_job
from app.services.alerting import alert_manager, Alert, AlertSeverity
from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

class BackgroundJobManager:
    """Manage all background jobs and scheduled tasks"""
    
    def __init__(self):
        # Configure scheduler
        jobstores = {
            'default': MemoryJobStore(),
        }
        executors = {
            'default': AsyncIOExecutor(),
        }
        job_defaults = {
            'coalesce': False,
            'max_instances': 1
        }
        
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )
        
        self.job_status: Dict[str, Dict[str, Any]] = {}
        self.is_running = False
    
    def start_scheduler(self):
        """Start the background scheduler"""
        if not self.is_running:
            try:
                self.scheduler.start()
                self.is_running = True
                logger.info("Background job scheduler started")
                
                # Schedule all jobs
                self._schedule_monitoring_jobs()
                self._schedule_maintenance_jobs()
                self._schedule_business_jobs()
                
            except Exception as e:
                logger.error(f"Failed to start scheduler: {e}")
                raise
    
    def shutdown_scheduler(self):
        """Shutdown the background scheduler"""
        if self.is_running:
            try:
                self.scheduler.shutdown()
                self.is_running = False
                logger.info("Background job scheduler stopped")
            except Exception as e:
                logger.error(f"Error stopping scheduler: {e}")
    
    def _schedule_monitoring_jobs(self):
        """Schedule monitoring and anomaly detection jobs"""
        
        # Anomaly detection - every 15 minutes
        self.scheduler.add_job(
            func=self._run_anomaly_detection,
            trigger=IntervalTrigger(minutes=15),
            id='anomaly_detection',
            name='Anomaly Detection',
            replace_existing=True
        )
        
        # Model drift detection - every 2 hours
        self.scheduler.add_job(
            func=self._run_drift_detection,
            trigger=IntervalTrigger(hours=2),
            id='drift_detection',
            name='Model Drift Detection',
            replace_existing=True
        )
        
        # System health check - every 5 minutes
        self.scheduler.add_job(
            func=self._run_health_check,
            trigger=IntervalTrigger(minutes=5),
            id='health_check',
            name='System Health Check',
            replace_existing=True
        )
        
        # Business metrics collection - every hour
        self.scheduler.add_job(
            func=self._collect_business_metrics,
            trigger=IntervalTrigger(hours=1),
            id='business_metrics',
            name='Business Metrics Collection',
            replace_existing=True
        )
    
    def _schedule_maintenance_jobs(self):
        """Schedule maintenance and cleanup jobs"""
        
        # Database cleanup - daily at 2 AM
        self.scheduler.add_job(
            func=self._run_database_cleanup,
            trigger=CronTrigger(hour=2, minute=0),
            id='database_cleanup',
            name='Database Cleanup',
            replace_existing=True
        )
        
        # Log rotation - daily at 3 AM
        self.scheduler.add_job(
            func=self._rotate_logs,
            trigger=CronTrigger(hour=3, minute=0),
            id='log_rotation',
            name='Log Rotation',
            replace_existing=True
        )
        
        # Cache cleanup - every 6 hours
        self.scheduler.add_job(
            func=self._cleanup_cache,
            trigger=IntervalTrigger(hours=6),
            id='cache_cleanup',
            name='Cache Cleanup',
            replace_existing=True
        )
        
        # Model performance validation - daily at 4 AM
        self.scheduler.add_job(
            func=self._validate_model_performance,
            trigger=CronTrigger(hour=4, minute=0),
            id='model_validation',
            name='Model Performance Validation',
            replace_existing=True
        )
    
    def _schedule_business_jobs(self):
        """Schedule business-specific jobs"""
        
        # Daily business report - daily at 6 AM
        self.scheduler.add_job(
            func=self._generate_daily_report,
            trigger=CronTrigger(hour=6, minute=0),
            id='daily_business_report',
            name='Daily Business Report',
            replace_existing=True
        )
        
        # Weekly summary - Mondays at 7 AM
        self.scheduler.add_job(
            func=self._generate_weekly_summary,
            trigger=CronTrigger(day_of_week=0, hour=7, minute=0),
            id='weekly_summary',
            name='Weekly Business Summary',
            replace_existing=True
        )
        
        # Market data sync - every 4 hours during business hours
        for hour in [8, 12, 16, 20]:  # 8 AM, 12 PM, 4 PM, 8 PM
            self.scheduler.add_job(
                func=self._sync_market_data,
                trigger=CronTrigger(hour=hour, minute=0),
                id=f'market_sync_{hour}',
                name=f'Market Data Sync {hour}:00',
                replace_existing=True
            )
    
    async def _run_anomaly_detection(self):
        """Run anomaly detection job"""
        job_id = 'anomaly_detection'
        try:
            self._update_job_status(job_id, 'running', 'Starting anomaly detection')
            
            await monitoring_job.run_anomaly_detection()
            
            self._update_job_status(job_id, 'completed', 'Anomaly detection completed successfully')
            
        except Exception as e:
            error_msg = f"Anomaly detection failed: {str(e)}"
            self._update_job_status(job_id, 'failed', error_msg)
            logger.error(error_msg)
            
            # Send alert about job failure
            alert = Alert(
                title="Background Job Failed",
                message=f"Anomaly detection job failed: {str(e)}",
                severity=AlertSeverity.MEDIUM,
                source="background_jobs",
                details={"job_id": job_id, "error": str(e)},
                tags=["job_failure", "anomaly_detection"]
            )
            await alert_manager.send_alert(alert)
    
    async def _run_drift_detection(self):
        """Run model drift detection job"""
        job_id = 'drift_detection'
        try:
            self._update_job_status(job_id, 'running', 'Starting drift detection')
            
            await monitoring_job.run_drift_detection()
            
            self._update_job_status(job_id, 'completed', 'Drift detection completed successfully')
            
        except Exception as e:
            error_msg = f"Drift detection failed: {str(e)}"
            self._update_job_status(job_id, 'failed', error_msg)
            logger.error(error_msg)
    
    async def _run_health_check(self):
        """Run system health check"""
        job_id = 'health_check'
        try:
            self._update_job_status(job_id, 'running', 'Running health check')
            
            # Collect basic health metrics
            metrics = await business_metrics.collector.collect_metrics()
            
            # Check for critical issues
            critical_issues = []
            
            if metrics.error_rate_24h > 5.0:
                critical_issues.append(f"High error rate: {metrics.error_rate_24h:.1f}%")
            
            if metrics.system_uptime < 95.0:
                critical_issues.append(f"Low uptime: {metrics.system_uptime:.1f}%")
            
            if metrics.daily_predictions < 5:
                critical_issues.append(f"Very low prediction volume: {metrics.daily_predictions}")
            
            # Send alerts for critical issues
            if critical_issues:
                alert = Alert(
                    title="System Health Alert",
                    message=f"Critical issues detected: {'; '.join(critical_issues)}",
                    severity=AlertSeverity.HIGH,
                    source="health_check",
                    details={"issues": critical_issues, "uptime": metrics.system_uptime},
                    tags=["health", "critical"]
                )
                await alert_manager.send_alert(alert)
            
            status_msg = f"Health check completed. Issues: {len(critical_issues)}"
            self._update_job_status(job_id, 'completed', status_msg)
            
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            self._update_job_status(job_id, 'failed', error_msg)
            logger.error(error_msg)
    
    async def _collect_business_metrics(self):
        """Collect and store business metrics"""
        job_id = 'business_metrics'
        try:
            self._update_job_status(job_id, 'running', 'Collecting business metrics')
            
            # Collect metrics
            metrics = await business_metrics.collector.collect_metrics()
            
            # Store metrics (implement metrics storage if needed)
            # For now, just log key metrics
            logger.info(f"Business Metrics - Predictions: {metrics.daily_predictions}, "
                       f"DAU: {metrics.daily_active_users}, "
                       f"Avg Value: ${metrics.avg_prediction_value:,.0f}")
            
            self._update_job_status(job_id, 'completed', 
                                  f'Metrics collected: {metrics.daily_predictions} predictions today')
            
        except Exception as e:
            error_msg = f"Business metrics collection failed: {str(e)}"
            self._update_job_status(job_id, 'failed', error_msg)
            logger.error(error_msg)
    
    async def _run_database_cleanup(self):
        """Clean up old database records"""
        job_id = 'database_cleanup'
        try:
            self._update_job_status(job_id, 'running', 'Starting database cleanup')
            
            # Mock cleanup - implement actual cleanup logic
            await asyncio.sleep(1)  # Simulate cleanup work
            
            cleanup_summary = {
                "old_logs_deleted": 0,
                "temp_files_cleaned": 0,
                "cache_entries_removed": 0
            }
            
            self._update_job_status(job_id, 'completed', 
                                  f'Database cleanup completed: {json.dumps(cleanup_summary)}')
            
        except Exception as e:
            error_msg = f"Database cleanup failed: {str(e)}"
            self._update_job_status(job_id, 'failed', error_msg)
            logger.error(error_msg)
    
    async def _rotate_logs(self):
        """Rotate application logs"""
        job_id = 'log_rotation'
        try:
            self._update_job_status(job_id, 'running', 'Rotating logs')
            
            # Mock log rotation - implement actual log rotation
            await asyncio.sleep(1)
            
            self._update_job_status(job_id, 'completed', 'Log rotation completed')
            
        except Exception as e:
            error_msg = f"Log rotation failed: {str(e)}"
            self._update_job_status(job_id, 'failed', error_msg)
            logger.error(error_msg)
    
    async def _cleanup_cache(self):
        """Clean up expired cache entries"""
        job_id = 'cache_cleanup'
        try:
            self._update_job_status(job_id, 'running', 'Cleaning cache')
            
            # Mock cache cleanup - implement Redis cache cleanup
            await asyncio.sleep(1)
            
            self._update_job_status(job_id, 'completed', 'Cache cleanup completed')
            
        except Exception as e:
            error_msg = f"Cache cleanup failed: {str(e)}"
            self._update_job_status(job_id, 'failed', error_msg)
            logger.error(error_msg)
    
    async def _validate_model_performance(self):
        """Validate model performance against benchmarks"""
        job_id = 'model_validation'
        try:
            self._update_job_status(job_id, 'running', 'Validating model performance')
            
            # Collect performance metrics
            metrics = await business_metrics.collector.collect_metrics()
            
            # Check performance thresholds
            performance_alerts = []
            
            if metrics.avg_confidence_score < 0.7:
                performance_alerts.append("Low average confidence score")
            
            if metrics.model_accuracy_mae and metrics.model_accuracy_mae > 100000:
                performance_alerts.append("High MAE indicating poor accuracy")
            
            # Send performance alerts
            if performance_alerts:
                alert = Alert(
                    title="Model Performance Alert",
                    message=f"Performance issues detected: {'; '.join(performance_alerts)}",
                    severity=AlertSeverity.MEDIUM,
                    source="model_validation",
                    details={
                        "avg_confidence": metrics.avg_confidence_score,
                        "mae": metrics.model_accuracy_mae,
                        "alerts": performance_alerts
                    },
                    tags=["model", "performance", "validation"]
                )
                await alert_manager.send_alert(alert)
            
            status_msg = f"Model validation completed. Issues: {len(performance_alerts)}"
            self._update_job_status(job_id, 'completed', status_msg)
            
        except Exception as e:
            error_msg = f"Model validation failed: {str(e)}"
            self._update_job_status(job_id, 'failed', error_msg)
            logger.error(error_msg)
    
    async def _generate_daily_report(self):
        """Generate daily business report"""
        job_id = 'daily_business_report'
        try:
            self._update_job_status(job_id, 'running', 'Generating daily report')
            
            # Generate report
            metrics = await business_metrics.get_kpi_summary()
            
            # Send summary alert/notification
            alert = Alert(
                title="Daily Business Report",
                message=f"Daily Summary - Predictions: {metrics['summary']['daily_predictions']}, "
                       f"DAU: {metrics['summary']['daily_active_users']}, "
                       f"Avg Value: ${metrics['summary']['avg_prediction_value']:,.0f}",
                severity=AlertSeverity.INFO,
                source="daily_report",
                details=metrics,
                tags=["report", "daily", "business"]
            )
            await alert_manager.send_alert(alert)
            
            self._update_job_status(job_id, 'completed', 'Daily report sent')
            
        except Exception as e:
            error_msg = f"Daily report generation failed: {str(e)}"
            self._update_job_status(job_id, 'failed', error_msg)
            logger.error(error_msg)
    
    async def _generate_weekly_summary(self):
        """Generate weekly business summary"""
        job_id = 'weekly_summary'
        try:
            self._update_job_status(job_id, 'running', 'Generating weekly summary')
            
            # Mock weekly summary generation
            await asyncio.sleep(1)
            
            self._update_job_status(job_id, 'completed', 'Weekly summary generated')
            
        except Exception as e:
            error_msg = f"Weekly summary generation failed: {str(e)}"
            self._update_job_status(job_id, 'failed', error_msg)
            logger.error(error_msg)
    
    async def _sync_market_data(self):
        """Sync market data from external sources"""
        job_id = 'market_sync'
        try:
            self._update_job_status(job_id, 'running', 'Syncing market data')
            
            # Mock market data sync
            await asyncio.sleep(2)
            
            self._update_job_status(job_id, 'completed', 'Market data sync completed')
            
        except Exception as e:
            error_msg = f"Market data sync failed: {str(e)}"
            self._update_job_status(job_id, 'failed', error_msg)
            logger.error(error_msg)
    
    def _update_job_status(self, job_id: str, status: str, message: str):
        """Update job status tracking"""
        self.job_status[job_id] = {
            'status': status,
            'message': message,
            'last_update': datetime.utcnow(),
            'last_run': datetime.utcnow() if status == 'completed' else 
                       self.job_status.get(job_id, {}).get('last_run')
        }
    
    def get_job_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all background jobs"""
        return self.job_status.copy()
    
    def get_scheduler_info(self) -> Dict[str, Any]:
        """Get scheduler information"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        
        return {
            'is_running': self.is_running,
            'total_jobs': len(jobs),
            'jobs': jobs
        }

# Global job manager instance
job_manager = BackgroundJobManager()

# Startup and shutdown handlers
async def startup_background_jobs():
    """Start background jobs on application startup"""
    try:
        job_manager.start_scheduler()
        logger.info("Background jobs started successfully")
    except Exception as e:
        logger.error(f"Failed to start background jobs: {e}")
        raise

async def shutdown_background_jobs():
    """Stop background jobs on application shutdown"""
    try:
        job_manager.shutdown_scheduler()
        logger.info("Background jobs stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping background jobs: {e}")
