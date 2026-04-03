"""Rich-based TUI dashboard."""

import asyncio
from datetime import datetime
from typing import Optional
from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.align import Align
from rich.style import Style

from ..config import Config
from ..controller import MultiRelayController
from ..database import Database
from ..alerts import AlertManager
from ..anomaly import AnomalyDetector
from ..prometheus import PrometheusExporter


class TorMonitorTUI:
    """Enhanced TUI dashboard with multi-relay support."""
    
    def __init__(
        self,
        config: Config,
        controller: MultiRelayController,
        database: Database,
        alert_manager: AlertManager,
        anomaly_detector: Optional[AnomalyDetector],
        prometheus: Optional[PrometheusExporter]
    ):
        self.config = config
        self.controller = controller
        self.database = database
        self.alert_manager = alert_manager
        self.anomaly_detector = anomaly_detector
        self.prometheus = prometheus
        
        self.console = Console()
        self.layout = Layout()
        self.refresh_interval = config.refresh_interval
        self.running = True
        self.selected_relay = config.relay_name
    
    async def run(self):
        """Run the TUI."""
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        self.layout["main"].split_row(
            Layout(name="metrics", ratio=1),
            Layout(name="circuits", ratio=2)
        )
        
        with Live(self.layout, console=self.console, refresh_per_second=10, screen=True):
            while self.running:
                try:
                    self._update_layout()
                    await asyncio.sleep(self.refresh_interval)
                except KeyboardInterrupt:
                    self.running = False
                except Exception as e:
                    self.console.print(f"[red]Error: {e}[/red]")
                    await asyncio.sleep(1)
    
    def _update_layout(self):
        """Update all layout sections."""
        self.layout["header"].update(self._render_header())
        self.layout["metrics"].update(self._render_metrics())
        self.layout["circuits"].update(self._render_circuits())
        self.layout["footer"].update(self._render_footer())
    
    def _render_header(self) -> Panel:
        """Render header panel."""
        relay = self.controller.get_relay(self.selected_relay)
        
        status = "[green]● Connected[/green]" if relay and relay.is_connected else "[red]● Disconnected[/red]"
        
        title = Text(f"Tor Monitor Pro v{self.config.version}", style="bold cyan")
        subtitle = Text(f"Relay: {self.selected_relay} | {status}", style="dim")
        
        header_text = Text.assemble(title, "\n", subtitle)
        
        return Panel(
            Align.center(header_text),
            style="bold",
            border_style="cyan"
        )
    
    def _render_metrics(self) -> Panel:
        """Render metrics panel."""
        metrics = self.controller.get_metrics(self.selected_relay)
        
        if not metrics:
            return Panel("[yellow]No metrics available[/yellow]", title="Metrics")
        
        table = Table.grid(padding=(0, 2))
        table.add_column(style="dim")
        table.add_column(style="bold")
        
        # Bandwidth
        read_kibs = metrics.get("read_bytes", 0) / 1024
        write_kibs = metrics.get("write_bytes", 0) / 1024
        
        table.add_row("↓ Download", f"{read_kibs:.2f} KiB/s")
        table.add_row("↑ Upload", f"{write_kibs:.2f} KiB/s")
        table.add_row("")
        
        # Circuits
        table.add_row("⊕ Circuits", str(metrics.get("circuit_count", 0)))
        table.add_row("")
        
        # Uptime
        uptime = metrics.get("uptime_seconds", 0)
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        table.add_row("⧗ Uptime", f"{hours}h {minutes}m")
        
        # Alerts
        alerts = self.alert_manager.get_active_alerts()
        critical = len([a for a in alerts if a.severity.value == "critical"])
        warning = len([a for a in alerts if a.severity.value == "warning"])
        
        table.add_row("")
        table.add_row("🚨 Critical", f"[red]{critical}[/red]" if critical else "0")
        table.add_row("⚠️  Warning", f"[yellow]{warning}[/yellow]" if warning else "0")
        
        # Anomalies
        if self.anomaly_detector:
            anomalies = self.anomaly_detector.get_recent_anomalies(limit=1)
            if anomalies:
                table.add_row("")
                table.add_row("🔍 Anomaly", f"[magenta]{anomalies[0].anomaly_type}[/magenta]")
        
        return Panel(table, title="Metrics", border_style="green")
    
    def _render_circuits(self) -> Panel:
        """Render circuits table."""
        metrics = self.controller.get_metrics(self.selected_relay)
        
        table = Table(title="Active Circuits")
        table.add_column("ID", style="cyan")
        table.add_column("Hops", justify="center")
        table.add_column("Purpose", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("Path")
        
        if metrics and "circuits" in metrics:
            for circ in metrics["circuits"]:
                path_str = " → ".join(circ.get("path", [])[:3])
                if len(circ.get("path", [])) > 3:
                    path_str += " → ..."
                
                table.add_row(
                    str(circ.get("id", "?")),
                    str(len(circ.get("path", []))),
                    circ.get("purpose", "GENERAL"),
                    circ.get("status", "UNKNOWN"),
                    path_str
                )
        
        return Panel(table, border_style="blue")
    
    def _render_footer(self) -> Panel:
        """Render footer panel."""
        footer_text = Text(
            "Ctrl+C: Quit | R: Refresh | Tab: Switch Relay | A: View Alerts",
            style="dim"
        )
        return Panel(
            Align.center(footer_text),
            style="dim",
            border_style="dim"
        )