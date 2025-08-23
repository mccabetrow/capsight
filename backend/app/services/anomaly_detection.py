"""
Anomaly Detection & Model Drift Monitoring
Advanced ML monitoring for production model health
"""

import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN

from app.db.session import get_db_session
from app.services.alerting import alert_manager, Alert, AlertSeverity, BusinessAlerts
from app.core.config import settings

logger = logging.getLogger(__name__)

class AnomalyType(str, Enum):
    """Types of anomalies detected"""
    STATISTICAL = "statistical"
    DISTRIBUTION = "distribution"
    VOLUME = "volume"
    PERFORMANCE = "performance"
    DRIFT = "drift"

@dataclass
class AnomalyResult:
    """Anomaly detection result"""
    anomaly_type: AnomalyType
    score: float  # 0-1, higher = more anomalous
    threshold: float
    is_anomaly: bool
    details: Dict[str, Any]
    timestamp: datetime
    affected_metrics: List[str]

@dataclass
class DriftResult:
    """Model drift detection result"""
    drift_type: str  # "data", "prediction", "performance"
    drift_score: float  # 0-1, higher = more drift
    p_value: float
    is_significant: bool
    baseline_period: str
    current_period: str
    details: Dict[str, Any]
    timestamp: datetime

class StatisticalAnomalyDetector:
    """Statistical anomaly detection using Z-score and IQR methods"""
    
    def __init__(self, z_threshold: float = 3.0, iqr_multiplier: float = 1.5):
        self.z_threshold = z_threshold
        self.iqr_multiplier = iqr_multiplier
    
    def detect_z_score_anomalies(self, data: np.ndarray) -> Tuple[np.ndarray, float]:
        """Detect anomalies using Z-score method"""
        if len(data) < 3:
            return np.array([]), 0.0
        
        mean = np.mean(data)
        std = np.std(data)
        
        if std == 0:
            return np.array([]), 0.0
        
        z_scores = np.abs((data - mean) / std)
        anomalies = z_scores > self.z_threshold
        max_score = np.max(z_scores) / self.z_threshold if len(z_scores) > 0 else 0.0
        
        return anomalies, min(max_score, 1.0)
    
    def detect_iqr_anomalies(self, data: np.ndarray) -> Tuple[np.ndarray, float]:
        """Detect anomalies using IQR method"""
        if len(data) < 4:
            return np.array([]), 0.0
        
        q1 = np.percentile(data, 25)
        q3 = np.percentile(data, 75)
        iqr = q3 - q1
        
        if iqr == 0:
            return np.array([]), 0.0
        
        lower_bound = q1 - self.iqr_multiplier * iqr
        upper_bound = q3 + self.iqr_multiplier * iqr
        
        anomalies = (data < lower_bound) | (data > upper_bound)
        
        # Calculate anomaly score based on distance from bounds
        scores = np.maximum(
            (lower_bound - data) / (iqr * self.iqr_multiplier),
            (data - upper_bound) / (iqr * self.iqr_multiplier)
        )
        max_score = np.max(scores) if len(scores) > 0 else 0.0
        
        return anomalies, min(max_score, 1.0)

