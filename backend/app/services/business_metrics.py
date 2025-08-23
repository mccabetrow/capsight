"""
Business Metrics Collection and Dashboard
Advanced KPIs for CapSight Property Predictor
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json
from dataclasses import dataclass, asdict
from decimal import Decimal

from sqlalchemy import text, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.prediction import Prediction
from app.models.user import User
from app.core.config import settings

@dataclass
class BusinessMetrics:
    """Business KPI metrics"""
    timestamp: datetime
    
    # Core Business Metrics
    daily_predictions: int
    daily_active_users: int
    monthly_active_users: int
    total_users: int
    
    # Financial Metrics
    total_predictions_value: float
    avg_prediction_value: float
    high_confidence_predictions: int  # >80% confidence
    
    # Model Performance
    avg_confidence_score: float
    avg_investment_score: float
    model_accuracy_mae: Optional[float]
    model_drift_score: Optional[float]
    
    # Market Intelligence
    top_markets: List[Dict[str, Any]]
    property_type_distribution: Dict[str, int]
    prediction_trends: Dict[str, float]  # 7d, 30d growth
    
    # Operational Metrics
    api_response_time_p95: float
    error_rate_24h: float
    system_uptime: float
    
    # User Behavior
    avg_predictions_per_user: float
    user_retention_7d: float
    user_retention_30d: float

class BusinessMetricsCollector:
    """Collect and calculate business metrics"""
    
    def __init__(self):
        self.session: Optional[AsyncSession] = None
    
    async def collect_metrics(self) -> BusinessMetrics:
        """Collect all business metrics"""
        async with get_db_session() as session:
            self.session = session
            
            # Collect metrics concurrently
            results = await asyncio.gather(
                self._get_prediction_metrics(),
                self._get_user_metrics(),
                self._get_financial_metrics(),
                self._get_model_performance(),
                self._get_market_intelligence(),
                self._get_operational_metrics(),
                self._get_user_behavior_metrics(),
                return_exceptions=True
            )
            
            # Combine results
            prediction_metrics = results[0] if not isinstance(results[0], Exception) else {}
            user_metrics = results[1] if not isinstance(results[1], Exception) else {}
            financial_metrics = results[2] if not isinstance(results[2], Exception) else {}
            model_metrics = results[3] if not isinstance(results[3], Exception) else {}
            market_metrics = results[4] if not isinstance(results[4], Exception) else {}
            operational_metrics = results[5] if not isinstance(results[5], Exception) else {}
            behavior_metrics = results[6] if not isinstance(results[6], Exception) else {}
            
            return BusinessMetrics(
                timestamp=datetime.utcnow(),
                **prediction_metrics,
                **user_metrics,
                **financial_metrics,
                **model_metrics,
                **market_metrics,
                **operational_metrics,
                **behavior_metrics
            )
    
    async def _get_prediction_metrics(self) -> Dict[str, Any]:
        """Get prediction-related metrics"""
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Daily predictions
        daily_query = text("""
            SELECT COUNT(*) as daily_predictions
            FROM predictions 
            WHERE created_at >= :today_start
        """)
        daily_result = await self.session.execute(daily_query, {"today_start": today_start})
        daily_predictions = daily_result.scalar() or 0
        
        # High confidence predictions (>80%)
        confidence_query = text("""
            SELECT COUNT(*) as high_confidence
            FROM predictions 
            WHERE confidence > 0.8 AND created_at >= :today_start
        """)
        confidence_result = await self.session.execute(confidence_query, {"today_start": today_start})
        high_confidence_predictions = confidence_result.scalar() or 0
        
        return {
            "daily_predictions": daily_predictions,
            "high_confidence_predictions": high_confidence_predictions
        }
    
    async def _get_user_metrics(self) -> Dict[str, Any]:
        """Get user-related metrics"""
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Daily active users
        dau_query = text("""
            SELECT COUNT(DISTINCT user_id) as dau
            FROM predictions 
            WHERE created_at >= :today_start
        """)
        dau_result = await self.session.execute(dau_query, {"today_start": today_start})
        daily_active_users = dau_result.scalar() or 0
        
        # Monthly active users
        mau_query = text("""
            SELECT COUNT(DISTINCT user_id) as mau
            FROM predictions 
            WHERE created_at >= :month_ago
        """)
        mau_result = await self.session.execute(mau_query, {"month_ago": month_ago})
        monthly_active_users = mau_result.scalar() or 0
        
        # Total users
        total_users_query = text("SELECT COUNT(*) FROM users")
        total_users_result = await self.session.execute(total_users_query)
        total_users = total_users_result.scalar() or 0
        
        return {
            "daily_active_users": daily_active_users,
            "monthly_active_users": monthly_active_users,
            "total_users": total_users
        }
    
    async def _get_financial_metrics(self) -> Dict[str, Any]:
        """Get financial metrics"""
        # Total prediction value today
        value_query = text("""
            SELECT 
                COALESCE(SUM(predicted_value), 0) as total_value,
                COALESCE(AVG(predicted_value), 0) as avg_value
            FROM predictions 
            WHERE created_at >= CURRENT_DATE
        """)
        value_result = await self.session.execute(value_query)
        value_row = value_result.fetchone()
        
        return {
            "total_predictions_value": float(value_row.total_value or 0),
            "avg_prediction_value": float(value_row.avg_value or 0)
        }
    
    async def _get_model_performance(self) -> Dict[str, Any]:
        """Get model performance metrics"""
        # Average confidence and investment scores
        model_query = text("""
            SELECT 
                COALESCE(AVG(confidence), 0) as avg_confidence,
                COALESCE(AVG(investment_score), 0) as avg_investment_score
            FROM predictions 
            WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
        """)
        model_result = await self.session.execute(model_query)
        model_row = model_result.fetchone()
        
        # Calculate MAE if actual values are available
        mae_query = text("""
            SELECT 
                AVG(ABS(predicted_value - actual_value)) as mae
            FROM predictions 
            WHERE actual_value IS NOT NULL 
            AND created_at >= CURRENT_DATE - INTERVAL '30 days'
        """)
        mae_result = await self.session.execute(mae_query)
        mae_value = mae_result.scalar()
        
        return {
            "avg_confidence_score": float(model_row.avg_confidence or 0),
            "avg_investment_score": float(model_row.avg_investment_score or 0),
            "model_accuracy_mae": float(mae_value) if mae_value else None,
            "model_drift_score": None  # Implement drift detection
        }
    
    async def _get_market_intelligence(self) -> Dict[str, Any]:
        """Get market intelligence metrics"""
        # Top markets by prediction volume
        markets_query = text("""
            SELECT 
                COALESCE(
                    SPLIT_PART(SPLIT_PART(address, ',', -2), ' ', -1), 
                    'Unknown'
                ) as state,
                COUNT(*) as prediction_count,
                AVG(predicted_value) as avg_value
            FROM predictions 
            WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY state 
            ORDER BY prediction_count DESC 
            LIMIT 10
        """)
        markets_result = await self.session.execute(markets_query)
        top_markets = [
            {
                "state": row.state,
                "prediction_count": row.prediction_count,
                "avg_value": float(row.avg_value)
            }
            for row in markets_result.fetchall()
        ]
        
        # Property type distribution
        property_types_query = text("""
            SELECT 
                property_type,
                COUNT(*) as count
            FROM predictions 
            WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY property_type
        """)
        property_types_result = await self.session.execute(property_types_query)
        property_type_distribution = {
            row.property_type: row.count 
            for row in property_types_result.fetchall()
        }
        
        # Prediction trends (7d vs previous 7d)
        trends_query = text("""
            SELECT 
                'current_week' as period,
                COUNT(*) as predictions,
                AVG(predicted_value) as avg_value
            FROM predictions 
            WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
            
            UNION ALL
            
            SELECT 
                'previous_week' as period,
                COUNT(*) as predictions,
                AVG(predicted_value) as avg_value
            FROM predictions 
            WHERE created_at >= CURRENT_DATE - INTERVAL '14 days'
            AND created_at < CURRENT_DATE - INTERVAL '7 days'
        """)
        trends_result = await self.session.execute(trends_query)
        trends_data = {row.period: {"predictions": row.predictions, "avg_value": float(row.avg_value or 0)} 
                      for row in trends_result.fetchall()}
        
        # Calculate growth rates
        current_week = trends_data.get("current_week", {"predictions": 0, "avg_value": 0})
        previous_week = trends_data.get("previous_week", {"predictions": 1, "avg_value": 1})  # Avoid division by zero
        
        prediction_trends = {
            "7d_volume_growth": ((current_week["predictions"] - previous_week["predictions"]) / 
                               max(previous_week["predictions"], 1)) * 100,
            "7d_value_growth": ((current_week["avg_value"] - previous_week["avg_value"]) / 
                              max(previous_week["avg_value"], 1)) * 100
        }
        
        return {
            "top_markets": top_markets,
            "property_type_distribution": property_type_distribution,
            "prediction_trends": prediction_trends
        }
    
    async def _get_operational_metrics(self) -> Dict[str, Any]:
        """Get operational metrics"""
        # These would typically come from monitoring systems
        # For now, return mock values - replace with actual monitoring integration
        
        return {
            "api_response_time_p95": 250.0,  # ms
            "error_rate_24h": 0.1,  # %
            "system_uptime": 99.9  # %
        }
    
    async def _get_user_behavior_metrics(self) -> Dict[str, Any]:
        """Get user behavior metrics"""
        # Average predictions per user
        avg_predictions_query = text("""
            SELECT AVG(prediction_count) as avg_predictions
            FROM (
                SELECT user_id, COUNT(*) as prediction_count
                FROM predictions 
                WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY user_id
            ) user_predictions
        """)
        avg_result = await self.session.execute(avg_predictions_query)
        avg_predictions_per_user = float(avg_result.scalar() or 0)
        
        # User retention (simplified - users who made predictions in both periods)
        retention_7d_query = text("""
            WITH recent_users AS (
                SELECT DISTINCT user_id FROM predictions 
                WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
            ),
            previous_users AS (
                SELECT DISTINCT user_id FROM predictions 
                WHERE created_at >= CURRENT_DATE - INTERVAL '14 days'
                AND created_at < CURRENT_DATE - INTERVAL '7 days'
            )
            SELECT 
                COUNT(DISTINCT r.user_id)::float / NULLIF(COUNT(DISTINCT p.user_id), 0) * 100 as retention
            FROM previous_users p
            LEFT JOIN recent_users r ON p.user_id = r.user_id
        """)
        retention_7d_result = await self.session.execute(retention_7d_query)
        user_retention_7d = float(retention_7d_result.scalar() or 0)
        
        return {
            "avg_predictions_per_user": avg_predictions_per_user,
            "user_retention_7d": user_retention_7d,
            "user_retention_30d": 0.0  # Implement 30-day retention
        }

# Business Metrics API Endpoint
class BusinessMetricsAPI:
    """API endpoints for business metrics"""
    
    def __init__(self):
        self.collector = BusinessMetricsCollector()
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        metrics = await self.collector.collect_metrics()
        return asdict(metrics)
    
    async def get_kpi_summary(self) -> Dict[str, Any]:
        """Get key KPI summary"""
        metrics = await self.collector.collect_metrics()
        
        return {
            "summary": {
                "daily_predictions": metrics.daily_predictions,
                "daily_active_users": metrics.daily_active_users,
                "avg_prediction_value": metrics.avg_prediction_value,
                "model_confidence": metrics.avg_confidence_score,
                "system_health": {
                    "uptime": metrics.system_uptime,
                    "error_rate": metrics.error_rate_24h,
                    "response_time": metrics.api_response_time_p95
                }
            },
            "growth": metrics.prediction_trends,
            "top_markets": metrics.top_markets[:5],
            "alerts": await self._generate_alerts(metrics)
        }
    
    async def _generate_alerts(self, metrics: BusinessMetrics) -> List[Dict[str, Any]]:
        """Generate business alerts based on metrics"""
        alerts = []
        
        # Low prediction volume alert
        if metrics.daily_predictions < 10:
            alerts.append({
                "type": "warning",
                "title": "Low Prediction Volume",
                "message": f"Only {metrics.daily_predictions} predictions today",
                "action": "Review marketing campaigns and user engagement"
            })
        
        # High error rate alert
        if metrics.error_rate_24h > 1.0:
            alerts.append({
                "type": "critical",
                "title": "High Error Rate",
                "message": f"Error rate at {metrics.error_rate_24h:.1f}%",
                "action": "Check system logs and infrastructure"
            })
        
        # Low model confidence alert
        if metrics.avg_confidence_score < 0.7:
            alerts.append({
                "type": "warning",
                "title": "Low Model Confidence",
                "message": f"Average confidence at {metrics.avg_confidence_score:.1%}",
                "action": "Review model performance and retrain if needed"
            })
        
        # Model drift alert (if MAE is available)
        if metrics.model_accuracy_mae and metrics.model_accuracy_mae > 50000:
            alerts.append({
                "type": "warning",
                "title": "Potential Model Drift",
                "message": f"MAE increased to ${metrics.model_accuracy_mae:,.0f}",
                "action": "Investigate model performance and consider retraining"
            })
        
        return alerts

# Export for use in API routes
business_metrics = BusinessMetricsAPI()
