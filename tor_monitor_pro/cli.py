"""CLI entry point and setup checker."""

import argparse
import asyncio
import sys
import os
from pathlib import Path
from typing import Optional
import logging

from .config import Config
from .controller import MultiRelayController
from .database import Database
from .ui.tui import TorMonitorTUI
from .api.server import create_api_server
from .prometheus import PrometheusExporter
from .alerts import AlertManager, EmailNotifier, SlackNotifier, PagerDutyNotifier
from .anomaly import AnomalyDetector
from .audit import AuditLogger
from .plugins import PluginManager


logger = logging.getLogger(__name__)


def setup_logging(debug: bool = False):
    """Configure logging."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stderr),
            logging.FileHandler("tor_monitor.log")
        ]
    )


def create_arg_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="tor-monitor-pro",
        description="Professional Tor relay monitoring with multi-relay support, alerts, and enterprise features"
    )
    
    parser.add_argument(
        "--config", "-c",
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
        "--web",
        action="store_true",
        help="Start web dashboard and API server"
    )
    
    parser.add_argument(
        "--tui",
        action="store_true",
        default=True,
        help="Start TUI dashboard (default)"
    )
    
    parser.add_argument(
        "--no-tui",
        action="store_true",
        help="Disable TUI (useful for headless mode)"
    )
    
    parser.add_argument(
        "--relay-name",
        type=str,
        default=None,
        help="Name for this relay instance"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="Tor Monitor Pro 1.0.0"
    )
    
    return parser


async def run_monitor(config: Config, use_tui: bool, use_web: bool):
    """Run the monitor with selected interfaces."""
    
    # Initialize database
    db = Database(
        url=config.database.url,
        pool_size=config.database.pool_size,
        retention_days=config.database.retention_days
    )
    db.init_db()
    logger.info(f"Database initialized: {config.database.url}")
    
    # Initialize controller
    controller = MultiRelayController()
    
    # Add default relay
    await controller.add_relay(
        name=config.relay_name,
        host=config.tor.host,
        port=config.tor.port,
        password=config.tor.password,
        cookie_path=config.tor.cookie_path
    )
    
    relay = controller.get_relay(config.relay_name)
    if not relay.is_connected:
        logger.error(f"Failed to connect to relay: {relay.error}")
        sys.exit(1)
    
    # Get or create relay in DB
    db_relay = db.get_or_create_relay(
        name=config.relay_name,
        fingerprint=relay.fingerprint,
        host=config.tor.host,
        port=config.tor.port
    )
    
    # Initialize alert manager
    alert_manager = AlertManager(config.model_dump())
    
    # Setup notification channels
    if config.alerts.email_smtp_host and config.alerts.email_to:
        email_notifier = EmailNotifier(
            smtp_host=config.alerts.email_smtp_host,
            smtp_port=config.alerts.email_smtp_port,
            from_addr=config.alerts.email_from,
            to_addrs=config.alerts.email_to
        )
        alert_manager.add_callback(email_notifier)
        logger.info("Email notifications enabled")
    
    if config.alerts.slack_webhook:
        slack_notifier = SlackNotifier(config.alerts.slack_webhook)
        alert_manager.add_callback(lambda a: asyncio.create_task(slack_notifier(a)))
        logger.info("Slack notifications enabled")
    
    if config.alerts.pagerduty_key:
        pd_notifier = PagerDutyNotifier(config.alerts.pagerduty_key)
        alert_manager.add_callback(lambda a: asyncio.create_task(pd_notifier(a)))
        logger.info("PagerDuty notifications enabled")
    
    # Initialize anomaly detector
    anomaly_detector = AnomalyDetector(
        threshold=config.security.anomaly_threshold
    ) if config.security.enable_anomaly_detection else None
    
    # Initialize audit logger
    audit_logger = AuditLogger(
        log_path=config.security.audit_log_path,
        retention_days=config.security.audit_retention_days
    )
    
    # Initialize Prometheus exporter
    prometheus = PrometheusExporter() if config.web.enable_prometheus else None
    
    # Initialize plugin manager
    plugin_manager = PluginManager()
    plugin_count = plugin_manager.load_plugins(config.model_dump())
    logger.info(f"Loaded {plugin_count} plugins")
    
    # Start web server if requested
    web_task = None
    if use_web:
        app = create_api_server(
            config=config,
            controller=controller,
            database=db,
            alert_manager=alert_manager,
            anomaly_detector=anomaly_detector,
            audit_logger=audit_logger,
            prometheus=prometheus,
            plugin_manager=plugin_manager
        )
        
        import uvicorn
        web_config = uvicorn.Config(
            app,
            host=config.web.host,
            port=config.web.port,
            log_level="info"
        )
        web_server = uvicorn.Server(web_config)
        web_task = asyncio.create_task(web_server.serve())
        logger.info(f"Web server starting on {config.web.host}:{config.web.port}")
    
    # Start TUI if requested
    if use_tui:
        tui = TorMonitorTUI(
            config=config,
            controller=controller,
            database=db,
            alert_manager=alert_manager,
            anomaly_detector=anomaly_detector,
            prometheus=prometheus
        )
        
        try:
            await tui.run()
        except KeyboardInterrupt:
            pass
        finally:
            if web_task:
                web_task.cancel()
                try:
                    await web_task
                except asyncio.CancelledError:
                    pass
    elif web_task:
        # Headless mode with web only
        try:
            await web_task
        except KeyboardInterrupt:
            pass
    
    # Cleanup
    controller.close_all()
    plugin_manager.unload_all()
    logger.info("Tor Monitor Pro shutdown complete")


def main():
    """Main entry point."""
    parser = create_arg_parser()
    args = parser.parse_args()
    
    setup_logging(args.debug)
    
    # Load configuration
    try:
        config = Config()
        
        # Override with CLI args
        if args.host:
            config.tor.host = args.host
        if args.port:
            config.tor.port = args.port
        if args.password:
            config.tor.password = args.password
        if args.relay_name:
            config.relay_name = args.relay_name
        if args.debug:
            config.debug = True
        
        # Validate secret key
        if not config.security.secret_key:
            logger.error("TOR_MONITOR_SECRET_KEY environment variable is required")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    
    use_tui = args.tui and not args.no_tui
    use_web = args.web or config.web.enable_dashboard
    
    # Check for TTY if TUI requested
    if use_tui and not sys.stdout.isatty():
        logger.warning("No TTY detected, disabling TUI")
        use_tui = False
    
    try:
        asyncio.run(run_monitor(config, use_tui, use_web))
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


def check_setup():
    """Pre-flight setup checker."""
    from . import check_setup as checker
    checker.run_checks()


if __name__ == "__main__":
    main()