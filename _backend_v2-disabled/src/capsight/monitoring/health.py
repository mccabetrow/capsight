"""
Comprehensive monitoring and health checking system for CapSight
Tracks accuracy, freshness, drift, and system health
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum

from ..core.config import settings, ACCURACY_ALERTS, FRESHNESS_ALERTS
from ..core.utils import logger, METRICS, HealthCheck, calculate_data_freshness_score

# Mock imports
try:
    import numpy as np
    import pandas as pd
    from prometheus_client import Gauge, Counter, Histogram
except ImportError:
    pass


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class AccuracyMetric:
    """Accuracy tracking metric"""
    metric_name: str
    current_value: float
    threshold: float
    timestamp: datetime
    model_name: str
    is_breach: bool = False


@dataclass
class FreshnessMetric:
    """Data freshness tracking metric"""
    source_name: str
    last_update: datetime
    age_seconds: float
    threshold_seconds: float
    is_stale: bool = False


@dataclass
class DriftAlert:
    """Model drift detection alert"""
    model_name: str
    feature_name: str
    drift_score: float
    threshold: float
    severity: str  # "low", "medium", "high"
    timestamp: datetime


class AccuracyMonitor:
    """Monitors model accuracy against SLA thresholds"""
    
    def __init__(self):
        self.accuracy_history: Dict[str, List[AccuracyMetric]] = {}
        self.breach_counts: Dict[str, int] = {}
    
    async def record_accuracy(self, model_name: str, metric_name: str, value: float) -> Optional[AccuracyMetric]:
        """Record accuracy metric and check for SLA breaches"""
        
        # Get threshold for metric
        threshold_map = {
            "caprate_mae_bps": ACCURACY_ALERTS["caprate_mae_breach"],
            "noi_mape_percent": ACCURACY_ALERTS["noi_mape_breach"],
            "arbitrage_top_decile_precision": settings.accuracy_targets.arbitrage_top_decile_precision,
            "confidence_calibration": ACCURACY_ALERTS["confidence_miscalibration"]
        }
        
        threshold = threshold_map.get(metric_name, 0.0)
        is_breach = False
        
        # Check for breach (higher is worse for MAE/MAPE, lower is worse for precision)
        if metric_name in ["caprate_mae_bps", "noi_mape_percent", "confidence_calibration"]:
            is_breach = value > threshold
        else:
            is_breach = value < threshold
        
        # Create metric record
        metric = AccuracyMetric(
            metric_name=metric_name,
            current_value=value,
            threshold=threshold,
            timestamp=datetime.now(timezone.utc),
            model_name=model_name,
            is_breach=is_breach
        )
        
        # Store in history
        key = f"{model_name}_{metric_name}"
        if key not in self.accuracy_history:
            self.accuracy_history[key] = []
        
        self.accuracy_history[key].append(metric)
        
        # Keep only last 100 measurements
        self.accuracy_history[key] = self.accuracy_history[key][-100:]
        
        # Update Prometheus metrics
        METRICS["model_accuracy"].labels(
            model_name=model_name,
            metric_type=metric_name
        ).set(value)
        
        # Handle breach
        if is_breach:
            await self._handle_accuracy_breach(metric)
        
        return metric
    
    async def _handle_accuracy_breach(self, metric: AccuracyMetric):
        """Handle accuracy SLA breach"""
        breach_key = f"{metric.model_name}_{metric.metric_name}"
        self.breach_counts[breach_key] = self.breach_counts.get(breach_key, 0) + 1
        
        logger.warning("Accuracy SLA breach detected",
                      model_name=metric.model_name,
                      metric_name=metric.metric_name,
                      current_value=metric.current_value,
                      threshold=metric.threshold,
                      breach_count=self.breach_counts[breach_key])
        
        # Trigger alerts for repeated breaches
        if self.breach_counts[breach_key] >= 3:
            await self._trigger_accuracy_alert(metric)
    
    async def _trigger_accuracy_alert(self, metric: AccuracyMetric):
        """Trigger PagerDuty/alerting for accuracy breaches"""
        logger.error("Critical accuracy alert",
                    model_name=metric.model_name,
                    metric_name=metric.metric_name,
                    breach_count=self.breach_counts.get(f"{metric.model_name}_{metric.metric_name}", 0))
        
        # In production, would integrate with PagerDuty/Slack/etc
        alert_payload = {
            "severity": "high",
            "component": "model_accuracy",
            "model_name": metric.model_name,
            "metric_name": metric.metric_name,
            "current_value": metric.current_value,
            "threshold": metric.threshold,
            "message": f"Model {metric.model_name} {metric.metric_name} has breached SLA threshold"
        }
        
        # Mock alert dispatch
        logger.info("Alert dispatched", **alert_payload)
    
    def get_accuracy_summary(self) -> Dict[str, Any]:
        """Get current accuracy status summary"""
        summary = {
            "total_metrics": len(self.accuracy_history),
            "active_breaches": 0,
            "models_with_issues": set(),
            "recent_metrics": {}
        }
        
        for key, history in self.accuracy_history.items():
            if history:
                latest = history[-1]
                summary["recent_metrics"][key] = {
                    "value": latest.current_value,
                    "threshold": latest.threshold,
                    "is_breach": latest.is_breach,
                    "timestamp": latest.timestamp.isoformat()
                }
                
                if latest.is_breach:
                    summary["active_breaches"] += 1
                    summary["models_with_issues"].add(latest.model_name)
        
        summary["models_with_issues"] = list(summary["models_with_issues"])
        return summary


class FreshnessMonitor:
    """Monitors data freshness against SLA thresholds"""
    
    def __init__(self):
        self.freshness_history: Dict[str, List[FreshnessMetric]] = {}
        self.stale_sources: set = set()
    
    async def check_data_freshness(self) -> List[FreshnessMetric]:
        """Check freshness for all data sources"""
        current_time = datetime.now(timezone.utc)
        freshness_metrics = []
        
        # Define data sources and their SLA thresholds
        sources_config = {
            "treasury_rates": FRESHNESS_ALERTS["treasury_stale_minutes"] * 60,
            "mortgage_pricing": FRESHNESS_ALERTS["mortgage_stale_minutes"] * 60,
            "mobility_data": settings.freshness_targets.daily_signals_hours * 3600,
            "news_sentiment": settings.freshness_targets.news_sentiment_minutes * 60
        }
        
        for source_name, threshold_seconds in sources_config.items():
            # Mock last update time - in production would query actual data sources
            mock_last_update = current_time - timedelta(seconds=threshold_seconds * 0.8)  # 80% of threshold
            
            age_seconds = (current_time - mock_last_update).total_seconds()
            is_stale = age_seconds > threshold_seconds
            
            metric = FreshnessMetric(
                source_name=source_name,
                last_update=mock_last_update,
                age_seconds=age_seconds,
                threshold_seconds=threshold_seconds,
                is_stale=is_stale
            )
            
            freshness_metrics.append(metric)
            
            # Store in history
            if source_name not in self.freshness_history:
                self.freshness_history[source_name] = []
            
            self.freshness_history[source_name].append(metric)
            self.freshness_history[source_name] = self.freshness_history[source_name][-50:]  # Keep last 50
            
            # Update Prometheus metrics
            METRICS["data_freshness_seconds"].labels(source=source_name).set(age_seconds)
            
            # Handle stale data
            if is_stale:
                await self._handle_stale_data(metric)
            elif source_name in self.stale_sources:
                # Data is fresh again
                self.stale_sources.remove(source_name)
                logger.info("Data source recovered", source=source_name, age_seconds=age_seconds)
        
        return freshness_metrics
    
    async def _handle_stale_data(self, metric: FreshnessMetric):
        """Handle stale data detection"""
        if metric.source_name not in self.stale_sources:
            self.stale_sources.add(metric.source_name)
            
            logger.warning("Stale data detected",
                          source=metric.source_name,
                          age_seconds=metric.age_seconds,
                          threshold_seconds=metric.threshold_seconds)
            
            # Trigger alert for critical data sources
            critical_sources = ["treasury_rates", "mortgage_pricing"]
            if metric.source_name in critical_sources:
                await self._trigger_freshness_alert(metric)
    
    async def _trigger_freshness_alert(self, metric: FreshnessMetric):
        """Trigger alert for stale critical data"""
        logger.error("Critical data freshness alert",
                    source=metric.source_name,
                    age_hours=metric.age_seconds / 3600)
        
        # Mock alert dispatch
        alert_payload = {
            "severity": "medium",
            "component": "data_freshness",
            "source": metric.source_name,
            "age_hours": metric.age_seconds / 3600,
            "message": f"Data source {metric.source_name} is stale"
        }
        
        logger.info("Freshness alert dispatched", **alert_payload)
    
    def get_freshness_summary(self) -> Dict[str, Any]:
        """Get current freshness status summary"""
        summary = {
            "total_sources": len(self.freshness_history),
            "stale_sources": len(self.stale_sources),
            "stale_source_names": list(self.stale_sources),
            "source_status": {}
        }
        
        for source_name, history in self.freshness_history.items():
            if history:
                latest = history[-1]
                summary["source_status"][source_name] = {
                    "age_seconds": latest.age_seconds,
                    "age_minutes": latest.age_seconds / 60,
                    "threshold_seconds": latest.threshold_seconds,
                    "is_stale": latest.is_stale,
                    "last_update": latest.last_update.isoformat()
                }
        
        return summary


class DriftDetector:
    """Detects model and data drift"""
    
    def __init__(self):
        self.feature_baselines: Dict[str, Dict[str, float]] = {}
        self.drift_history: List[DriftAlert] = []
    
    async def detect_feature_drift(self, model_name: str, features: Dict[str, float]) -> List[DriftAlert]:
        """Detect drift in feature distributions"""
        drift_alerts = []
        
        # Initialize baselines if first time
        if model_name not in self.feature_baselines:
            self.feature_baselines[model_name] = features.copy()
            return drift_alerts
        
        baseline = self.feature_baselines[model_name]
        
        for feature_name, current_value in features.items():
            if feature_name in baseline:
                baseline_value = baseline[feature_name]
                
                # Simple drift detection: relative change
                if baseline_value != 0:
                    drift_score = abs((current_value - baseline_value) / baseline_value)
                else:
                    drift_score = abs(current_value)
                
                # Drift thresholds
                if drift_score > 0.5:  # 50% change
                    severity = "high"
                elif drift_score > 0.2:  # 20% change
                    severity = "medium"
                elif drift_score > 0.1:  # 10% change
                    severity = "low"
                else:
                    continue  # No significant drift
                
                alert = DriftAlert(
                    model_name=model_name,
                    feature_name=feature_name,
                    drift_score=drift_score,
                    threshold=0.1,
                    severity=severity,
                    timestamp=datetime.now(timezone.utc)
                )
                
                drift_alerts.append(alert)
                self.drift_history.append(alert)
                
                logger.warning("Feature drift detected",
                              model_name=model_name,
                              feature_name=feature_name,
                              drift_score=drift_score,
                              severity=severity)
        
        # Keep drift history manageable
        self.drift_history = self.drift_history[-1000:]
        
        return drift_alerts
    
    def get_drift_summary(self) -> Dict[str, Any]:
        """Get drift detection summary"""
        recent_drift = [d for d in self.drift_history 
                       if (datetime.now(timezone.utc) - d.timestamp).days <= 7]
        
        return {
            "total_drift_alerts": len(self.drift_history),
            "recent_drift_alerts": len(recent_drift),
            "high_severity_count": len([d for d in recent_drift if d.severity == "high"]),
            "affected_models": list(set(d.model_name for d in recent_drift)),
            "top_drifting_features": self._get_top_drifting_features(recent_drift)
        }
    
    def _get_top_drifting_features(self, recent_drift: List[DriftAlert]) -> List[Dict[str, Any]]:
        """Get features with most drift occurrences"""
        feature_counts = {}
        for alert in recent_drift:
            key = f"{alert.model_name}:{alert.feature_name}"
            if key not in feature_counts:
                feature_counts[key] = {"count": 0, "max_score": 0}
            feature_counts[key]["count"] += 1
            feature_counts[key]["max_score"] = max(feature_counts[key]["max_score"], alert.drift_score)
        
        # Sort by count and return top 5
        sorted_features = sorted(feature_counts.items(), key=lambda x: x[1]["count"], reverse=True)
        
        return [{
            "feature": key,
            "drift_count": data["count"],
            "max_drift_score": data["max_score"]
        } for key, data in sorted_features[:5]]


class HealthChecker:
    """Main health checking orchestrator"""
    
    def __init__(self):
        self.accuracy_monitor = AccuracyMonitor()
        self.freshness_monitor = FreshnessMonitor()
        self.drift_detector = DriftDetector()
        self.start_time = datetime.now(timezone.utc)
        self.last_health_check = None
        self.background_task = None
    
    async def initialize(self):
        """Initialize health monitoring"""
        logger.info("Initializing health monitoring system")
        
        # Start background monitoring task
        self.background_task = asyncio.create_task(self._run_background_monitoring())
        
        logger.info("Health monitoring system initialized")
    
    async def check_health(self) -> HealthCheck:
        """Perform comprehensive health check"""
        check_start = datetime.now(timezone.utc)
        uptime = (check_start - self.start_time).total_seconds()
        
        checks = {}
        overall_status = HealthStatus.HEALTHY
        
        # Check data freshness
        freshness_metrics = await self.freshness_monitor.check_data_freshness()
        stale_count = sum(1 for m in freshness_metrics if m.is_stale)
        
        checks["data_freshness"] = {
            "status": "healthy" if stale_count == 0 else "degraded" if stale_count <= 2 else "unhealthy",
            "stale_sources": stale_count,
            "total_sources": len(freshness_metrics),
            "details": self.freshness_monitor.get_freshness_summary()
        }
        
        if stale_count > 2:
            overall_status = HealthStatus.UNHEALTHY
        elif stale_count > 0:
            overall_status = HealthStatus.DEGRADED
        
        # Check model accuracy
        accuracy_summary = self.accuracy_monitor.get_accuracy_summary()
        active_breaches = accuracy_summary["active_breaches"]
        
        checks["model_accuracy"] = {
            "status": "healthy" if active_breaches == 0 else "degraded" if active_breaches <= 2 else "unhealthy",
            "active_breaches": active_breaches,
            "models_with_issues": accuracy_summary["models_with_issues"],
            "details": accuracy_summary
        }
        
        if active_breaches > 2:
            overall_status = HealthStatus.UNHEALTHY
        elif active_breaches > 0 and overall_status == HealthStatus.HEALTHY:
            overall_status = HealthStatus.DEGRADED
        
        # Check drift
        drift_summary = self.drift_detector.get_drift_summary()
        high_drift_count = drift_summary["high_severity_count"]
        
        checks["model_drift"] = {
            "status": "healthy" if high_drift_count == 0 else "degraded" if high_drift_count <= 1 else "unhealthy",
            "high_severity_alerts": high_drift_count,
            "recent_alerts": drift_summary["recent_drift_alerts"],
            "details": drift_summary
        }
        
        if high_drift_count > 1:
            overall_status = HealthStatus.UNHEALTHY
        elif high_drift_count > 0 and overall_status == HealthStatus.HEALTHY:
            overall_status = HealthStatus.DEGRADED
        
        # Check system resources (mock)
        checks["system_resources"] = {
            "status": "healthy",
            "cpu_usage_percent": 45.2,
            "memory_usage_percent": 62.1,
            "disk_usage_percent": 23.4
        }
        
        # Database connectivity (mock)
        checks["database"] = {
            "status": "healthy",
            "connection_pool_active": 8,
            "connection_pool_idle": 2,
            "query_latency_ms": 15.3
        }
        
        # Feature store (mock)
        checks["feature_store"] = {
            "status": "healthy",
            "cache_hit_rate": 0.85,
            "avg_retrieval_time_ms": 25.1
        }
        
        self.last_health_check = check_start
        
        return HealthCheck(
            status=overall_status.value,
            timestamp=check_start,
            checks=checks,
            uptime_seconds=uptime
        )
    
    async def _run_background_monitoring(self):
        """Background task for continuous monitoring"""
        logger.info("Starting background monitoring task")
        
        while True:
            try:
                # Run freshness checks every minute
                await self.freshness_monitor.check_data_freshness()
                
                # Sleep for 1 minute
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error("Background monitoring error", error=str(e))
                await asyncio.sleep(30)  # Shorter sleep on error
    
    async def record_prediction_metrics(self, model_name: str, actual_values: Dict[str, float], predicted_values: Dict[str, float]):
        """Record prediction accuracy metrics"""
        
        # Calculate accuracy metrics
        if "caprate" in actual_values and "caprate" in predicted_values:
            mae_bps = abs(actual_values["caprate"] - predicted_values["caprate"]) * 10000
            await self.accuracy_monitor.record_accuracy(model_name, "caprate_mae_bps", mae_bps)
        
        if "noi_growth" in actual_values and "noi_growth" in predicted_values:
            mape = abs((actual_values["noi_growth"] - predicted_values["noi_growth"]) / actual_values["noi_growth"]) * 100
            await self.accuracy_monitor.record_accuracy(model_name, "noi_mape_percent", mape)
    
    async def record_feature_drift(self, model_name: str, features: Dict[str, float]):
        """Record feature values for drift detection"""
        await self.drift_detector.detect_feature_drift(model_name, features)
    
    def get_monitoring_dashboard_data(self) -> Dict[str, Any]:
        """Get data for monitoring dashboard"""
        return {
            "accuracy": self.accuracy_monitor.get_accuracy_summary(),
            "freshness": self.freshness_monitor.get_freshness_summary(),
            "drift": self.drift_detector.get_drift_summary(),
            "uptime_seconds": (datetime.now(timezone.utc) - self.start_time).total_seconds(),
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None
        }


# Export main classes
__all__ = [
    "HealthChecker",
    "AccuracyMonitor",
    "FreshnessMonitor", 
    "DriftDetector",
    "HealthStatus",
    "AccuracyMetric",
    "FreshnessMetric",
    "DriftAlert"
]
