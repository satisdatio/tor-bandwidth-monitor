"""Alerting engine with multiple notification channels."""

import asyncio
import smtplib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
import httpx

logger = logging.getLogger(__name__)


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(Enum):
    BANDWIDTH_DROP = "bandwidth_drop"
    BANDWIDTH_SPIKE = "bandwidth_spike"
    HIGH_LATENCY = "high_latency"
    CIRCUIT_FAILURE = "circuit_failure"
    RELAY_OFFLINE = "relay_offline"
    ANOMALY_DETECTED = "anomaly_detected"
    BOOTSTRAP_ISSUE = "bootstrap_issue"
    CUSTOM = "custom"


@dataclass
class AlertRule:
    """Alert rule definition."""
    name: str
    alert_type: AlertType
    condition: Callable[[Dict[str, Any]], bool]
    severity: Severity
    message_template: str
    cooldown_minutes: int = 5
    enabled: bool = True


@dataclass
class Alert:
    """Active alert instance."""
    id: str
    rule_name: str
    alert_type: AlertType
    severity: Severity
    message: str
    metrics: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    notified: bool = False


class AlertManager:
    """
    Alerting engine with rules, cooldowns, and multiple notification channels.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.rules: List[AlertRule] = []
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self._last_triggered: Dict[str, datetime] = {}
        self._callbacks: List[Callable[[Alert], None]] = []
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default alert rules."""
        self.rules.extend([
            AlertRule(
                name="bandwidth_drop_critical",
                alert_type=AlertType.BANDWIDTH_DROP,
                condition=lambda m: m.get("read_rate_kibs", 0) < m.get("read_rate_avg", 0) * 0.1,
                severity=Severity.CRITICAL,
                message_template="Bandwidth dropped below 10% of average: {read_rate_kibs:.2f} KiB/s (avg: {read_rate_avg:.2f} KiB/s)",
                cooldown_minutes=5
            ),
            AlertRule(
                name="bandwidth_drop_warning",
                alert_type=AlertType.BANDWIDTH_DROP,
                condition=lambda m: m.get("read_rate_kibs", 0) < m.get("read_rate_avg", 0) * 0.3,
                severity=Severity.WARNING,
                message_template="Bandwidth dropped below 30% of average: {read_rate_kibs:.2f} KiB/s",
                cooldown_minutes=10
            ),
            AlertRule(
                name="high_latency",
                alert_type=AlertType.HIGH_LATENCY,
                condition=lambda m: m.get("latency_ms", 0) > m.get("latency_threshold", 500),
                severity=Severity.WARNING,
                message_template="High latency detected: {latency_ms:.1f}ms (threshold: {latency_threshold}ms)",
                cooldown_minutes=5
            ),
            AlertRule(
                name="circuit_failure",
                alert_type=AlertType.CIRCUIT_FAILURE,
                condition=lambda m: m.get("circuit_failures", 0) > m.get("circuit_failure_threshold", 5),
                severity=Severity.CRITICAL,
                message_template="Multiple circuit failures: {circuit_failures} failures in last minute",
                cooldown_minutes=2
            ),
            AlertRule(
                name="relay_offline",
                alert_type=AlertType.RELAY_OFFLINE,
                condition=lambda m: not m.get("is_connected", True),
                severity=Severity.CRITICAL,
                message_template="Relay connection lost",
                cooldown_minutes=1
            ),
        ])
    
    def add_rule(self, rule: AlertRule):
        """Add custom alert rule."""
        self.rules.append(rule)
    
    def add_callback(self, callback: Callable[[Alert], None]):
        """Add callback for alert notifications."""
        self._callbacks.append(callback)
    
    def evaluate(self, metrics: Dict[str, Any]) -> List[Alert]:
        """
        Evaluate all rules against metrics.
        
        Returns:
            List of newly triggered alerts
        """
        triggered = []
        now = datetime.utcnow()
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            # Check cooldown
            if rule.name in self._last_triggered:
                elapsed = (now - self._last_triggered[rule.name]).total_seconds() / 60
                if elapsed < rule.cooldown_minutes:
                    continue
            
            try:
                if rule.condition(metrics):
                    alert = self._create_alert(rule, metrics)
                    triggered.append(alert)
                    self._last_triggered[rule.name] = now
                    self._notify(alert)
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.name}: {e}")
        
        return triggered
    
    def _create_alert(self, rule: AlertRule, metrics: Dict[str, Any]) -> Alert:
        """Create alert from rule."""
        import uuid
        alert_id = f"{rule.name}_{int(datetime.utcnow().timestamp())}_{uuid.uuid4().hex[:8]}"
        
        message = rule.message_template.format(**metrics)
        
        alert = Alert(
            id=alert_id,
            rule_name=rule.name,
            alert_type=rule.alert_type,
            severity=rule.severity,
            message=message,
            metrics=metrics.copy()
        )
        
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        return alert
    
    def _notify(self, alert: Alert):
        """Send notifications via configured channels."""
        for callback in self._callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Notification callback error: {e}")
        
        alert.notified = True
    
    def resolve_alert(self, alert_id: str):
        """Mark alert as resolved."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            del self.active_alerts[alert_id]
    
    def get_active_alerts(self, severity: Optional[Severity] = None) -> List[Alert]:
        """Get active alerts, optionally filtered by severity."""
        alerts = list(self.active_alerts.values())
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)
    
    def get_alert_stats(self) -> Dict[str, int]:
        """Get alert statistics."""
        return {
            "active": len(self.active_alerts),
            "critical": len([a for a in self.active_alerts.values() if a.severity == Severity.CRITICAL]),
            "warning": len([a for a in self.active_alerts.values() if a.severity == Severity.WARNING]),
            "info": len([a for a in self.active_alerts.values() if a.severity == Severity.INFO]),
            "total_history": len(self.alert_history)
        }


class EmailNotifier:
    """Email notification channel."""
    
    def __init__(self, smtp_host: str, smtp_port: int, 
                 from_addr: str, to_addrs: List[str],
                 username: str = None, password: str = None):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.from_addr = from_addr
        self.to_addrs = to_addrs
        self.username = username
        self.password = password
    
    def __call__(self, alert: Alert):
        """Send email notification."""
        if not self.to_addrs:
            return
        
        subject = f"[Tor Monitor] {alert.severity.value.upper()}: {alert.rule_name}"
        body = f"""
