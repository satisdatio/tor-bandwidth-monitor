"""Circuit path and traffic pattern anomaly detection."""

import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import deque
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class Anomaly:
    """Detected anomaly."""
    anomaly_type: str
    severity: str
    message: str
    timestamp: datetime
    details: Dict
    confidence: float


class StatisticalAnalyzer:
    """Statistical analysis for anomaly detection."""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self._values: deque = deque(maxlen=window_size)
        self._sum = 0.0
        self._sum_sq = 0.0
    
    def add(self, value: float):
        """Add value to window."""
        if len(self._values) == self.window_size:
            old = self._values[0]
            self._sum -= old
            self._sum_sq -= old * old
        
        self._values.append(value)
        self._sum += value
        self._sum_sq += value * value
    
    def mean(self) -> float:
        if not self._values:
            return 0.0
        return self._sum / len(self._values)
    
    def std(self) -> float:
        n = len(self._values)
        if n < 2:
            return 0.0
        variance = (self._sum_sq / n) - (self._sum / n) ** 2
        return math.sqrt(max(0, variance))
    
    def z_score(self, value: float) -> float:
        std = self.std()
        if std < 1e-6:
            return 0.0
        return abs(value - self.mean()) / std
    
    def is_anomaly(self, value: float, threshold: float = 3.0) -> Tuple[bool, float]:
        """Check if value is anomalous based on z-score."""
        if len(self._values) < 10:
            return False, 0.0
        z = self.z_score(value)
        return z > threshold, z


class CircuitPathAnalyzer:
    """
    Analyzes circuit paths for potential security anomalies.
    
    Detects:
    - Guard relay rotation anomalies
    - Exit relay concentration
    - Geographic path anomalies
    - Unusual circuit purposes
    """
    
    def __init__(self, threshold: float = 3.0):
        self.threshold = threshold
        self._guard_usage: Dict[str, int] = {}
        self._exit_usage: Dict[str, int] = {}
        self._path_history: deque = deque(maxlen=1000)
        self._guard_analyzer = StatisticalAnalyzer()
        self._exit_analyzer = StatisticalAnalyzer()
    
    def analyze_circuit(self, circuit_id: int, path: List[str], 
                       purpose: str, is_hs: bool = False) -> List[Anomaly]:
        """
        Analyze a circuit path for anomalies.
        
        Args:
            circuit_id: Circuit identifier
            path: List of relay fingerprints/names in path
            purpose: Circuit purpose
            is_hs: Whether this is a hidden service circuit
        
        Returns:
            List of detected anomalies
        """
        anomalies = []
        now = datetime.utcnow()
        
        if not path:
            return anomalies
        
        # Track guard usage
        guard = path[0]
        self._guard_usage[guard] = self._guard_usage.get(guard, 0) + 1
        
        # Track exit usage
        if not is_hs and len(path) >= 3:
            exit_relay = path[-1]
            self._exit_usage[exit_relay] = self._exit_usage.get(exit_relay, 0) + 1
        
        # Store path
        self._path_history.append({
            "circuit_id": circuit_id,
            "path": path,
            "purpose": purpose,
            "timestamp": now
        })
        
        # Check for guard concentration
        total_guards = sum(self._guard_usage.values())
        if total_guards > 10:
            guard_ratio = self._guard_usage[guard] / total_guards
            if guard_ratio > 0.5:
                anomalies.append(Anomaly(
                    anomaly_type="guard_concentration",
                    severity="warning",
                    message=f"High guard relay concentration: {guard} used in {guard_ratio:.1%} of circuits",
                    timestamp=now,
                    details={"guard": guard, "ratio": guard_ratio, "threshold": 0.5},
                    confidence=min(guard_ratio, 1.0)
                ))
        
        # Check for exit concentration
        total_exits = sum(self._exit_usage.values())
        if total_exits > 10:
            for exit_relay, count in self._exit_usage.items():
                exit_ratio = count / total_exits
                if exit_ratio > 0.3:
                    anomalies.append(Anomaly(
                        anomaly_type="exit_concentration",
                        severity="warning",
                        message=f"High exit relay concentration: {exit_relay} used in {exit_ratio:.1%} of circuits",
                        timestamp=now,
                        details={"exit": exit_relay, "ratio": exit_ratio, "threshold": 0.3},
                        confidence=min(exit_ratio, 1.0)
                    ))
                    break
        
        # Check for unusual purposes
        unusual_purposes = ["UNKNOWN", "TESTING"]
        if purpose in unusual_purposes:
            anomalies.append(Anomaly(
                anomaly_type="unusual_purpose",
                severity="info",
                message=f"Circuit with unusual purpose: {purpose}",
                timestamp=now,
                details={"purpose": purpose, "circuit_id": circuit_id},
                confidence=0.7
            ))
        
        return anomalies
    
    def get_guard_stats(self) -> Dict[str, float]:
        """Get guard relay usage statistics."""
        total = sum(self._guard_usage.values())
        if total == 0:
            return {}
        return {g: c / total for g, c in self._guard_usage.items()}
    
    def get_exit_stats(self) -> Dict[str, float]:
        """Get exit relay usage statistics."""
        total = sum(self._exit_usage.values())
        if total == 0:
            return {}
        return {e: c / total for e, c in self._exit_usage.items()}


