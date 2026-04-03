"""True circuit latency measurement via SOCKS5 probes."""

import asyncio
import time
import socket
from typing import Optional, Dict, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class LatencyResult:
    """Latency measurement result."""
    latency_ms: float
    success: bool
    circuit_id: Optional[int] = None
    exit_relay: Optional[str] = None
    error: Optional[str] = None


class CircuitLatencyProbe:
    """
    Measures true circuit latency by creating SOCKS5 connections
    through Tor circuits to known endpoints.
    """
    
    TEST_ENDPOINTS = [
        ("8.8.8.8", 53),      # Google DNS
        ("1.1.1.1", 53),      # Cloudflare DNS
        ("9.9.9.9", 53),      # Quad9 DNS
    ]
    
    def __init__(self, socks_host: str = "127.0.0.1", 
                 socks_port: int = 9050, timeout: float = 10.0):
        self.socks_host = socks_host
        self.socks_port = socks_port
        self.timeout = timeout
        self._results: List[LatencyResult] = []
    
    async def probe_circuit(self, circuit_id: Optional[int] = None) -> LatencyResult:
        """
        Probe latency through a specific circuit or any available circuit.
        
        Args:
            circuit_id: Optional circuit ID to use (via circuit isolation)
        
        Returns:
            LatencyResult with measurement data
        """
        start_time = time.perf_counter()
        
        try:
            # Create SOCKS5 connection
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.socks_host, self.socks_port),
                timeout=self.timeout
            )
            
            # SOCKS5 handshake
            await self._socks5_handshake(reader, writer)
            
            # Try each test endpoint
            for host, port in self.TEST_ENDPOINTS:
                try:
                    await self._socks5_connect(reader, writer, host, port)
                    
                    # Send minimal DNS query
                    dns_query = b"\x00\x01\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
                    writer.write(dns_query)
                    await writer.drain()
                    
                    # Wait for response
                    await asyncio.wait_for(reader.read(512), timeout=2.0)
                    
                    elapsed = (time.perf_counter() - start_time) * 1000
                    writer.close()
                    await writer.wait_closed()
                    
                    result = LatencyResult(
                        latency_ms=elapsed,
                        success=True,
                        circuit_id=circuit_id,
                        exit_relay=None  # Would need controller to determine
                    )
                    self._results.append(result)
                    return result
                    
                except Exception:
                    continue
            
            # All endpoints failed
            writer.close()
            await writer.wait_closed()
            return LatencyResult(
                latency_ms=0,
                success=False,
                error="All test endpoints unreachable"
            )
            
        except asyncio.TimeoutError:
            return LatencyResult(
                latency_ms=0,
                success=False,
                error="Connection timeout"
            )
        except Exception as e:
            return LatencyResult(
                latency_ms=0,
                success=False,
                error=str(e)
            )
    
    async def _socks5_handshake(self, reader, writer):
        """Perform SOCKS5 handshake."""
        # Send version identifier/method selection
        writer.write(b"\x05\x01\x00")  # SOCKS5, 1 method, no auth
        await writer.drain()
        
        # Read method selection
        response = await reader.read(2)
        if len(response) != 2 or response[0] != 0x05:
            raise Exception("Invalid SOCKS5 response")
        if response[1] != 0x00:
            raise Exception("SOCKS5 authentication required")
    
    async def _socks5_connect(self, reader, writer, host: str, port: int):
        """Send SOCKS5 CONNECT request."""
        # Try to parse as IP
        try:
            ip_bytes = socket.inet_aton(host)
            request = b"\x05\x01\x00\x01" + ip_bytes + port.to_bytes(2, "big")
        except socket.error:
            # Hostname
            host_bytes = host.encode("ascii")
            request = b"\x05\x01\x00\x03" + bytes([len(host_bytes)]) + host_bytes + port.to_bytes(2, "big")
        
        writer.write(request)
        await writer.drain()
        
        # Read response
        response = await reader.read(10)
        if len(response) < 2 or response[0] != 0x05 or response[1] != 0x00:
            raise Exception(f"SOCKS5 connect failed: {response}")
    
    async def probe_multiple(self, count: int = 3) -> Dict[str, float]:
        """
        Run multiple probes and return statistics.
        
        Returns:
            Dictionary with min, max, avg, p95 latency values
        """
        results = await asyncio.gather(
            *[self.probe_circuit() for _ in range(count)],
            return_exceptions=True
        )
        
        latencies = [
            r.latency_ms for r in results 
            if isinstance(r, LatencyResult) and r.success
        ]
        
        if not latencies:
            return {"error": "No successful probes"}
        
        latencies.sort()
        return {
            "min_ms": min(latencies),
            "max_ms": max(latencies),
            "avg_ms": sum(latencies) / len(latencies),
            "p50_ms": latencies[len(latencies) // 2],
            "p95_ms": latencies[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[-1],
            "sample_count": len(latencies)
        }
    
    def get_recent_results(self, limit: int = 100) -> List[LatencyResult]:
        """Get recent latency results."""
        return self._results[-limit:]