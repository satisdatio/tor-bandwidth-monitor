"""Pre-flight setup validation."""

import sys
import socket
from pathlib import Path
from typing import List, Tuple
import logging

try:
    from stem.control import Controller
    from stem.connection import connect, AuthenticationFailure
    STEM_AVAILABLE = True
except ImportError:
    STEM_AVAILABLE = False

try:
    import rich
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


def check_python() -> Tuple[bool, str]:
    """Check Python version."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        return False, f"Python 3.9+ required, got {version.major}.{version.minor}"
    return True, f"Python {version.major}.{version.minor}.{version.micro}"


def check_stem() -> Tuple[bool, str]:
    """Check stem library."""
    if not STEM_AVAILABLE:
        return False, "stem library not installed"
    
    try:
        import stem
        return True, f"stem {stem.__version__}"
    except Exception as e:
        return False, f"stem import error: {e}"


def check_rich() -> Tuple[bool, str]:
    """Check Rich library."""
    if not RICH_AVAILABLE:
        return False, "rich library not installed"
    
    try:
        return True, f"rich {rich.__version__}"
    except Exception as e:
        return False, f"rich import error: {e}"


def check_control_port(host: str = "127.0.0.1", port: int = 9051) -> Tuple[bool, str]:
    """Check Tor control port."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            return True, f"Control port {host}:{port} reachable"
        else:
            return False, f"Control port {host}:{port} not reachable"
    except Exception as e:
        return False, f"Connection error: {e}"


def check_authentication(host: str = "127.0.0.1", port: int = 9051, 
                        password: str = None) -> Tuple[bool, str]:
    """Check Tor control port authentication."""
    try:
        from stem import Controller
        from stem.connection import connect
        
        controller = connect(host=host, port=port, password=password)
        controller.close()
        return True, "Authentication successful"
    except Exception as e:
        return False, f"Authentication failed: {e}"
from .database import Database
from .controller import MultiRelayController
from .metrics import MetricsCollector
from .alerts import AlertManager, EmailNotifier, SlackNotifier, PagerDutyNotifier
from .prometheus import PrometheusExporter
from .anomaly import AnomalyDetector
from .audit import AuditLogger
from .plugins import PluginManager
from .latency import CircuitLatencyProbe
from .ui.tui import TorMonitorTUI
from .api.server import create_api_server

logger = logging.getLogger(__name__)


class TorMonitorApp:
    """Main application orchestrator."""
    
    def __init__(self, config: Config):
        self.config = config
        self.running = False
        
        # Initialize core components
        self.db = Database(
            url=config.database.url,
            pool_size=config.database.pool_size,
            retention_days=config.database.retention_days
        )
        
        self.controller = MultiRelayController()
        self.metrics = MetricsCollector()
        self.alerts = AlertManager({})
        self.prometheus = PrometheusExporter()
        self.anomaly = AnomalyDetector(threshold=config.security.anomaly_threshold)
        self.audit = AuditLogger(
            log_path=config.security.audit_log_path,
            retention_days=config.security.audit_retention_days
        )
        self.plugins = PluginManager()
        self.latency_probe = CircuitLatencyProbe()
        
        # Notification channels
        self._setup_notifiers()
        
        # API server (lazy init)
        self._api_server: Optional[uvicorn.Server] = None
    
    def _setup_notifiers(self):
        """Configure notification channels from config."""
        alerts = self.config.alerts
        
        if alerts.email_smtp_host and alerts.email_to:
            self.alerts.add_callback(EmailNotifier(
                smtp_host=alerts.email_smtp_host,
                smtp_port=alerts.email_smtp_port,
                from_addr=alerts.email_from or "tor-monitor@localhost",
                to_addrs=alerts.email_to
            ))
        
        if alerts.slack_webhook:
            self.alerts.add_callback(SlackNotifier(alerts.slack_webhook))
        
        if alerts.pagerduty_key:
            self.alerts.add_callback(PagerDutyNotifier(alerts.pagerduty_key))
    
    def initialize(self):
        """Initialize all components."""
        logger.info("Initializing Tor Monitor Pro...")
        
        # Initialize database
        self.db.init_db()
        
        # Load plugins
        plugin_count = self.plugins.load_plugins({})
        logger.info(f"Loaded {plugin_count} plugins")
        
        # Add default relay
        tor = self.config.tor
        asyncio.get_event_loop().run_until_complete(
            self.controller.add_relay(
                name=self.config.relay_name,
                host=tor.host,
                port=tor.port,
                password=tor.password,
                cookie_path=tor.cookie_path
            )
        )
        
        # Register alert callback for database storage
        self.alerts.add_callback(self._store_alert)
        
        logger.info("Initialization complete")
    
    def _store_alert(self, alert):
        """Store alert in database."""
        relay = self.controller.get_relay(self.config.relay_name)
        if relay:
            self.db.store_alert(
                relay_id=relay.id if hasattr(relay, 'id') else 1,
                alert_type=alert.alert_type.value,
                severity=alert.severity.value,
                message=alert.message,
                metrics=alert.metrics
            )
    
    async def run_tui(self):
        """Run the TUI dashboard."""
        logger.info("Starting TUI dashboard...")
        
        tui = TorMonitorTUI(
            config=self.config,
            controller=self.controller,
            metrics=self.metrics,
            alerts=self.alerts,
            anomaly=self.anomaly,
            db=self.db,
            refresh_interval=self.config.refresh_interval
        )
        
        await tui.run()
    
    async def run_web(self):
        """Run the web dashboard and API server."""
        logger.info(f"Starting web server on {self.config.web.host}:{self.config.web.port}")
        
        app = create_api_server(
            config=self.config,
            db=self.db,
            controller=self.controller,
            metrics=self.metrics,
            alerts=self.alerts,
            prometheus=self.prometheus,
            anomaly=self.anomaly,
            audit=self.audit,
            plugins=self.plugins
        )
        
        config = uvicorn.Config(
            app,
            host=self.config.web.host,
            port=self.config.web.port,
            log_level="info" if not self.config.debug else "debug",
            access_log=True
        )
        
        self._api_server = uvicorn.Server(config)
        await self._api_server.serve()
    
    async def run_background(self):
        """Run background monitoring without UI."""
        logger.info("Running in background mode...")
        
        while self.running:
            await self._collect_metrics()
            await asyncio.sleep(self.config.refresh_interval)
    
    async def _collect_metrics(self):
        """Collect and process metrics from all relays."""
        for relay_name in self.controller.relays:
            raw_metrics = self.controller.get_metrics(relay_name)
            
            if raw_metrics:
                # Process metrics
                snapshot = self.metrics.process(raw_metrics)
                
                # Store in database
                relay = self.controller.get_relay(relay_name)
                if relay and hasattr(relay, 'id'):
                    self.db.store_metric(
                        relay_id=relay.id,
                        read_bytes=snapshot.read_bytes,
                        write_bytes=snapshot.write_bytes,
                        read_rate_kibs=snapshot.read_rate_kibs,
                        write_rate_kibs=snapshot.write_rate_kibs,
                        circuit_count=snapshot.circuit_count,
                        latency_ms=snapshot.latency_ms
                    )
                
                # Update Prometheus
                self.prometheus.update_bandwidth(
                    relay=relay_name,
                    read_rate=snapshot.read_rate_kibs,
                    write_rate=snapshot.write_rate_kibs
                )
                self.prometheus.update_circuits(
                    relay=relay_name,
                    count=snapshot.circuit_count
                )
                self.prometheus.update_latency(
                    relay=relay_name,
                    latency_ms=snapshot.latency_ms
                )
                
                # Check alerts
                alert_context = {
                    **snapshot.to_dict(),
                    "read_rate_avg": self.metrics.get_average_read_rate(),
                    "latency_threshold": 500
                }
                triggered = self.alerts.evaluate(alert_context)
                
                # Check anomalies
                if self.config.security.enable_anomaly_detection:
                    anomalies = self.anomaly.analyze_metrics(raw_metrics)
                    for anomaly in anomalies:
                        logger.warning(f"Anomaly detected: {anomaly.message}")
                        self.prometheus.update_anomaly(
                            relay=relay_name,
                            anomaly_type=anomaly.anomaly_type,
                            severity=anomaly.severity
                        )
                
                # Plugin exports
                self.plugins.export_data(snapshot.to_dict())
    
    async def start(self, mode: str = "tui"):
        """Start the application in specified mode."""
        self.running = True
        self.initialize()
        
        # Start background collection
        background_task = asyncio.create_task(self.run_background())
        
        try:
            if mode == "web":
                await self.run_web()
            elif mode == "tui":
                await self.run_tui()
            else:
                await background_task
        except KeyboardInterrupt:
            logger.info("Shutdown requested...")
        finally:
            self.running = False
            background_task.cancel()
            try:
                await background_task
            except asyncio.CancelledError:
                pass
            
            self.controller.close_all()
            self.plugins.unload_all()
            logger.info("Shutdown complete")
    
    def stop(self):
        """Stop the application."""
        self.running = False


