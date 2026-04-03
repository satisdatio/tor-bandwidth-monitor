"""Metrics processing and aggregation for Tor monitoring."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from collections import deque
import time
import statistics
from datetime import datetime, timedelta


@dataclass
class MetricsSnapshot:
    """Processed metrics snapshot with calculated rates and statistics."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    read_bytes: int = 0
    write_bytes: int = 0
    read_rate_kibs: float = 0.0
    write_rate_kibs: float = 0.0
    circuit_count: int = 0
    stream_count: int = 0
    latency_ms: Optional[float] = None
    uptime_seconds: Optional[float] = None
    bootstrap_progress: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "read_bytes": self.read_bytes,
            "write_bytes": self.write_bytes,
            "read_rate_kibs": self.read_rate_kibs,
            "write_rate_kibs": self.write_rate_kibs,
            "circuit_count": self.circuit_count,
            "stream_count": self.stream_count,
            "latency_ms": self.latency_ms,
            "uptime_seconds": self.uptime_seconds,
            "bootstrap_progress": self.bootstrap_progress
        }


class MetricsCollector:
    """
    Collects and processes metrics over time with statistical analysis.

    Provides rate calculations, trend analysis, and historical data.
    """

    def __init__(self, history_size: int = 1000, retention_hours: int = 24):
        self.history_size = history_size
        self.retention_hours = retention_hours
        self._history: deque[MetricsSnapshot] = deque(maxlen=history_size)
        self._rate_window: deque[Dict[str, Any]] = deque(maxlen=10)  # For rate calculation

    def process(self, raw_metrics: Dict[str, Any]) -> MetricsSnapshot:
        """
        Process raw metrics from controller into enriched snapshot.

        Args:
            raw_metrics: Raw metrics dictionary from Tor controller

        Returns:
            Processed MetricsSnapshot with calculated rates
        """
        snapshot = MetricsSnapshot()
        current_time = datetime.utcnow()

        if raw_metrics:
            # Basic metrics
            snapshot.read_bytes = raw_metrics.get("read_bytes", 0)
            snapshot.write_bytes = raw_metrics.get("write_bytes", 0)
            snapshot.circuit_count = raw_metrics.get("circuit_count", 0)
            snapshot.uptime_seconds = raw_metrics.get("uptime_seconds", 0)
            snapshot.bootstrap_progress = raw_metrics.get("bootstrap_progress", 0.0)

            # Calculate rates using sliding window
            self._calculate_rates(snapshot)

            # Store in rate calculation window
            self._rate_window.append({
                "timestamp": current_time,
                "read_bytes": snapshot.read_bytes,
                "write_bytes": snapshot.write_bytes
            })

        # Store in history
        self._history.append(snapshot)

        # Cleanup old data
        self._cleanup_old_data()

        return snapshot

    def _calculate_rates(self, snapshot: MetricsSnapshot):
        """Calculate bandwidth rates using recent history."""
        if len(self._rate_window) < 2:
            return

        # Get last two measurements
        current = self._rate_window[-1]
        previous = self._rate_window[-2]

        time_diff = (current["timestamp"] - previous["timestamp"]).total_seconds()
        if time_diff <= 0:
            return

        # Calculate rates in KiB/s
        read_diff = current["read_bytes"] - previous["read_bytes"]
        write_diff = current["write_bytes"] - previous["write_bytes"]

        snapshot.read_rate_kibs = max(0, read_diff / 1024 / time_diff)
        snapshot.write_rate_kibs = max(0, write_diff / 1024 / time_diff)

    def _cleanup_old_data(self):
        """Remove data older than retention period."""
        cutoff = datetime.utcnow() - timedelta(hours=self.retention_hours)
        while self._history and self._history[0].timestamp < cutoff:
            self._history.popleft()

    def get_average_read_rate(self, hours: int = 1) -> float:
        """Get average read rate over specified hours."""
        return self._get_average_rate("read_rate_kibs", hours)

    def get_average_write_rate(self, hours: int = 1) -> float:
        """Get average write rate over specified hours."""
        return self._get_average_rate("write_rate_kibs", hours)

    def _get_average_rate(self, field: str, hours: int) -> float:
        """Get average rate for field over time period."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        values = [
            getattr(snapshot, field)
            for snapshot in self._history
            if snapshot.timestamp >= cutoff and getattr(snapshot, field) is not None
        ]

        if not values:
            return 0.0

        return statistics.mean(values)

    def get_peak_read_rate(self, hours: int = 1) -> float:
        """Get peak read rate over specified hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        values = [
            snapshot.read_rate_kibs
            for snapshot in self._history
            if snapshot.timestamp >= cutoff
        ]

        return max(values) if values else 0.0

    def get_peak_write_rate(self, hours: int = 1) -> float:
        """Get peak write rate over specified hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        values = [
            snapshot.write_rate_kibs
            for snapshot in self._history
            if snapshot.timestamp >= cutoff
        ]

        return max(values) if values else 0.0

    def get_recent_history(self, limit: int = 100) -> List[MetricsSnapshot]:
        """Get recent metrics history."""
        return list(self._history)[-limit:]

    def get_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive statistics over time period."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent_snapshots = [
            s for s in self._history
            if s.timestamp >= cutoff
        ]

        if not recent_snapshots:
            return {}

        read_rates = [s.read_rate_kibs for s in recent_snapshots if s.read_rate_kibs > 0]
        write_rates = [s.write_rate_kibs for s in recent_snapshots if s.write_rate_kibs > 0]

        stats = {
            "sample_count": len(recent_snapshots),
            "time_range_hours": hours,
            "read_rate": {
                "current": recent_snapshots[-1].read_rate_kibs if recent_snapshots else 0,
                "average": statistics.mean(read_rates) if read_rates else 0,
                "peak": max(read_rates) if read_rates else 0,
                "p95": statistics.quantiles(read_rates, n=20)[18] if len(read_rates) >= 20 else max(read_rates) if read_rates else 0,
            },
            "write_rate": {
                "current": recent_snapshots[-1].write_rate_kibs if recent_snapshots else 0,
                "average": statistics.mean(write_rates) if write_rates else 0,
                "peak": max(write_rates) if write_rates else 0,
                "p95": statistics.quantiles(write_rates, n=20)[18] if len(write_rates) >= 20 else max(write_rates) if write_rates else 0,
            },
            "circuits": {
                "current": recent_snapshots[-1].circuit_count if recent_snapshots else 0,
                "average": statistics.mean([s.circuit_count for s in recent_snapshots]),
                "max": max([s.circuit_count for s in recent_snapshots]),
            }
        }

        return stats

    def get_trend_analysis(self, hours: int = 1) -> Dict[str, Any]:
        """Analyze trends in metrics over time period."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent = [s for s in self._history if s.timestamp >= cutoff]

        if len(recent) < 2:
            return {"trend": "insufficient_data"}

        # Simple linear trend analysis
        x = list(range(len(recent)))
        read_y = [s.read_rate_kibs for s in recent]
        write_y = [s.write_rate_kibs for s in recent]

        try:
            read_slope = statistics.linear_regression(x, read_y)[0]
            write_slope = statistics.linear_regression(x, write_y)[0]

            return {
                "trend": "stable",
                "read_rate_slope": read_slope,
                "write_rate_slope": write_slope,
                "read_trend": "increasing" if read_slope > 0.1 else "decreasing" if read_slope < -0.1 else "stable",
                "write_trend": "increasing" if write_slope > 0.1 else "decreasing" if write_slope < -0.1 else "stable",
            }
        except statistics.StatisticsError:
            return {"trend": "calculation_error"}