class MachineLearningAnomalyDetector:
    """ML-based anomaly detection using Isolation Forest"""
    
    def __init__(self, contamination: float = 0.1, random_state: int = 42):
        self.contamination = contamination
        self.random_state = random_state
        self.model = None
    
    def fit_detect(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Fit model and detect anomalies"""
        if len(data.shape) == 1:
            data = data.reshape(-1, 1)
        
        if len(data) < 10:
            return np.array([]), np.array([])
        
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            n_estimators=100
        )
        
        predictions = self.model.fit_predict(data)
        anomaly_scores = self.model.decision_function(data)
        
        # Convert to boolean anomalies and normalize scores
        anomalies = predictions == -1
        normalized_scores = (anomaly_scores - anomaly_scores.min()) / (
            anomaly_scores.max() - anomaly_scores.min()
        ) if anomaly_scores.max() > anomaly_scores.min() else np.zeros_like(anomaly_scores)
        
        return anomalies, normalized_scores

class ModelDriftDetector:
    """Detect model drift using statistical tests"""
    
    def __init__(self):
        self.drift_threshold = 0.05  # p-value threshold for significance
    
    def detect_data_drift(
        self, 
        baseline_data: np.ndarray, 
        current_data: np.ndarray
    ) -> DriftResult:
        """Detect data drift using Kolmogorov-Smirnov test"""
        try:
            # KS test for distribution comparison
            ks_statistic, p_value = stats.ks_2samp(baseline_data, current_data)
            
            is_significant = p_value < self.drift_threshold
            drift_score = min(ks_statistic, 1.0)
            
            details = {
                "ks_statistic": float(ks_statistic),
                "baseline_mean": float(np.mean(baseline_data)),
                "current_mean": float(np.mean(current_data)),
                "baseline_std": float(np.std(baseline_data)),
                "current_std": float(np.std(current_data)),
                "baseline_size": len(baseline_data),
                "current_size": len(current_data)
            }
            
            return DriftResult(
                drift_type="data",
                drift_score=drift_score,
                p_value=p_value,
                is_significant=is_significant,
                baseline_period="last_30_days",
                current_period="last_7_days",
                details=details,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error in data drift detection: {e}")
            return DriftResult(
                drift_type="data",
                drift_score=0.0,
                p_value=1.0,
                is_significant=False,
                baseline_period="last_30_days",
                current_period="last_7_days",
                details={"error": str(e)},
                timestamp=datetime.utcnow()
            )
    
    def detect_prediction_drift(
        self,
        baseline_predictions: np.ndarray,
        current_predictions: np.ndarray
    ) -> DriftResult:
        """Detect prediction drift"""
        return self.detect_data_drift(baseline_predictions, current_predictions)
    
    def detect_performance_drift(
        self,
        baseline_errors: np.ndarray,
        current_errors: np.ndarray
    ) -> DriftResult:
        """Detect performance drift using error distributions"""
        drift_result = self.detect_data_drift(baseline_errors, current_errors)
        drift_result.drift_type = "performance"
        
        # Add performance-specific details
        drift_result.details.update({
            "baseline_mae": float(np.mean(np.abs(baseline_errors))),
            "current_mae": float(np.mean(np.abs(current_errors))),
            "baseline_rmse": float(np.sqrt(np.mean(baseline_errors**2))),
            "current_rmse": float(np.sqrt(np.mean(current_errors**2)))
        })
        
        return drift_result

class BusinessAnomalyDetector:
    """Business-specific anomaly detection"""
    
    def __init__(self):
        self.statistical_detector = StatisticalAnomalyDetector()
        self.ml_detector = MachineLearningAnomalyDetector()
        self.drift_detector = ModelDriftDetector()
    
    async def detect_volume_anomalies(self) -> List[AnomalyResult]:
        """Detect anomalies in prediction volume"""
        anomalies = []
        
        try:
            async with get_db_session() as session:
                # Get daily prediction counts for last 30 days
                query = text("""
                    SELECT 
                        DATE(created_at) as date,
                        COUNT(*) as prediction_count
                    FROM predictions 
                    WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                    GROUP BY DATE(created_at)
                    ORDER BY date
                """)
                
                result = await session.execute(query)
                rows = result.fetchall()
                
                if len(rows) < 7:
                    return anomalies
                
                dates = [row.date for row in rows]
                counts = np.array([row.prediction_count for row in rows])
                
                # Statistical anomaly detection
                z_anomalies, z_score = self.statistical_detector.detect_z_score_anomalies(counts)
                iqr_anomalies, iqr_score = self.statistical_detector.detect_iqr_anomalies(counts)
                
                # ML anomaly detection
                ml_anomalies, ml_scores = self.ml_detector.fit_detect(counts)
                
                # Combine results
                if len(z_anomalies) > 0 and np.any(z_anomalies):
                    anomalies.append(AnomalyResult(
                        anomaly_type=AnomalyType.VOLUME,
                        score=z_score,
                        threshold=self.statistical_detector.z_threshold,
                        is_anomaly=True,
                        details={
                            "method": "z_score",
                            "anomalous_dates": [str(dates[i]) for i, is_anom in enumerate(z_anomalies) if is_anom],
                            "mean_count": float(np.mean(counts)),
                            "std_count": float(np.std(counts))
                        },
                        timestamp=datetime.utcnow(),
                        affected_metrics=["daily_predictions"]
                    ))
                
        except Exception as e:
            logger.error(f"Error detecting volume anomalies: {e}")
        
        return anomalies
    
    async def detect_performance_anomalies(self) -> List[AnomalyResult]:
        """Detect anomalies in model performance"""
        anomalies = []
        
        try:
            async with get_db_session() as session:
                # Get daily average confidence scores
                query = text("""
                    SELECT 
                        DATE(created_at) as date,
                        AVG(confidence) as avg_confidence,
                        AVG(investment_score) as avg_investment_score,
                        COUNT(*) as prediction_count
                    FROM predictions 
                    WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                    GROUP BY DATE(created_at)
                    HAVING COUNT(*) >= 5
                    ORDER BY date
                """)
                
                result = await session.execute(query)
                rows = result.fetchall()
                
                if len(rows) < 7:
                    return anomalies
                
                confidence_scores = np.array([row.avg_confidence for row in rows])
                investment_scores = np.array([row.avg_investment_score for row in rows])
                
                # Detect confidence anomalies
                conf_anomalies, conf_score = self.statistical_detector.detect_z_score_anomalies(confidence_scores)
                if np.any(conf_anomalies):
                    anomalies.append(AnomalyResult(
                        anomaly_type=AnomalyType.PERFORMANCE,
                        score=conf_score,
                        threshold=0.7,  # Business threshold for acceptable confidence
                        is_anomaly=conf_score > 0.5,
                        details={
                            "metric": "confidence",
                            "mean_confidence": float(np.mean(confidence_scores)),
                            "min_confidence": float(np.min(confidence_scores)),
                            "anomaly_dates": [str(rows[i].date) for i, is_anom in enumerate(conf_anomalies) if is_anom]
                        },
                        timestamp=datetime.utcnow(),
                        affected_metrics=["model_confidence"]
                    ))
                
        except Exception as e:
            logger.error(f"Error detecting performance anomalies: {e}")
        
        return anomalies
    
    async def detect_drift(self) -> List[DriftResult]:
        """Detect various types of model drift"""
        drift_results = []
        
        try:
            async with get_db_session() as session:
                # Get baseline data (30 days ago to 7 days ago)
                baseline_query = text("""
                    SELECT predicted_value, confidence, investment_score
                    FROM predictions 
                    WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                    AND created_at < CURRENT_DATE - INTERVAL '7 days'
                """)
                
                # Get current data (last 7 days)
                current_query = text("""
                    SELECT predicted_value, confidence, investment_score
                    FROM predictions 
                    WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
                """)
                
                baseline_result = await session.execute(baseline_query)
                current_result = await session.execute(current_query)
                
                baseline_rows = baseline_result.fetchall()
                current_rows = current_result.fetchall()
                
                if len(baseline_rows) < 10 or len(current_rows) < 10:
                    return drift_results
                
                # Extract features
                baseline_values = np.array([row.predicted_value for row in baseline_rows])
                current_values = np.array([row.predicted_value for row in current_rows])
                
                baseline_confidence = np.array([row.confidence for row in baseline_rows])
                current_confidence = np.array([row.confidence for row in current_rows])
                
                # Detect prediction drift
                value_drift = self.drift_detector.detect_data_drift(baseline_values, current_values)
                value_drift.drift_type = "prediction_values"
                drift_results.append(value_drift)
                
                # Detect confidence drift
                conf_drift = self.drift_detector.detect_data_drift(baseline_confidence, current_confidence)
                conf_drift.drift_type = "prediction_confidence"
                drift_results.append(conf_drift)
                
        except Exception as e:
            logger.error(f"Error detecting drift: {e}")
        
        return drift_results

class MonitoringJob:
    """Background job for anomaly detection and drift monitoring"""
    
    def __init__(self):
        self.detector = BusinessAnomalyDetector()
        self.last_check = datetime.utcnow()
    
    async def run_anomaly_detection(self):
        """Run anomaly detection checks"""
        try:
            logger.info("Starting anomaly detection job")
            
            # Detect anomalies
            volume_anomalies = await self.detector.detect_volume_anomalies()
            performance_anomalies = await self.detector.detect_performance_anomalies()
            
            all_anomalies = volume_anomalies + performance_anomalies
            
            # Send alerts for significant anomalies
            for anomaly in all_anomalies:
                if anomaly.is_anomaly and anomaly.score > 0.7:
                    severity = AlertSeverity.HIGH if anomaly.score > 0.9 else AlertSeverity.MEDIUM
                    
                    alert = Alert(
                        title=f"{anomaly.anomaly_type.value.title()} Anomaly Detected",
                        message=f"Anomaly score: {anomaly.score:.2f}. Check {', '.join(anomaly.affected_metrics)}",
                        severity=severity,
                        source="anomaly_detection",
                        details=anomaly.details,
                        tags=["anomaly", anomaly.anomaly_type.value]
                    )
                    
                    await alert_manager.send_alert(alert)
            
            logger.info(f"Anomaly detection completed. Found {len(all_anomalies)} anomalies")
            
        except Exception as e:
            logger.error(f"Error in anomaly detection job: {e}")
    
    async def run_drift_detection(self):
        """Run drift detection checks"""
        try:
            logger.info("Starting drift detection job")
            
            drift_results = await self.detector.detect_drift()
            
            # Send alerts for significant drift
            for drift in drift_results:
                if drift.is_significant and drift.drift_score > 0.3:
                    severity = AlertSeverity.HIGH if drift.drift_score > 0.7 else AlertSeverity.MEDIUM
                    
                    alert = Alert(
                        title=f"Model Drift Detected - {drift.drift_type}",
                        message=f"Drift score: {drift.drift_score:.2f}, p-value: {drift.p_value:.4f}",
                        severity=severity,
                        source="drift_detection",
                        details=drift.details,
                        tags=["drift", "model", drift.drift_type]
                    )
                    
                    await alert_manager.send_alert(alert)
            
            logger.info(f"Drift detection completed. Found {len([d for d in drift_results if d.is_significant])} significant drifts")
            
        except Exception as e:
            logger.error(f"Error in drift detection job: {e}")
    
    async def run_full_monitoring_cycle(self):
        """Run complete monitoring cycle"""
        try:
            # Run anomaly and drift detection concurrently
            await asyncio.gather(
                self.run_anomaly_detection(),
                self.run_drift_detection(),
                return_exceptions=True
            )
            
            self.last_check = datetime.utcnow()
            logger.info("Full monitoring cycle completed")
            
        except Exception as e:
            logger.error(f"Error in monitoring cycle: {e}")

# Global monitoring job instance
monitoring_job = MonitoringJob()
