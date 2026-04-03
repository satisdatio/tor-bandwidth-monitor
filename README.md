# Tor Bandwidth Monitor

A lightweight, real-time CLI dashboard for monitoring Tor bandwidth and circuits,
built with [`stem`](https://stem.torproject.org/) and [`Rich`](https://rich.readthedocs.io/).

```
⬤  Tor Bandwidth Monitor  │  Tor 0.4.8.10  │  uptime 2h 34m 12s  │  mode: client  │  14:22:07
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
╭──── Metrics ──────────────╮  ╭──── Bandwidth History ──────────────────────────────────────────╮
│  ↓ Download   12.34 KiB/s │  │  ↓ Download  peak: 48.2 KiB/s                                   │
│  ↑ Upload      3.21 KiB/s │  │  ▁▂▃▄▅▆▇█▇▆▅▄▃▂▁▂▃▄▅▆▇█▇▆▅▄▃▂▁▂▃▄▅▆▇█▇▆▅▄▃▂▁                    │
│                           │  │  ↑ Upload    peak: 12.1 KiB/s                                   │
│  ↕ Total ↓   142.003 MiB  │  │  ▁▁▁▂▂▃▂▁▁▁▂▂▃▂▁▁▁▂▂▃▂▁▁▁▂▂▃▂▁▁▁▂▂▃▂▁▁▁▂▂▃▂▁                    │
│  ↕ Total ↑    31.447 MiB  │  ├─────────────────────────────────────────────────────────────────┤
│                           │  │  Last 12 samples                                                │
│  ⧗ Latency      4.2 ms    │  │  ██▊▋▌▍▎▏ ▏▎▍  ↓                                                │
│  ⊕ Circuits         3     │  │  ▍▎▏ ▏▎▍▌▋▊█▊  ↑                                                │
╰───────────────────────────╯  ╰─────────────────────────────────────────────────────────────────╯

╭──── Active Circuits  (3 built) ─────────────────────────────────────────────────────────────╮
│  ID   │ Hops │ Purpose        │ Status     │ Path (Guard → Middle → Exit)                   │
│ ───── │ ──── │ ────────────── │ ────────── │ ─────────────────────────────────────────────  │
│  42   │   3  │ GENERAL        │ BUILT      │ PrivacyGuard → SwissRelay → ExitNodeDE         │
│  43   │   3  │ GENERAL        │ BUILT      │ FastRelay → MidEurope → USExitNode             │
│  44   │   2  │ HS_CLIENT_REND │ BUILT      │ OnionGuard → RendPoint                         │
╰─────────────────────────────────────────────────────────────────────────────────────────────╯

  Ctrl-C quit    Auto-refresh every 1 s    Colour: ● fast  ● medium  ● slow
```

---

## Features

| Feature | Details |
|---|---|
| **Live circuit table** | Circuit ID, hop count, purpose, status, colour-coded relay path |
| **Bandwidth metrics** | Real-time download/upload KiB/s via cumulative counter diffing |
| **Sparklines** | Unicode block-char history charts for the last N samples |
| **Mini bar chart** | Last 12 samples rendered as vertical bar segments |
| **Latency probe** | Control-port RTT as a lightweight responsiveness indicator |
| **Auth detection** | Cookie → password → unauthenticated fallback chain |
| **Pre-flight check** | `check_setup.py` validates everything before first run |
| **Low CPU** | Single-threaded, no background polling threads |

---

## Requirements

- Python **3.8+**
- **Tor** running with `ControlPort` enabled
- `stem` ≥ 1.8.0
- `rich` ≥ 13.0.0

---

## Installation

### 1. Configure Tor

Add (or uncomment) these lines in your `torrc`:

```
ControlPort 9051
CookieAuthentication 1
```

Then restart Tor:
```bash
# Linux / macOS (systemd)
sudo systemctl restart tor

# macOS (Homebrew)
brew services restart tor

# Direct
tor -f /etc/tor/torrc
```

Find your `torrc`:
| Platform | Typical path |
|---|---|
| Linux (apt/yum) | `/etc/tor/torrc` |
| macOS (Homebrew) | `/usr/local/etc/tor/torrc` |
| Windows (TBB) | `Browser/TorBrowser/Data/Tor/torrc` |

### 2. Install Python dependencies

```bash
cd tor_monitor
pip install -r requirements.txt
```

Or as a package (editable):
```bash
pip install -e .
```

### 3. Run the pre-flight checker

```bash
python -m tor_monitor.check_setup
```

Expected output:
```
─── Tor Monitor Pre-flight Checks ───────────────────────

Python & packages
  [✓] Python 3.11
  [✓] stem (1.8.2)
  [✓] rich (13.7.0)

Tor control port
  [✓] Control port 127.0.0.1:9051 is reachable

Authentication & data
  [✓] Tor authentication succeeded
  [✓] Traffic counters read OK  (↓ 14829312 B  ↑ 4194304 B cumulative)
  [✓] 3 active circuit(s) found

──────────────────────────────────────────────────────────
  All checks passed – you're ready to run tor_monitor!
```

---

## Usage

```bash
python main.py
```

### Options

```
usage: tor-monitor [-h] [--host HOST] [--port PORT] [--password PASSWORD]
                   [--refresh SECONDS] [--history N]

  --host HOST        Control-port host (default: 127.0.0.1)
  --port PORT        Control-port number (default: 9051)
  --password PASS    Control-port password (omit for cookie auth)
  --refresh SECS     Seconds between refreshes (default: 1.0)
  --history N        Sparkline sample count (default: 60)
```

### Common invocations

```bash
# Default (cookie auth, 1 s refresh)
python main.py

# Password auth
python main.py --password "mySecret"

# Non-standard port, faster refresh
python main.py --port 9999 --refresh 0.5

# Wider sparkline window
python main.py --history 120

# Remote Tor instance
python main.py --host 192.168.1.50 --port 9051
```

---

## Project Structure

```
tor_monitor/
├── main.py                    # CLI entry-point & main render loop
├── requirements.txt
├── pyproject.toml
├── README.md
└── tor_monitor/
    ├── __init__.py
    ├── controller.py          # stem wrapper – connect, auth, GETINFO
    ├── metrics.py             # bandwidth sampling, history, snapshots
    ├── ui.py                  # Rich dashboard – all rendering logic
    └── check_setup.py         # pre-flight environment validator
```

### Module responsibilities

```
main.py
  └─ parse CLI args
  └─ connect TorController
  └─ initialise MetricsCollector + DashboardUI
  └─ drive Live() render loop

controller.py         (stem boundary)
  └─ TCP preflight check
  └─ authenticate (cookie → password → none)
  └─ get_circuits()           → raw stem Circuit objects
  └─ get_bytes_transferred()  → (read_bytes, write_bytes) ints
  └─ get_uptime() / get_version() / is_relay()

metrics.py            (data layer)
  └─ sample()                 → Snapshot dataclass
  └─ delta computation        (bytes / elapsed / 1024)
  └─ deque history buffers    (maxlen = history_size)
  └─ latency probe            (perf_counter around GETINFO)

ui.py                 (view layer)
  └─ build()                  → Rich renderable (Group)
  └─ _render_header()         → Panel
  └─ _render_metrics_panel()  → Panel (Table.grid)
  └─ _render_sparklines()     → Panel (unicode blocks)
  └─ _render_mini_bars()      → Text (vertical bars)
  └─ _render_circuit_table()  → Panel (Table)
  └─ _render_footer()         → Panel
```

---

## Throughput formula

```
elapsed   = time_now − time_prev          (seconds, wall clock)
read_Δ    = traffic/read_now − read_prev  (bytes, monotonic)
read_kib  = read_Δ / elapsed / 1024       (KiB/s)
```

Tor's `traffic/read` and `traffic/written` are cumulative byte
counters maintained by the Tor process.  We diff successive readings
divided by elapsed time.  The counter resets when Tor restarts.

---

## Latency note

The "Latency" metric is the **control-port round-trip time** – the
time to send a GETINFO command and receive the response.  It is *not*
the circuit latency you'd see in a browser.  True circuit latency
requires an actual SOCKS5 connection, which is outside the scope of
this tool.  The RTT is still useful as a proxy for Tor process
responsiveness.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Connection refused` on port 9051 | Add `ControlPort 9051` to torrc and restart Tor |
| `Auth failed: missing password` | Add `CookieAuthentication 1` to torrc **or** use `--password` |
| `UnreadableCookieFile` | Run with `sudo` or add your user to the `debian-tor` group |
| No circuits shown | Tor may still be bootstrapping – wait 30 s |
| Latency `N/A` | Control socket error; check Tor is running |
| `stem` not found | `pip install stem` |

---

## License

MIT
