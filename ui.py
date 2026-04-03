"""
tor_monitor/ui.py
────────────────────────────────────────────────────────────────
Rich-based dashboard.

Layout overview
───────────────
┌──────────────── HEADER (title + Tor info) ─────────────────┐
│                                                             │
│  ┌─ METRICS PANEL ──┐  ┌─ SPARKLINES ────────────────────┐ │
│  │ ↓ Read  X KiB/s  │  │ ▁▂▄▆█▇▅▃▂▁  Download           │ │
│  │ ↑ Write X KiB/s  │  │ ▁▁▂▃▄▃▂▁▁▁  Upload             │ │
│  │ ⧗ Latency X ms   │  └────────────────────────────────┘ │
│  │ ↕ Total R/W      │                                      │
│  └──────────────────┘                                      │
│                                                             │
│  ┌─ CIRCUIT TABLE ─────────────────────────────────────── ┐ │
│  │  ID  │ Hops │ Purpose │ Status │ Path                   │ │
│  │  …   │  …   │  …      │  …     │  …                    │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
└──────────────── FOOTER (keybindings) ──────────────────────┘

All Rich renderables are rebuilt from scratch each frame;
no state is stored in UI objects.
"""

from __future__ import annotations

import math
import time
from typing import List, Optional

from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.console import Group
from rich.layout import Layout
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from tor_monitor.controller import TorController
from tor_monitor.metrics import MetricsCollector, Snapshot

# ── Sparkline character sets ──────────────────────────────────
_SPARK_CHARS = " ▁▂▃▄▅▆▇█"   # 9 levels (index 0 = empty)


def _sparkline(values: List[float], width: int = 40) -> str:
    """
    Render a unicode braille-style bar sparkline.

    Parameters
    ----------
    values: List of float values (oldest first, newest last).
    width:  Max number of characters to render.

    Returns a string of block characters representing the values.
    """
    if not values:
        return _SPARK_CHARS[0] * width

    # Trim / pad to `width`
    data = values[-width:] if len(values) > width else values
    peak = max(data) if max(data) > 0 else 1.0
    chars = []
    for v in data:
        idx = int((v / peak) * (len(_SPARK_CHARS) - 1))
        chars.append(_SPARK_CHARS[max(0, min(idx, len(_SPARK_CHARS) - 1))])

    return "".join(chars)


# ── Colour helpers ────────────────────────────────────────────

def _kib_colour(kib: float) -> str:
    """Traffic-light colour based on throughput."""
    if kib < 10:
        return "dim white"
    if kib < 100:
        return "green"
    if kib < 512:
        return "yellow"
    return "red"


def _latency_colour(ms: Optional[float]) -> str:
    if ms is None:
        return "dim"
    if ms < 10:
        return "bright_green"
    if ms < 50:
        return "green"
    if ms < 150:
        return "yellow"
    return "red"


def _status_colour(status: str) -> str:
    mapping = {
        "BUILT":    "bright_green",
        "EXTENDED": "yellow",
        "LAUNCHED": "cyan",
        "FAILED":   "red",
        "CLOSED":   "dim",
    }
    return mapping.get(status.upper(), "white")


# ── Main UI class ─────────────────────────────────────────────

