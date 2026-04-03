"""
tor_monitor/main.py
────────────────────────────────────────────────────────────────
Entry-point for the Tor Bandwidth Monitor CLI tool.

Usage
-----
    python main.py [--host HOST] [--port PORT] [--password PASSWORD]
                   [--refresh SECONDS] [--history N]

The script wires together every sub-module and drives the Rich
Live-rendering loop.  Keep this file thin – real logic lives in
the modules under tor_monitor/.
"""

import argparse
import sys
import time

from rich.console import Console
from rich.live import Live

from tor_monitor.controller import TorController
from tor_monitor.metrics import MetricsCollector
from tor_monitor.ui import DashboardUI

# ── CLI argument parsing ──────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="tor-monitor",
        description="Live Tor bandwidth & circuit monitor (stem + Rich)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Control-port host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=9051, help="Control-port number (default: 9051)")
    parser.add_argument("--password", default=None, help="Control-port password (omit for cookie auth)")
    parser.add_argument(
        "--refresh",
        type=float,
        default=1.0,
        help="Seconds between screen refreshes (default: 1.0)",
    )
    parser.add_argument(
        "--history",
        type=int,
        default=60,
        help="Number of bandwidth samples to keep for sparkline (default: 60)",
    )
    return parser.parse_args()


# ── Bootstrap & main loop ─────────────────────────────────────

def main() -> None:
    args = parse_args()
    console = Console()

    # ── 1. Connect to Tor control port ───────────────────────
    console.print("\n[bold cyan]⟳  Connecting to Tor Control Port …[/bold cyan]")
    try:
        tor = TorController(
            host=args.host,
            port=args.port,
            password=args.password,
        )
        tor.connect()
    except Exception as exc:
        console.print(f"\n[bold red]✗  Connection failed:[/bold red] {exc}")
        console.print(
            "\n[dim]Make sure Tor is running with ControlPort enabled in torrc:\n"
            "  ControlPort 9051\n"
            "  CookieAuthentication 1   [italic](or set HashedControlPassword)[/italic][/dim]\n"
        )
        sys.exit(1)

    console.print("[bold green]✓  Connected[/bold green]\n")

    # ── 2. Initialise metrics collector & UI ─────────────────
    metrics = MetricsCollector(tor, history_size=args.history)
    ui = DashboardUI(metrics, tor, history_size=args.history)

    # ── 3. Prime the first bandwidth sample so deltas are     ─
    #        non-zero from the very first frame.               ─
    metrics.sample()
    time.sleep(args.refresh)

    # ── 4. Live rendering loop ────────────────────────────────
    try:
        with Live(
            ui.build(),
            console=console,
            refresh_per_second=int(1 / max(args.refresh, 0.1)),
            screen=True,          # full-screen mode
        ) as live:
            while True:
                metrics.sample()
                live.update(ui.build())
                time.sleep(args.refresh)

    except KeyboardInterrupt:
        pass                       # clean Ctrl-C
    finally:
        tor.disconnect()
        console.print("\n[bold cyan]Bye! Connection closed.[/bold cyan]\n")


if __name__ == "__main__":
    main()