def run_checks() -> bool:
    """Run all pre-flight checks and return overall status."""
    print("🔍 Running Tor Monitor Pro pre-flight checks...\n")
    
    checks = [
        ("Python Version", check_python()),
        ("Stem Library", check_stem()),
        ("Rich Library", check_rich()),
        ("Tor Control Port", check_control_port()),
    ]
    
    # Try authentication check if control port is reachable
    control_check = None
    for name, (passed, message) in checks:
        if name == "Tor Control Port" and passed:
            control_check = ("Tor Authentication", check_authentication())
            break
    
    if control_check:
        checks.append(control_check)
    
    all_passed = True
    for name, (passed, message) in checks:
        status = "✅" if passed else "❌"
        color = "[green]" if passed else "[red]"
        print(f"{status} {name}: {color}{message}[/reset]")
        if not passed:
            all_passed = False
    
    print(f"\n{'🎉 All checks passed!' if all_passed else '❌ Some checks failed. Please resolve issues before running.'}")
    return all_passed


def check_setup():
    """Pre-flight environment validation."""
    return run_checks()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="tor-monitor-pro",
        description="Professional Tor relay monitoring with multi-relay support, alerts, and enterprise features"
    )
    
    parser.add_argument(
        "--mode",
        choices=["tui", "web", "background"],
        default="tui",
        help="Run mode: tui, web, or background (default: tui)"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to configuration file"
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Tor control host (overrides config)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Tor control port (overrides config)"
    )
    
    parser.add_argument(
        "--password",
        type=str,
        default=None,
        help="Tor control password (overrides config)"
    )
    
    parser.add_argument(
        "--refresh",
        type=float,
        default=None,
        help="Refresh interval in seconds (overrides config)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run pre-flight checks and exit"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0"
    )
    
    args = parser.parse_args()
    
    # Run pre-flight checks
    if args.check:
        sys.exit(0 if check_setup() else 1)
    
    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("tor-monitor.log")
        ]
    )
    
    # Load configuration
    config = Config()
    
    # Override with CLI args
    if args.host:
        config.tor.host = args.host
    if args.port:
        config.tor.port = args.port
    if args.password:
        config.tor.password = args.password
    if args.refresh:
        config.refresh_interval = args.refresh
    if args.debug:
        config.debug = True
    
    # Setup signal handlers
    app = TorMonitorApp(config)
    
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        app.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run application
    try:
        asyncio.run(app.start(mode=args.mode))
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()