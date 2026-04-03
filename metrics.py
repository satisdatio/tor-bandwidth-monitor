"""
tor_monitor/metrics.py
────────────────────────────────────────────────────────────────
Bandwidth sampling, throughput derivation, and latency estimation.

Design notes
------------
* All CPU-heavy work happens in sample(), which is called exactly
  once per refresh interval in the main loop.
* Thread-safety: this module is single-threaded (no background
  threads) to keep CPU overhead low.
* History is stored as a fixed-length deque to avoid unbounded
  memory growth.

Throughput calculation
----------------------
Tor exposes cumulative byte counters via GETINFO traffic/read
and traffic/written.  By diffing successive readings divided
by the elapsed wall-clock time we get an instantaneous rate:

    rate_kib = (bytes_now - bytes_prev) / elapsed / 1024

Latency estimation
------------------
Stem doesn't expose RTT directly.  We proxy it by measuring the
wall-clock time to complete a GETINFO round-trip (two syscalls +
one Tor response).  This is a loose estimate of the control-port
latency, which correlates with but is not identical to circuit
latency.  A proper latency measurement would require BEGINDIR
or an actual SOCKS5 connection test, which is out of scope for
an MVP.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List, Optional, Tuple

from tor_monitor.controller import TorController


# ── Data classes ──────────────────────────────────────────────

@dataclass
class BandwidthSample:
    """One instantaneous bandwidth measurement."""
    timestamp:   float   # time.monotonic()
    read_kib_s:  float   # downstream throughput in KiB/s
    write_kib_s: float   # upstream throughput in KiB/s


@dataclass
class CircuitInfo:
    """Snapshot of a single Tor circuit."""
    id:      str
    status:  str
    purpose: str
    path:    List[Tuple[str, str]]   # [(fingerprint, nickname), …]

    @property
    def path_str(self) -> str:
        """Human-readable relay path: Alice → Bob → Carol"""
        names = [nick or fp[:8] for fp, nick in self.path]
        return " → ".join(names) if names else "—"

    @property
    def hop_count(self) -> int:
        return len(self.path)


@dataclass
class Snapshot:
    """Everything the UI needs, produced once per sample interval."""
    # Bandwidth
    read_kib_s:     float
    write_kib_s:    float
    total_read_mib:  float     # cumulative MiB since Tor started
    total_write_mib: float

    # History (for sparkline)
    read_history:   List[float]   # KiB/s readings, oldest→newest
    write_history:  List[float]

    # Circuits
    circuits:       List[CircuitInfo]

    # Latency
    latency_ms:     Optional[float]   # None if unmeasurable

    # Tor info
    tor_version:    str
    uptime_s:       int
    is_relay:       bool

    # Timing
    sampled_at:     float = field(default_factory=time.monotonic)


# ── Collector ─────────────────────────────────────────────────

class MetricsCollector:
    """
    Collects and maintains a rolling window of bandwidth samples.

    Parameters
    ----------
    tor:          Connected TorController instance.
    history_size: How many samples to keep (one per refresh interval).
    """

    def __init__(self, tor: TorController, history_size: int = 60) -> None:
        self._tor = tor
        self._history_size = history_size

        # Circular buffers
        self._read_history:  Deque[float] = deque(maxlen=history_size)
        self._write_history: Deque[float] = deque(maxlen=history_size)

        # State for delta computation
        self._prev_read_bytes:  int   = 0
        self._prev_write_bytes: int   = 0
        self._prev_sample_time: float = 0.0

        # Latest snapshot (read by UI thread)
        self.snapshot: Optional[Snapshot] = None

        # Cache slow/static fields
        self._tor_version: Optional[str]  = None
        self._is_relay:    Optional[bool] = None
        self._version_age: float = 0.0   # monotonic time of last version fetch

    # ── Public API ────────────────────────────────────────────

    def sample(self) -> Snapshot:
        """
        Poll Tor once, compute deltas, update history, and return a
        fresh Snapshot.  Call this exactly once per refresh interval.
        """
        now = time.monotonic()

        # ── Bandwidth ────────────────────────────────────────
        raw_read, raw_write = self._tor.get_bytes_transferred()
        elapsed = now - self._prev_sample_time if self._prev_sample_time else 1.0

        read_delta  = max(0, raw_read  - self._prev_read_bytes)
        write_delta = max(0, raw_write - self._prev_write_bytes)

        read_kib_s  = read_delta  / elapsed / 1024.0
        write_kib_s = write_delta / elapsed / 1024.0

        self._prev_read_bytes  = raw_read
        self._prev_write_bytes = raw_write
        self._prev_sample_time = now

        self._read_history.append(read_kib_s)
        self._write_history.append(write_kib_s)

        # ── Circuits ─────────────────────────────────────────
        circuits = [
            CircuitInfo(
                id=c["id"],
                status=c["status"],
                purpose=c["purpose"],
                path=c["path"],
            )
            for c in self._tor.get_circuits()
        ]

        # ── Latency probe ────────────────────────────────────
        latency_ms = self._measure_latency()

        # ── Static / slow-changing fields ───────────────────
        if self._tor_version is None or (now - self._version_age) > 30:
            self._tor_version = self._tor.get_version()
            self._is_relay    = self._tor.is_relay()
            self._version_age = now

        uptime = self._tor.get_uptime()

        # ── Build snapshot ───────────────────────────────────
        snap = Snapshot(
            read_kib_s=read_kib_s,
            write_kib_s=write_kib_s,
            total_read_mib=raw_read   / (1024 * 1024),
            total_write_mib=raw_write / (1024 * 1024),
            read_history=list(self._read_history),
            write_history=list(self._write_history),
            circuits=circuits,
            latency_ms=latency_ms,
            tor_version=self._tor_version or "unknown",
            uptime_s=uptime,
            is_relay=self._is_relay or False,
        )
        self.snapshot = snap
        return snap

    # ── Private helpers ───────────────────────────────────────

    def _measure_latency(self) -> Optional[float]:
        """
        Estimate control-port round-trip latency in milliseconds.

        We time a lightweight GETINFO call.  The result is a proxy
        for responsiveness, not true circuit latency.
        """
        try:
            t0 = time.perf_counter()
            self._tor.get_uptime()    # lightweight, single response
            t1 = time.perf_counter()
            return (t1 - t0) * 1000.0
        except Exception:   # noqa: BLE001
            return None

    # ── Utility ───────────────────────────────────────────────

    @staticmethod
    def format_uptime(seconds: int) -> str:
        """Convert seconds → 'Xd Xh Xm Xs'."""
        d, rem = divmod(seconds, 86400)
        h, rem = divmod(rem, 3600)
        m, s   = divmod(rem, 60)
        parts  = []
        if d: parts.append(f"{d}d")
        if h: parts.append(f"{h}h")
        if m: parts.append(f"{m}m")
        parts.append(f"{s}s")
        return " ".join(parts)
