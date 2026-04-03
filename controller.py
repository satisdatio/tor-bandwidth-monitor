"""
tor_monitor/controller.py
────────────────────────────────────────────────────────────────
Thin wrapper around stem's Controller.

Responsibilities
----------------
* Open & authenticate the control-port connection.
* Expose helpers that the rest of the app uses (get_circuits,
  get_bw_event, get_info, …).
* Centralise all stem imports so the rest of the code stays
  library-agnostic; swapping stem for something else only
  touches this file.

Authentication strategy
-----------------------
1. If --password was supplied → PasswordAuthentication.
2. Otherwise → CookieAuthentication (reads the cookie file
   path from the control-port itself, so no hard-coded path).
3. Falls back to unauthenticated if both fail (rare, but some
   test/dev Tor instances allow it).
"""

from __future__ import annotations

import socket
from typing import Dict, List, Optional, Tuple

import stem                                         # type: ignore
import stem.connection                              # type: ignore
import stem.control                                 # type: ignore
import stem.descriptor                              # type: ignore
from stem import CircStatus                         # type: ignore
from stem.control import Controller, EventType      # type: ignore


class TorController:
    """
    Manages a single persistent connection to the Tor control port.

    Parameters
    ----------
    host:     IP/hostname of the control port (default 127.0.0.1)
    port:     TCP port (default 9051)
    password: Optional password string for password-auth.
              When None, cookie authentication is attempted first.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9051,
        password: Optional[str] = None,
    ) -> None:
        self.host = host
        self.port = port
        self.password = password
        self._ctrl: Optional[Controller] = None

    # ── Public API ────────────────────────────────────────────

    def connect(self) -> None:
        """Open the control socket and authenticate.  Raises on failure."""
        self._preflight_check()          # fast TCP probe before stem overhead
        self._ctrl = Controller.from_port(address=self.host, port=self.port)
        self._authenticate()

    def disconnect(self) -> None:
        """Cleanly close the control connection."""
        if self._ctrl and self._ctrl.is_alive():
            self._ctrl.close()
        self._ctrl = None

    @property
    def ctrl(self) -> Controller:
        """Raw stem Controller – use sparingly outside this module."""
        if self._ctrl is None:
            raise RuntimeError("Not connected – call connect() first.")
        return self._ctrl

    # ── Circuit helpers ───────────────────────────────────────

    def get_circuits(self) -> List[Dict]:
        """
        Return a list of dicts describing each active circuit.

        Keys per dict
        -------------
        id          : str   – circuit ID
        status      : str   – BUILT / LAUNCHED / EXTENDED / …
        purpose     : str   – GENERAL / HS_CLIENT_INTRO / …
        path        : list[tuple[fingerprint, nickname]]
        build_flags : list[str]
        """
        circuits = []
        try:
            for circ in self._ctrl.get_circuits():
                if circ.status == CircStatus.BUILT:
                    circuits.append(
                        {
                            "id": circ.id,
                            "status": circ.status.name if hasattr(circ.status, "name") else str(circ.status),
                            "purpose": circ.purpose or "GENERAL",
                            "path": circ.path,          # list of (fp, nickname)
                        }
                    )
        except stem.ControllerError:
            pass
        return circuits

    # ── Bandwidth helpers ─────────────────────────────────────

    def get_bytes_transferred(self) -> Tuple[int, int]:
        """
        Return cumulative (bytes_read, bytes_written) from Tor's GETINFO.

        These are monotonically increasing counters since Tor started.
        The MetricsCollector derives throughput by diffing successive calls.
        """
        try:
            read_bytes  = int(self._ctrl.get_info("traffic/read",  "0"))
            write_bytes = int(self._ctrl.get_info("traffic/written", "0"))
            return read_bytes, write_bytes
        except stem.ControllerError:
            return 0, 0

    # ── General info ──────────────────────────────────────────

    def get_version(self) -> str:
        try:
            return str(self._ctrl.get_version())
        except stem.ControllerError:
            return "unknown"

    def get_uptime(self) -> int:
        """Return Tor process uptime in seconds (0 if unavailable)."""
        try:
            return int(self._ctrl.get_info("uptime", "0"))
        except stem.ControllerError:
            return 0

    def get_fingerprint(self) -> str:
        try:
            return self._ctrl.get_info("fingerprint", "N/A")
        except stem.ControllerError:
            return "N/A"

    def get_exit_policy_summary(self) -> str:
        try:
            return self._ctrl.get_info("exit-policy/summary", "N/A")
        except stem.ControllerError:
            return "N/A"

    def is_relay(self) -> bool:
        try:
            return self._ctrl.get_conf("ORPort", None) not in (None, "0")
        except stem.ControllerError:
            return False

    # ── Private helpers ───────────────────────────────────────

    def _preflight_check(self) -> None:
        """
        Attempt a raw TCP connect before handing off to stem.
        Gives a friendlier error message than stem's exception.
        """
        with socket.create_connection((self.host, self.port), timeout=3):
            pass   # success – connection is closed immediately

    def _authenticate(self) -> None:
        """Try password → cookie → none in sequence."""
        if self.password is not None:
            stem.connection.authenticate_password(self._ctrl, self.password)
            return

        # Try cookie (most common default)
        try:
            stem.connection.authenticate_cookie(self._ctrl)
            return
        except stem.connection.IncorrectCookieSize:
            pass
        except stem.connection.UnreadableCookieFile:
            pass
        except Exception:   # noqa: BLE001
            pass

        # Try the generic authenticate() which auto-detects
        try:
            self._ctrl.authenticate()
            return
        except stem.connection.MissingPassword:
            raise RuntimeError(
                "Tor requires a password.  Re-run with --password <your-password>."
            )
        except stem.connection.AuthenticationFailure as exc:
            raise RuntimeError(f"Authentication failed: {exc}")
