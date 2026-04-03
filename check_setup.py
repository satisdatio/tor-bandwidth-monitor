"""
tor_monitor/check_setup.py
────────────────────────────────────────────────────────────────
Stand-alone pre-flight checker.

Run this before tor_monitor to validate your environment:
    python -m tor_monitor.check_setup [--host HOST] [--port PORT]

Checks performed
----------------
1. Python version ≥ 3.8
2. Required packages installed (stem, rich)
3. Tor control port is reachable
4. Authentication succeeds (cookie or password)
5. GETINFO traffic/read returns a valid integer
6. At least one circuit is active (warns, not fatal)
"""

from __future__ import annotations

import argparse
import importlib
import socket
import sys
import time


# ── Helpers ───────────────────────────────────────────────────

def _ok(msg: str)   -> None: print(f"  [✓] {msg}")
def _warn(msg: str) -> None: print(f"  [!] {msg}")
def _fail(msg: str) -> None: print(f"  [✗] {msg}")


# ── Individual checks ─────────────────────────────────────────

def check_python_version() -> bool:
    major, minor = sys.version_info[:2]
    ok = (major, minor) >= (3, 8)
    label = f"Python {major}.{minor}"
    if ok:
        _ok(label)
    else:
        _fail(f"{label} – Python 3.8+ required")
    return ok


def check_package(name: str, import_name: str | None = None) -> bool:
    import_name = import_name or name
    try:
        mod = importlib.import_module(import_name)
        ver = getattr(mod, "__version__", "installed")
        _ok(f"{name} ({ver})")
        return True
    except ImportError:
        _fail(f"{name} not installed  →  pip install {name}")
        return False


def check_port(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=3):
            pass
        _ok(f"Control port {host}:{port} is reachable")
        return True
    except OSError as exc:
        _fail(f"Cannot reach {host}:{port} – {exc}")
        return False


def check_auth(host: str, port: int, password: str | None) -> bool:
    """Attempt full auth and run a sample GETINFO to validate."""
    try:
        from tor_monitor.controller import TorController

        tor = TorController(host=host, port=port, password=password)
        tor.connect()
        _ok("Tor authentication succeeded")

        # Smoke-test traffic counters
        rb, wb = tor.get_bytes_transferred()
        if isinstance(rb, int) and isinstance(wb, int):
            _ok(f"Traffic counters read OK  (↓ {rb} B  ↑ {wb} B cumulative)")
        else:
            _warn("traffic/read returned unexpected type – monitor may malfunction")

        # Check circuits
        circs = tor.get_circuits()
        if circs:
            _ok(f"{len(circs)} active circuit(s) found")
        else:
            _warn("No BUILT circuits yet – Tor may still be bootstrapping")

        tor.disconnect()
        return True

    except Exception as exc:     # noqa: BLE001
        _fail(f"Auth/GETINFO error: {exc}")
        return False


# ── Runner ────────────────────────────────────────────────────

def run_checks(host: str, port: int, password: str | None) -> bool:
    print("\n─── Tor Monitor Pre-flight Checks ───────────────────────\n")
    results = []

    print("Python & packages")
    results.append(check_python_version())
    results.append(check_package("stem"))
    results.append(check_package("rich"))

    print("\nTor control port")
    port_ok = check_port(host, port)
    results.append(port_ok)

    if port_ok:
        print("\nAuthentication & data")
        results.append(check_auth(host, port, password))
    else:
        _warn("Skipping auth check – port not reachable")

    print("\n──────────────────────────────────────────────────────────")
    if all(results):
        print("  All checks passed – you're ready to run tor_monitor!\n")
        return True
    else:
        failed = results.count(False)
        print(f"  {failed} check(s) failed.  Fix the issues above before running.\n")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Tor Monitor setup checker")
    parser.add_argument("--host",     default="127.0.0.1")
    parser.add_argument("--port",     type=int, default=9051)
    parser.add_argument("--password", default=None)
    args = parser.parse_args()

    ok = run_checks(args.host, args.port, args.password)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
