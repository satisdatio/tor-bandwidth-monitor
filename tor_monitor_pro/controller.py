"""Enhanced Tor controller with multi-relay support."""

import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from stem.control import Controller
from stem.connection import connect, connect_port
from stem.response import events
import logging

logger = logging.getLogger(__name__)


@dataclass
class RelayConnection:
    """Represents a connection to a Tor relay."""
    name: str
    host: str
    port: int
    controller: Optional[Controller] = None
    is_connected: bool = False
    error: Optional[str] = None
    fingerprint: Optional[str] = None
    version: Optional[str] = None
    uptime: Optional[float] = None


class MultiRelayController:
    """
    Controller supporting multiple Tor relay connections.
    
    Enables monitoring of relay fleets from a single dashboard.
    """
    
    def __init__(self):
        self.relays: Dict[str, RelayConnection] = {}
        self._event_callbacks: Dict[str, List[callable]] = {}
    
    async def add_relay(self, name: str, host: str, port: int,
                       password: str = None, cookie_path: str = None) -> RelayConnection:
        """
        Add a relay to monitor.
        
        Args:
            name: Unique relay identifier
            host: Control port host
            port: Control port number
            password: Optional password
            cookie_path: Optional cookie file path
        
        Returns:
            RelayConnection with connection status
        """
        relay = RelayConnection(name=name, host=host, port=port)
        
        try:
            # Connect to control port
            if host in ("127.0.0.1", "localhost"):
                controller = connect(port=port, password=password, cookie_path=cookie_path)
            else:
                controller = connect_port(host, port, password=password)
            
            relay.controller = controller
            relay.is_connected = True
            
            # Get relay info
            try:
                relay.fingerprint = controller.get_info("fingerprint", None)
                relay.version = controller.get_info("version", None)
                uptime_str = controller.get_info("uptime", "0")
                relay.uptime = float(uptime_str)
            except Exception:
                pass
            
            logger.info(f"Connected to relay {name} at {host}:{port}")
            
        except Exception as e:
            relay.error = str(e)
            logger.error(f"Failed to connect to relay {name}: {e}")
        
        self.relays[name] = relay
        return relay
    
    async def remove_relay(self, name: str):
        """Remove a relay from monitoring."""
        if name in self.relays:
            relay = self.relays[name]
            if relay.controller:
                try:
                    relay.controller.close()
                except Exception:
                    pass
            del self.relays[name]
    
    def get_relay(self, name: str) -> Optional[RelayConnection]:
        """Get relay by name."""
        return self.relays.get(name)
    
    def get_connected_relays(self) -> List[RelayConnection]:
        """Get all connected relays."""
        return [r for r in self.relays.values() if r.is_connected]
    
    def get_metrics(self, relay_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metrics for a specific relay.
        
        Returns:
            Dictionary with bandwidth, circuits, latency, etc.
        """
        relay = self.relays.get(relay_name)
        if not relay or not relay.controller:
            return None
        
        try:
            controller = relay.controller
            
            # Bandwidth
            read_bytes = int(controller.get_info("traffic/read", "0"))
            write_bytes = int(controller.get_info("traffic/write", "0"))
            
            # Circuits
            circuits = []
            for circ in controller.get_circuits():
                circuits.append({
                    "id": circ.id,
                    "status": circ.status,
                    "purpose": circ.purpose,
                    "path": [hop.nickname for hop in circ.path],
                    "path_fingerprints": [hop.fingerprint for hop in circ.path],
                    "is_hs": circ.purpose and "HS" in circ.purpose
                })
            
            # Uptime
            uptime = float(controller.get_info("uptime", "0"))
            
            # Bootstrap
            bootstrap = controller.get_info("status/bootstrap-phase", "")
            
            # Version
            version = controller.get_info("version", "unknown")
            
            return {
                "relay_name": relay_name,
                "fingerprint": relay.fingerprint,
                "version": version,
                "uptime_seconds": uptime,
                "read_bytes": read_bytes,
                "write_bytes": write_bytes,
                "circuits": circuits,
                "circuit_count": len(circuits),
                "bootstrap": bootstrap,
                "is_connected": True
            }
            
        except Exception as e:
            logger.error(f"Error getting metrics for {relay_name}: {e}")
            relay.is_connected = False
            relay.error = str(e)
            return None
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all relays."""
        return {
            name: self.get_metrics(name)
            for name in self.relays
        }
    
    def register_event_callback(self, event_type: str, callback: callable):
        """Register callback for Tor events."""
        if event_type not in self._event_callbacks:
            self._event_callbacks[event_type] = []
        self._event_callbacks[event_type].append(callback)
    
    def close_all(self):
        """Close all relay connections."""
        for relay in self.relays.values():
            if relay.controller:
                try:
                    relay.controller.close()
                except Exception:
                    pass
            relay.is_connected = False