Alert: {alert.message}
Severity: {alert.severity.value}
Type: {alert.alert_type.value}
Timestamp: {alert.timestamp}

Metrics:
{json.dumps(alert.metrics, indent=2, default=str)}
"""
        
        message = f"Subject: {subject}\n\n{body}"
        
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.sendmail(self.from_addr, self.to_addrs, message)
            logger.info(f"Email alert sent: {alert.id}")
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")


class SlackNotifier:
    """Slack webhook notification channel."""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self._client = httpx.AsyncClient(timeout=10.0)
    
    async def __call__(self, alert: Alert):
        """Send Slack notification."""
        color = {
            Severity.INFO: "#36a64f",
            Severity.WARNING: "#ff9500",
            Severity.CRITICAL: "#ff0000"
        }.get(alert.severity, "#808080")
        
        emoji = {
            Severity.INFO: "ℹ️",
            Severity.WARNING: "⚠️",
            Severity.CRITICAL: "🚨"
        }.get(alert.severity, "📢")
        
        payload = {
            "attachments": [{
                "color": color,
                "title": f"{emoji} {alert.severity.value.upper()}: {alert.rule_name}",
                "text": alert.message,
                "fields": [
                    {"title": "Type", "value": alert.alert_type.value, "short": True},
                    {"title": "Timestamp", "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "short": True},
                ],
                "footer": "Tor Monitor Pro",
                "ts": int(alert.timestamp.timestamp())
            }]
        }
        
        try:
            response = await self._client.post(self.webhook_url, json=payload)
            response.raise_for_status()
            logger.info(f"Slack alert sent: {alert.id}")
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
    
    async def close(self):
        await self._client.aclose()


class PagerDutyNotifier:
    """PagerDuty notification channel."""
    
    def __init__(self, integration_key: str):
        self.integration_key = integration_key
        self._client = httpx.AsyncClient(timeout=10.0)
        self._api_url = "https://events.pagerduty.com/v2/enqueue"
    
    async def __call__(self, alert: Alert):
        """Send PagerDuty notification."""
        severity_map = {
            Severity.INFO: "info",
            Severity.WARNING: "warning",
            Severity.CRITICAL: "critical"
        }
        
        payload = {
            "routing_key": self.integration_key,
            "event_action": "trigger",
            "dedup_key": alert.id,
            "payload": {
                "summary": alert.message,
                "severity": severity_map[alert.severity],
                "source": "tor-monitor-pro",
                "component": alert.alert_type.value,
                "custom_details": alert.metrics
            }
        }
        
        try:
            response = await self._client.post(self._api_url, json=payload)
            response.raise_for_status()
            logger.info(f"PagerDuty alert sent: {alert.id}")
        except Exception as e:
            logger.error(f"Failed to send PagerDuty alert: {e}")
    
    async def resolve(self, alert: Alert):
        """Resolve PagerDuty incident."""
        payload = {
            "routing_key": self.integration_key,
            "event_action": "resolve",
            "dedup_key": alert.id
        }
        
        try:
            await self._client.post(self._api_url, json=payload)
        except Exception as e:
            logger.error(f"Failed to resolve PagerDuty alert: {e}")
    
    async def close(self):
        await self._client.aclose()