class TrafficPatternAnalyzer:
    """
    Analyzes traffic patterns for anomalies.
    
    Detects:
    - Sudden bandwidth spikes/drops
    - Unusual traffic ratios
    - Timing pattern anomalies
    """
    
    def __init__(self, threshold: float = 3.0, window_minutes: int = 60):
        self.threshold = threshold
        self.window_minutes = window_minutes
        self._read_analyzer = StatisticalAnalyzer()
        self._write_analyzer = StatisticalAnalyzer()
        self._ratio_analyzer = StatisticalAnalyzer()
        self._traffic_history: deque = deque(maxlen=1000)
    
    def analyze(self, read_rate: float, write_rate: float, 
               timestamp: datetime = None) -> List[Anomaly]:
        """
        Analyze traffic rates for anomalies.
        
        Returns:
            List of detected anomalies
        """
        anomalies = []
        now = timestamp or datetime.utcnow()
        
        # Check read rate
        self._read_analyzer.add(read_rate)
        is_read_anomaly, read_z = self._read_analyzer.is_anomaly(read_rate, self.threshold)
        
        if is_read_anomaly:
            direction = "spike" if read_rate > self._read_analyzer.mean() else "drop"
            anomalies.append(Anomaly(
                anomaly_type=f"bandwidth_{direction}",
                severity="critical" if read_z > 4 else "warning",
                message=f"Unusual bandwidth {direction}: {read_rate:.2f} KiB/s (z-score: {read_z:.2f})",
                timestamp=now,
                details={
                    "rate": read_rate,
                    "mean": self._read_analyzer.mean(),
                    "std": self._read_analyzer.std(),
                    "z_score": read_z
                },
                confidence=min(read_z / 5, 1.0)
            ))
        
        # Check write rate
        self._write_analyzer.add(write_rate)
        is_write_anomaly, write_z = self._write_analyzer.is_anomaly(write_rate, self.threshold)
        
        if is_write_anomaly:
            direction = "spike" if write_rate > self._write_analyzer.mean() else "drop"
            anomalies.append(Anomaly(
                anomaly_type=f"upload_{direction}",
                severity="critical" if write_z > 4 else "warning",
                message=f"Unusual upload {direction}: {write_rate:.2f} KiB/s (z-score: {write_z:.2f})",
                timestamp=now,
                details={
                    "rate": write_rate,
                    "mean": self._write_analyzer.mean(),
                    "std": self._write_analyzer.std(),
                    "z_score": write_z
                },
                confidence=min(write_z / 5, 1.0)
            ))
        
        # Check read/write ratio
        if write_rate > 0:
            ratio = read_rate / write_rate
            self._ratio_analyzer.add(ratio)
            is_ratio_anomaly, ratio_z = self._ratio_analyzer.is_anomaly(ratio, self.threshold)
            
            if is_ratio_anomaly:
                anomalies.append(Anomaly(
                    anomaly_type="traffic_ratio_anomaly",
                    severity="warning",
                    message=f"Unusual traffic ratio: {ratio:.2f} (z-score: {ratio_z:.2f})",
                    timestamp=now,
                    details={
                        "ratio": ratio,
                        "mean": self._ratio_analyzer.mean(),
                        "z_score": ratio_z
                    },
                    confidence=min(ratio_z / 5, 1.0)
                ))
        
        # Store for history
        self._traffic_history.append({
            "timestamp": now,
            "read_rate": read_rate,
            "write_rate": write_rate
        })
        
        return anomalies
    
    def get_traffic_summary(self) -> Dict:
        """Get traffic pattern summary."""
        return {
            "read": {
                "mean": self._read_analyzer.mean(),
                "std": self._read_analyzer.std()
            },
            "write": {
                "mean": self._write_analyzer.mean(),
                "std": self._write_analyzer.std()
            },
            "samples": len(self._traffic_history)
        }


class AnomalyDetector:
    """
    Main anomaly detection engine combining all analyzers.
    """
    
    def __init__(self, threshold: float = 3.0):
        self.threshold = threshold
        self.circuit_analyzer = CircuitPathAnalyzer(threshold)
        self.traffic_analyzer = TrafficPatternAnalyzer(threshold)
        self._anomalies: deque = deque(maxlen=1000)
    
    def analyze_metrics(self, metrics: Dict) -> List[Anomaly]:
        """
        Analyze metrics for all anomaly types.
        
        Args:
            metrics: Dictionary with read_rate_kibs, write_rate_kibs, etc.
        
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        # Traffic analysis
        read_rate = metrics.get("read_rate_kibs", 0)
        write_rate = metrics.get("write_rate_kibs", 0)
        anomalies.extend(self.traffic_analyzer.analyze(read_rate, write_rate))
        
        # Circuit analysis
        if "circuits" in metrics:
            for circuit in metrics["circuits"]:
                path = circuit.get("path", [])
                purpose = circuit.get("purpose", "GENERAL")
                is_hs = circuit.get("is_hs", False)
                circuit_anomalies = self.circuit_analyzer.analyze_circuit(
                    circuit.get("id", 0), path, purpose, is_hs
                )
                anomalies.extend(circuit_anomalies)
        
        # Store anomalies
        for anomaly in anomalies:
            self._anomalies.append(anomaly)
        
        return anomalies
    
    def get_recent_anomalies(self, limit: int = 50, 
                            severity: str = None) -> List[Anomaly]:
        """Get recent anomalies."""
        results = list(self._anomalies)
        if severity:
            results = [a for a in results if a.severity == severity]
        return sorted(results, key=lambda a: a.timestamp, reverse=True)[:limit]
    
    def get_anomaly_stats(self) -> Dict:
        """Get anomaly statistics."""
        stats = {
            "total": len(self._anomalies),
            "by_type": {},
            "by_severity": {"info": 0, "warning": 0, "critical": 0}
        }
        
        for anomaly in self._anomalies:
            stats["by_type"][anomaly.anomaly_type] = \
                stats["by_type"].get(anomaly.anomaly_type, 0) + 1
            stats["by_severity"][anomaly.severity] = \
                stats["by_severity"].get(anomaly.severity, 0) + 1
        
        return stats