class DashboardUI:
    """
    Stateless view layer.  build() constructs a full Rich renderable
    from the latest MetricsCollector snapshot every call.

    Parameters
    ----------
    metrics:      Live MetricsCollector instance.
    tor:          Connected TorController (used for static info).
    history_size: Width of sparklines in characters.
    """

    def __init__(
        self,
        metrics: MetricsCollector,
        tor: TorController,
        history_size: int = 60,
    ) -> None:
        self._metrics = metrics
        self._tor     = tor
        self._history_size = history_size

    # ── Public entry-point ────────────────────────────────────

    def build(self):
        """Return a Rich renderable representing the full dashboard."""
        snap = self._metrics.snapshot
        if snap is None:
            return Panel("[dim]Waiting for first sample…[/dim]", title="Tor Monitor")

        return Group(
            self._render_header(snap),
            self._render_middle_row(snap),
            self._render_circuit_table(snap),
            self._render_footer(),
        )

    # ── Header ────────────────────────────────────────────────

    def _render_header(self, snap: Snapshot) -> Panel:
        title_text = Text("⬤  Tor Bandwidth Monitor", style="bold bright_cyan")
        title_text.append("  │  ", style="dim")
        title_text.append(f"Tor {snap.tor_version}", style="cyan")

        uptime = MetricsCollector.format_uptime(snap.uptime_s)
        title_text.append("  │  uptime ", style="dim")
        title_text.append(uptime, style="bright_white")

        role = "relay" if snap.is_relay else "client"
        title_text.append(f"  │  mode: ", style="dim")
        title_text.append(role, style="magenta" if snap.is_relay else "white")

        ts = time.strftime("%H:%M:%S")
        title_text.append(f"  │  {ts}", style="dim")

        return Panel(Align.center(title_text), style="bold", box=box.HEAVY_HEAD)

    # ── Middle row: metrics + sparklines ──────────────────────

    def _render_middle_row(self, snap: Snapshot):
        metrics_panel  = self._render_metrics_panel(snap)
        sparkline_panel = self._render_sparklines(snap)
        return Columns([metrics_panel, sparkline_panel], equal=True, expand=True)

    def _render_metrics_panel(self, snap: Snapshot) -> Panel:
        t = Table.grid(padding=(0, 1))
        t.add_column(justify="right",  style="dim", no_wrap=True)
        t.add_column(justify="left",   no_wrap=True)

        # Download
        dl_colour = _kib_colour(snap.read_kib_s)
        t.add_row(
            "↓ Download",
            Text(f"{snap.read_kib_s:>8.2f} KiB/s", style=f"bold {dl_colour}"),
        )
        # Upload
        ul_colour = _kib_colour(snap.write_kib_s)
        t.add_row(
            "↑ Upload   ",
            Text(f"{snap.write_kib_s:>8.2f} KiB/s", style=f"bold {ul_colour}"),
        )

        # Blank spacer
        t.add_row("", "")

        # Totals
        t.add_row(
            "↕ Total ↓",
            Text(f"{snap.total_read_mib:>8.3f} MiB", style="cyan"),
        )
        t.add_row(
            "↕ Total ↑",
            Text(f"{snap.total_write_mib:>8.3f} MiB", style="cyan"),
        )

        t.add_row("", "")

        # Latency
        lat_str  = f"{snap.latency_ms:.1f} ms" if snap.latency_ms is not None else "N/A"
        lat_col  = _latency_colour(snap.latency_ms)
        t.add_row(
            "⧗ Latency ",
            Text(lat_str, style=f"bold {lat_col}"),
        )

        # Circuits count
        t.add_row(
            "⊕ Circuits",
            Text(str(len(snap.circuits)), style="bright_white"),
        )

        return Panel(t, title="[bold]Metrics[/bold]", border_style="cyan", box=box.ROUNDED)

    def _render_sparklines(self, snap: Snapshot) -> Panel:
        width = self._history_size

        dl_spark = _sparkline(snap.read_history,  width)
        ul_spark = _sparkline(snap.write_history, width)

        peak_dl = max(snap.read_history)  if snap.read_history  else 0
        peak_ul = max(snap.write_history) if snap.write_history else 0

        # Build text blocks with colour gradients
        dl_text = Text()
        dl_label = Text(f" ↓ Download  peak: {peak_dl:.1f} KiB/s\n", style="dim")
        dl_bar   = Text(dl_spark, style=_kib_colour(snap.read_kib_s))

        ul_label = Text(f"\n ↑ Upload    peak: {peak_ul:.1f} KiB/s\n", style="dim")
        ul_bar   = Text(ul_spark, style=_kib_colour(snap.write_kib_s))

        spark_group = Group(dl_label, dl_bar, ul_label, ul_bar)

        # Mini bar-chart: last 10 samples as thin vertical bars
        bar_section = self._render_mini_bars(snap)

        return Panel(
            Group(spark_group, Rule(style="dim"), bar_section),
            title="[bold]Bandwidth History[/bold]",
            border_style="cyan",
            box=box.ROUNDED,
        )

    def _render_mini_bars(self, snap: Snapshot) -> Text:
        """Render a compact two-row bar chart of the last 10 samples."""
        BAR_CHARS = "▏▎▍▌▋▊▉█"
        N = 12
        dl = snap.read_history[-N:]  if snap.read_history  else []
        ul = snap.write_history[-N:] if snap.write_history else []

        peak = max((max(dl) if dl else 0), (max(ul) if ul else 0), 1)

        def bar(v: float, colour: str) -> Text:
            norm  = v / peak
            idx   = int(norm * (len(BAR_CHARS) - 1))
            char  = BAR_CHARS[max(0, min(idx, len(BAR_CHARS) - 1))]
            width = max(1, int(norm * 6))
            return Text(char * width, style=colour)

        t = Table.grid(padding=(0, 0))
        for i in range(max(len(dl), len(ul))):
            dl_v = dl[i] if i < len(dl) else 0
            ul_v = ul[i] if i < len(ul) else 0
            t.add_column()

        row_dl, row_ul = [], []
        for i in range(max(len(dl), len(ul))):
            dl_v = dl[i] if i < len(dl) else 0.0
            ul_v = ul[i] if i < len(ul) else 0.0
            row_dl.append(bar(dl_v, "green"))
            row_ul.append(bar(ul_v, "yellow"))

        if row_dl:
            t.add_row(*row_dl)
        if row_ul:
            t.add_row(*row_ul)

        label = Text(" Last 12 samples  ", style="dim")
        return Group(label, t)

    # ── Circuit table ─────────────────────────────────────────

    def _render_circuit_table(self, snap: Snapshot) -> Panel:
        table = Table(
            box=box.SIMPLE_HEAVY,
            show_edge=True,
            header_style="bold bright_cyan",
            expand=True,
        )

        table.add_column("ID",      style="dim",          width=6,  no_wrap=True)
        table.add_column("Hops",    justify="center",     width=5)
        table.add_column("Purpose", style="magenta",      width=14, no_wrap=True)
        table.add_column("Status",                        width=10, no_wrap=True)
        table.add_column("Path (Guard → Middle → Exit)", ratio=1)

        if not snap.circuits:
            table.add_row(
                "—", "—", "—", "—",
                Text("No BUILT circuits yet …", style="dim italic"),
            )
        else:
            for circ in snap.circuits:
                status_text = Text(circ.status, style=_status_colour(circ.status))
                table.add_row(
                    circ.id,
                    str(circ.hop_count),
                    circ.purpose,
                    status_text,
                    self._coloured_path(circ.path),
                )

        return Panel(
            table,
            title=f"[bold]Active Circuits[/bold]  ({len(snap.circuits)} built)",
            border_style="cyan",
            box=box.ROUNDED,
        )

    @staticmethod
    def _coloured_path(path: list) -> Text:
        """
        Render circuit path with alternating colours for readability:
          Guard (green) → Middle (yellow) → Exit (red)
        """
        colours = ["bright_green", "yellow", "red"]
        text    = Text()
        for i, (fp, nick) in enumerate(path):
            label  = nick if nick else fp[:8]
            colour = colours[min(i, len(colours) - 1)]
            if i:
                text.append(" → ", style="dim")
            text.append(label, style=colour)
        return text if text else Text("—", style="dim")

    # ── Footer ────────────────────────────────────────────────

    @staticmethod
    def _render_footer() -> Panel:
        keys = Text()
        keys.append("  Ctrl-C", style="bold yellow")
        keys.append(" quit   ", style="dim")
        keys.append("  Auto-refresh every 1 s  ", style="dim")
        keys.append("  Colour: ", style="dim")
        keys.append("●", style="bright_green")
        keys.append(" fast  ", style="dim")
        keys.append("●", style="yellow")
        keys.append(" medium  ", style="dim")
        keys.append("●", style="red")
        keys.append(" slow", style="dim")
        return Panel(Align.center(keys), style="dim", box=box.HORIZONTALS)
