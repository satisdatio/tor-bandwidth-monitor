"""Prometheus metrics exporter."""

from prometheus_client import (
    Counter, Gauge, Histogram, Info, CollectorRegistry,
    generate_latest, CONTENT_TYPE_LATEST
)
from typing import Dict, Optional
import time


class PrometheusExporter:
    """
    Prometheus metrics exporter for Tor monitoring.
    
    Exports metrics compatible with Prometheus/Grafana dashboards.
    """
    
    def __init__(self, prefix: str = "tor_monitor"):
        self.prefix = prefix
        self.registry = CollectorRegistry()
        self._metrics: Dict[str, any] = {}
        self._setup_metrics()
    
    def _setup_metrics(self):
        """Setup all Prometheus metrics."""
        p = self.prefix
        
        # Info metrics
        self._metrics["info"] = Info(
            f"{p}_relay",
            "Tor relay information",
            registry=self.registry
        )
        
        # Bandwidth gauges
        self._metrics["read_rate"] = Gauge(
            f"{p}_read_rate_kibs",
            "Current download rate in KiB/s",
            ["relay"],
            registry=self.registry
        )
        
        self._metrics["write_rate"] = Gauge(
            f"{p}_write_rate_kibs",
            "Current upload rate in KiB/s",
            ["relay"],
            registry=self.registry
        )
        
        self._metrics["read_bytes_total"] = Counter(
            f"{p}_read_bytes_total",
            "Total bytes downloaded",
            ["relay"],
            registry=self.registry
        )
        
        self._metrics["write_bytes_total"] = Counter(
            f"{p}_write_bytes_total",
            "Total bytes uploaded",
            ["relay"],
            registry=self.registry
        )
        
        # Circuit metrics
        self._metrics["circuit_count"] = Gauge(
            f"{p}_circuit_count",
            "Number of active circuits",
            ["relay"],
            registry=self.registry
        )
        
        self._metrics["circuit_status"] = Gauge(
            f"{p}_circuit_status",
            "Circuit status count by state",
            ["relay", "status"],
            registry=self.registry
        )
        
        self._metrics["circuit_purpose"] = Gauge(
            f"{p}_circuit_purpose",
            "Circuit count by purpose",
            ["relay", "purpose"],
            registry=self.registry
        )
        
        # Latency metrics
        self._metrics["latency_ms"] = Gauge(
            f"{p}_latency_ms",
            "Current latency in milliseconds",
            ["relay"],
            registry=self.registry
        )
        
        self._metrics["latency_histogram"] = Histogram(
            f"{p}_latency_seconds",
            "Latency distribution",
            ["relay"],
            buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
            registry=self.registry
        )
        
        # Stream metrics
        self._metrics["stream_count"] = Gauge(
            f"{p}_stream_count",
            "Number of active streams",
            ["relay"],
            registry=self.registry
        )
        
        # Uptime
        self._metrics["uptime_seconds"] = Gauge(
            f"{p}_uptime_seconds",
            "Tor process uptime in seconds",
            ["relay"],
            registry=self.registry
        )
        
        # Bootstrap
        self._metrics["bootstrap_progress"] = Gauge(
            f"{p}_bootstrap_progress",
            "Bootstrap progress percentage",
            ["relay"],
            registry=self.registry
        )
        
        # Alert metrics
        self._metrics["alerts_active"] = Gauge(
            f"{p}_alerts_active",
            "Number of active alerts",
            ["relay", "severity"],
            registry=self.registry
        )
        
        self._metrics["alerts_total"] = Counter(
            f"{p}_alerts_total",
            "Total alerts triggered",
            ["relay", "type", "severity"],
            registry=self.registry
        )
        
        # Anomaly metrics
        self._metrics["anomalies_total"] = Counter(
            f"{p}_anomalies_total",
            "Total anomalies detected",
            ["relay", "type", "severity"],
            registry=self.registry
        )
        
        # Connection status
        self._metrics["connected"] = Gauge(
            f"{p}_connected",
            "Connection status (1=connected, 0=disconnected)",
            ["relay"],
            registry=self.registry
        )
    
    def update_relay_info(self, relay: str, info: Dict[str, str]):
        """Update relay info labels."""
        self._metrics["info"].info(info)
    
    def update_bandwidth(self, relay: str, read_rate: float, 
                        write_rate: float, read_total: int = None,
                        write_total: int = None):
        """Update bandwidth metrics."""
        self._metrics["read_rate"].labels(relay=relay).set(read_rate)
        self._metrics["write_rate"].labels(relay=relay).set(write_rate)
        
        if read_total is not None:
            self._metrics["read_bytes_total"].labels(relay=relay).inc(read_total)
        if write_total is not None:
            self._metrics["write_bytes_total"].labels(relay=relay).inc(write_total)
    
    def update_circuits(self, relay: str, count: int, 
                       by_status: Dict[str, int] = None,
                       by_purpose: Dict[str, int] = None):
        """Update circuit metrics."""
        self._metrics["circuit_count"].labels(relay=relay).set(count)
        
        if by_status:
            for status, c in by_status.items():
                self._metrics["circuit_status"].labels(relay=relay, status=status).set(c)
        
        if by_purpose:
            for purpose, c in by_purpose.items():
                self._metrics["circuit_purpose"].labels(relay=relay, purpose=purpose).set(c)
    
    def update_latency(self, relay: str, latency_ms: float):
        """Update latency metrics."""
        self._metrics["latency_ms"].labels(relay=relay).set(latency_ms)
        self._metrics["latency_histogram"].labels(relay=relay).observe(latency_ms / 1000)
    
    def update_streams(self, relay: str, count: int):
        """Update stream count."""
        self._metrics["stream_count"].labels(relay=relay).set(count)
    
    def update_uptime(self, relay: str, uptime_seconds: float):
        """Update uptime."""
        self._metrics["uptime_seconds"].labels(relay=relay).set(uptime_seconds)
    
    def update_bootstrap(self, relay: str, progress: float):
        """Update bootstrap progress."""
        self._metrics["bootstrap_progress"].labels(relay=relay).set(progress)
    
    def update_alerts(self, relay: str, active: Dict[str, int],
                     triggered: Dict[str, Dict[str, int]] = None):
        """Update alert metrics."""
        for severity, count in active.items():
            self._metrics["alerts_active"].labels(relay=relay, severity=severity).set(count)
        
        if triggered:
            for alert_type, severities in triggered.items():
                for severity, count in severities.items():
                    self._metrics["alerts_total"].labels(
                        relay=relay, type=alert_type, severity=severity
                    ).inc(count)
    
    def update_anomaly(self, relay: str, anomaly_type: str, 
                      severity: str, count: int = 1):
        """Record anomaly."""
        self._metrics["anomalies_total"].labels(
            relay=relay, type=anomaly_type, severity=severity
        ).inc(count)
    
    def update_connection(self, relay: str, connected: bool):
        """Update connection status."""
        self._metrics["connected"].labels(relay=relay).set(1 if connected else 0)
    
    def generate(self) -> bytes:
        """Generate Prometheus metrics output."""
        return generate_latest(self.registry)
    
    def get_content_type(self) -> str:
        """Get content type for HTTP response."""
        return CONTENT_TYPE_LATEST