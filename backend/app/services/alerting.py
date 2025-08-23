"""
Alerting & Monitoring Integration
PagerDuty, OpsGenie, Slack integration for business alerts
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum
import httpx

from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

class AlertSeverity(str, Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class AlertChannel(str, Enum):
    """Alert channels"""
    PAGERDUTY = "pagerduty"
    OPSGENIE = "opsgenie"
    SLACK = "slack"
    EMAIL = "email"
    WEBHOOK = "webhook"

class Alert:
    """Alert model"""
    def __init__(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        source: str,
        details: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ):
        self.title = title
        self.message = message
        self.severity = severity
        self.source = source
        self.details = details or {}
        self.tags = tags or []
        self.timestamp = datetime.utcnow()
        self.alert_id = f"{source}_{int(self.timestamp.timestamp())}"

class PagerDutyIntegration:
    """PagerDuty integration for critical alerts"""
    
    def __init__(self):
        self.integration_key = settings.PAGERDUTY_INTEGRATION_KEY
        self.api_url = "https://events.pagerduty.com/v2/enqueue"
        self.enabled = bool(self.integration_key)
    
    async def send_alert(self, alert: Alert) -> bool:
        """Send alert to PagerDuty"""
        if not self.enabled:
            logger.warning("PagerDuty integration not configured")
            return False
        
        try:
            # Map severity to PagerDuty event action
            event_action = "trigger"
            if alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]:
                event_action = "trigger"
            elif alert.severity == AlertSeverity.INFO:
                event_action = "resolve"
            
            payload = {
                "routing_key": self.integration_key,
                "event_action": event_action,
                "dedup_key": alert.alert_id,
                "payload": {
                    "summary": f"[{alert.source}] {alert.title}",
                    "source": alert.source,
                    "severity": alert.severity.value,
                    "timestamp": alert.timestamp.isoformat(),
                    "custom_details": {
                        "message": alert.message,
                        "details": alert.details,
                        "tags": alert.tags
                    }
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()
                
            logger.info(f"PagerDuty alert sent: {alert.alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send PagerDuty alert: {e}")
            return False

class OpsGenieIntegration:
    """OpsGenie integration for operational alerts"""
    
    def __init__(self):
        self.api_key = settings.OPSGENIE_API_KEY
        self.api_url = "https://api.opsgenie.com/v2/alerts"
        self.enabled = bool(self.api_key)
    
    async def send_alert(self, alert: Alert) -> bool:
        """Send alert to OpsGenie"""
        if not self.enabled:
            logger.warning("OpsGenie integration not configured")
            return False
        
        try:
            # Map severity to OpsGenie priority
            priority_map = {
                AlertSeverity.CRITICAL: "P1",
                AlertSeverity.HIGH: "P2",
                AlertSeverity.MEDIUM: "P3",
                AlertSeverity.LOW: "P4",
                AlertSeverity.INFO: "P5"
            }
            
            payload = {
                "message": f"[{alert.source}] {alert.title}",
                "alias": alert.alert_id,
                "description": alert.message,
                "priority": priority_map.get(alert.severity, "P3"),
                "source": alert.source,
                "tags": alert.tags,
                "details": alert.details
            }
            
            headers = {
                "Authorization": f"GenieKey {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                    timeout=10.0
                )
                response.raise_for_status()
                
            logger.info(f"OpsGenie alert sent: {alert.alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send OpsGenie alert: {e}")
            return False

class SlackIntegration:
    """Slack integration for team notifications"""
    
    def __init__(self):
        self.webhook_url = settings.SLACK_WEBHOOK_URL
        self.enabled = bool(self.webhook_url)
    
    async def send_alert(self, alert: Alert) -> bool:
        """Send alert to Slack"""
        if not self.enabled:
            logger.warning("Slack integration not configured")
            return False
        
        try:
            # Map severity to Slack colors
            color_map = {
                AlertSeverity.CRITICAL: "#FF0000",  # Red
                AlertSeverity.HIGH: "#FF8C00",      # Orange
                AlertSeverity.MEDIUM: "#FFD700",    # Gold
                AlertSeverity.LOW: "#32CD32",       # Green
                AlertSeverity.INFO: "#87CEEB"       # Sky Blue
            }
            
            # Format details as fields
            fields = []
            if alert.details:
                for key, value in alert.details.items():
                    fields.append({
                        "title": key.replace("_", " ").title(),
                        "value": str(value),
                        "short": True
                    })
            
            attachment = {
                "color": color_map.get(alert.severity, "#808080"),
                "title": f"🚨 {alert.title}",
                "text": alert.message,
                "fields": fields,
                "footer": f"Source: {alert.source}",
                "ts": int(alert.timestamp.timestamp())
            }
            
            if alert.tags:
                attachment["fields"].append({
                    "title": "Tags",
                    "value": ", ".join(alert.tags),
                    "short": True
                })
            
            payload = {
                "username": "CapSight Alerts",
                "icon_emoji": ":warning:",
                "attachments": [attachment]
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()
                
            logger.info(f"Slack alert sent: {alert.alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False

class AlertManager:
    """Central alert management and routing"""
    
    def __init__(self):
        self.pagerduty = PagerDutyIntegration()
        self.opsgenie = OpsGenieIntegration()
        self.slack = SlackIntegration()
        
        # Alert routing rules
        self.routing_rules = {
            AlertSeverity.CRITICAL: [AlertChannel.PAGERDUTY, AlertChannel.SLACK],
            AlertSeverity.HIGH: [AlertChannel.OPSGENIE, AlertChannel.SLACK],
            AlertSeverity.MEDIUM: [AlertChannel.SLACK],
            AlertSeverity.LOW: [AlertChannel.SLACK],
            AlertSeverity.INFO: [AlertChannel.SLACK]
        }
        
        # Alert suppression (prevent spam)
        self.suppression_cache = {}
        self.suppression_window = timedelta(minutes=15)
    
    async def send_alert(
        self, 
        alert: Alert,
        channels: Optional[List[AlertChannel]] = None
    ) -> Dict[str, bool]:
        """
        Send alert to appropriate channels
        Returns dict of channel -> success status
        """
        # Check for suppression
        if self._is_suppressed(alert):
            logger.info(f"Alert suppressed: {alert.alert_id}")
            return {}
        
        # Determine channels to use
        if channels is None:
            channels = self.routing_rules.get(alert.severity, [AlertChannel.SLACK])
        
        # Send to channels concurrently
        tasks = []
        for channel in channels:
            if channel == AlertChannel.PAGERDUTY:
                tasks.append(self._send_pagerduty(alert))
            elif channel == AlertChannel.OPSGENIE:
                tasks.append(self._send_opsgenie(alert))
            elif channel == AlertChannel.SLACK:
                tasks.append(self._send_slack(alert))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Map results to channels
        channel_results = {}
        for i, channel in enumerate(channels):
            if i < len(results):
                channel_results[channel.value] = (
                    results[i] if not isinstance(results[i], Exception) else False
                )
        
        # Update suppression cache
        self._update_suppression_cache(alert)
        
        return channel_results
    
    async def _send_pagerduty(self, alert: Alert) -> bool:
        """Send to PagerDuty"""
        return await self.pagerduty.send_alert(alert)
    
    async def _send_opsgenie(self, alert: Alert) -> bool:
        """Send to OpsGenie"""
        return await self.opsgenie.send_alert(alert)
    
    async def _send_slack(self, alert: Alert) -> bool:
        """Send to Slack"""
        return await self.slack.send_alert(alert)
    
    def _is_suppressed(self, alert: Alert) -> bool:
        """Check if alert should be suppressed"""
        suppression_key = f"{alert.source}_{alert.title}_{alert.severity}"
        
        if suppression_key in self.suppression_cache:
            last_sent = self.suppression_cache[suppression_key]
            if datetime.utcnow() - last_sent < self.suppression_window:
                return True
        
        return False
    
    def _update_suppression_cache(self, alert: Alert):
        """Update suppression cache"""
        suppression_key = f"{alert.source}_{alert.title}_{alert.severity}"
        self.suppression_cache[suppression_key] = alert.timestamp
        
        # Clean old entries
        cutoff = datetime.utcnow() - self.suppression_window * 2
        self.suppression_cache = {
            k: v for k, v in self.suppression_cache.items() 
            if v > cutoff
        }

# Business Alert Templates
class BusinessAlerts:
    """Pre-configured business alert templates"""
    
    @staticmethod
    def low_prediction_volume(count: int) -> Alert:
        return Alert(
            title="Low Prediction Volume",
            message=f"Only {count} predictions generated today. Expected minimum: 50.",
            severity=AlertSeverity.MEDIUM,
            source="business_metrics",
            details={"prediction_count": count, "expected_minimum": 50},
            tags=["business", "volume", "predictions"]
        )
    
    @staticmethod
    def high_error_rate(rate: float) -> Alert:
        return Alert(
            title="High Error Rate",
            message=f"System error rate at {rate:.1f}%. Immediate attention required.",
            severity=AlertSeverity.CRITICAL if rate > 5.0 else AlertSeverity.HIGH,
            source="system_health",
            details={"error_rate": rate, "threshold": 2.0},
            tags=["system", "errors", "health"]
        )
    
    @staticmethod
    def model_degradation(confidence: float, mae: Optional[float] = None) -> Alert:
        severity = AlertSeverity.HIGH if confidence < 0.6 else AlertSeverity.MEDIUM
        message = f"Model confidence dropped to {confidence:.1%}."
        if mae:
            message += f" MAE: ${mae:,.0f}"
        
        return Alert(
            title="Model Performance Degradation",
            message=message,
            severity=severity,
            source="model_monitoring",
            details={"avg_confidence": confidence, "mae": mae},
            tags=["model", "ml", "performance"]
        )
    
    @staticmethod
    def system_downtime() -> Alert:
        return Alert(
            title="System Downtime Detected",
            message="Critical system components are not responding.",
            severity=AlertSeverity.CRITICAL,
            source="health_check",
            details={},
            tags=["system", "downtime", "critical"]
        )

# Global alert manager instance
alert_manager = AlertManager()
