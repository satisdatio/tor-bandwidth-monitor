# Tor Monitor Pro

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)](https://docker.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-%23336791.svg?style=flat&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Tor](https://img.shields.io/badge/Tor-%237E4798.svg?style=flat&logo=tor&logoColor=white)](https://www.torproject.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-%23009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Prometheus](https://img.shields.io/badge/Prometheus-%23E6522C.svg?style=flat&logo=prometheus&logoColor=white)](https://prometheus.io/)

Professional Tor relay monitoring with multi-relay support, enterprise-grade security, and comprehensive alerting.

Tor Monitor Pro is a sophisticated monitoring solution designed specifically for [Tor](https://www.torproject.org/) relay operators and network administrators. Built with enterprise-grade security and reliability, it provides real-time insights into Tor network performance, anomaly detection, and automated alerting.

                                     
                                             :*%%%%%=.                                             
                                         .+@@@@@@@@@@@@%:                                          
                                       .*@@@@@@@@@@@@@@@@%:                                        
                                      .%@@@@@@@@@@@@@@@@@@@=                                       
                                      %@@@@@@@@@@@@@@@@@@@@@:                                      
                                     -@@@@@@@@@@@@@@@@@@@@@@@                                      
                                     %@@@@@@@@@@@@@@@@@@@@@@@                                      
                                     %@@@@@@@@@@@@@@@@@@@@@@@                                      
                  ..-===-:.          .@@@@@@@@@@@@@@@@@@@@@@@           .::::...                   
               .*@@@@@@@@@@@%=.       #@@@@@@@@@@@@@@@@@@@@@.       .*@@@@@@@@@@%=.                
             .%@@@@@@@@@@@@@@@@+.      #@@@@@@@@@@@@@@@@@@@:      .@@@@@@@@@@@@@@@@#.              
            -@@@@@@@@@@@@@@@@@@@%.     .%@@@@@@@@@@@@@@@@@=      +@@@@@@@@@@@@@@@@@@@:             
           :@@@@@@@@@@@@@@@@@@@@@@:     .@@@@@@@@@@@@@@@@+      %@@@@@@@@@@@@@@@@@@@@@.            
          .@@@@@@@@@@@@@@@@@@@@@@@@=     .@@@@@@@@@@@@@@+     .@@@@@@@@@@@@@@@@@@@@@@@@.           
          .@@@@@@@@@@@@@@@@@@@@@@@@@#.    :@@@@@@@@@@@@*.    :@@@@@@@@@@@@@@@@@@@@@@@@@.           
          .@@@@@@@@@@@@@@@@@@@@@@@@@@@.    :@@@@@@@@@@%.   .+@@@@@@@@@@@@@@@@@@@@@@@@@@.           
          .@@@@@@@@@@@@@@@@@@@@@@@@@@@@:    -@@@@@@@@@.   .#@@@@@@@@@@@@@@@@@@@@@@@@@@@.           
           :@@@@@@@@@@@@@@@@@@@@@@@@@@@@=    *@@@@@@@.   .@@@@@@@@@@@@@@@@@@@@@@@@@@@@-            
            -@@@@@@@@@@@@@@@@@@@@@@@@@@@@#   :@@@@@@@.  -@@@@@@@@@@@@@@@@@@@@@@@@@@@@*             
             .#@@@@@@@@@@@@@@@@@@@@@@@@@@@@%@@@@@@@@@@%@@@@@@@@@@@@@@@@@@@@@@@@@@@@@:              
               .#@@@@@@@@@@@@@@@@@@@@@@@@@@@@%:    .%@@@@@@@@@@@@@@@@@@@@@@@@@@@@%:                
                  .:==+#@@@@@@@@@@@@@@@@@@@@          %@@@@@@@@@@@@@@@@@@@@@#==.                   
                                      .%@@@            @@@@*.                                      
                                       .@@%     ..     *@@.                                        
                                      .%@@@    =++=    @@@@-                                       
                 .-=@@@@@@@@@@@@@@@@@@@@@@@@.-++++++-.%@@@@@@@@@@@@@@@@@@@@@@%=:.                  
               -@@@@@@@@@@@@@@@@@@@@@@@@@@@@@%*++++*%@@@@@@@@@@@@@@@@@@@@@@@@@@@@%=                
             :@@@@@@@@@@@@@@@@@@@@@@@@@@@@@%%@@@@@@@@@%%@@@@@@@@@@@@@@@@@@@@@@@@@@@@:              
            *@@@@@@@@@@@@@@@@@@@@@@@@@@@@=   =@@@@@@@.  :@@@@@@@@@@@@@@@@@@@@@@@@@@@@*             
           -@@@@@@@@@@@@@@@@@@@@@@@@@@@@.    %@@@@@@@.    %@@@@@@@@@@@@@@@@@@@@@@@@@@@-            
          .@@@@@@@@@@@@@@@@@@@@@@@@@@@%.   .%@@@@@@@@@.    *@@@@@@@@@@@@@@@@@@@@@@@@@@@.           
          .@@@@@@@@@@@@@@@@@@@@@@@@@@*.    +@@@@@@@@@@@.    -@@@@@@@@@@@@@@@@@@@@@@@@@@.           
          .@@@@@@@@@@@@@@@@@@@@@@@@@=     =@@@@@@@@@@@@*.    .@@@@@@@@@@@@@@@@@@@@@@@@@.           
          .@@@@@@@@@@@@@@@@@@@@@@@@:     -@@@@@@@@@@@@@@=     .%@@@@@@@@@@@@@@@@@@@@@@@.           
            @@@@@@@@@@@@@@@@@@@@@%      :@@@@@@@@@@@@@@@@=      #@@@@@@@@@@@@@@@@@@@@@.            
            .%@@@@@@@@@@@@@@@@@@*      .@@@@@@@@@@@@@@@@@@:      +@@@@@@@@@@@@@@@@@@@:             
             .=@@@@@@@@@@@@@@@@:      .@@@@@@@@@@@@@@@@@@@@.      .@@@@@@@@@@@@@@@@#.              
                :#@@@@@@@@@@*.        %@@@@@@@@@@@@@@@@@@@@%        .*@@@@@@@@@@%=.                
                    ..::..           +@@@@@@@@@@@@@@@@@@@@@@+           .::::..                    
                                     %@@@@@@@@@@@@@@@@@@@@@@@                                      
                                     %@@@@@@@@@@@@@@@@@@@@@@@                                      
                                     %@@@@@@@@@@@@@@@@@@@@@@@                                      
                                     .@@@@@@@@@@@@@@@@@@@@@@.                                      
                                      -@@@@@@@@@@@@@@@@@@@@:                                       
                                       .%@@@@@@@@@@@@@@@@%.                                        
                                         :%@@@@@@@@@@@@#:                                          
                                             =%@@@@%+.                                            
  

## Key Features

### Comprehensive Monitoring
- Multi-Relay Support: Monitor entire Tor relay fleets from a single dashboard
- Real-time Metrics: Bandwidth utilization, circuit counts, latency measurements, and performance KPIs
- Historical Analysis: Time-series data with configurable retention policies
- Statistical Insights: Trend analysis, peak detection, and percentile calculations

### Advanced Alerting
- Multi-Channel Notifications: Email, Slack, and PagerDuty integration
- Intelligent Thresholds: Configurable alert rules with cooldown periods
- Severity Levels: INFO, WARNING, CRITICAL classification system
- Alert Acknowledgment: Web interface for alert management and tracking

### Enterprise Security
- Tamper-Evident Audit Logs: SHA256-chained audit trail for compliance
- Role-Based Access Control: JWT-based authentication with configurable permissions
- LDAP Integration: Enterprise directory authentication support
- TLS/HTTPS: Secure web interface with certificate support

### Observability & Integration
- Prometheus Metrics: Native Prometheus exporter for Grafana dashboards
- RESTful API: Complete API for integration with existing tools
- Plugin Architecture: Extensible system for custom metrics and alerts
- Database Flexibility: PostgreSQL for production, SQLite for development

### User Interfaces
- Terminal UI: Rich, interactive terminal dashboard with real-time updates
- Web Dashboard: Modern web interface with responsive design
- API Documentation: Auto-generated OpenAPI/Swagger documentation

## Quick Start

### Prerequisites

- Python: 3.9 or higher
- Tor: Running Tor instance with control port enabled
- Database: PostgreSQL (recommended) or SQLite

### Installation

```bash
# Clone the repository
git clone https://github.com/satisdatio/tor-bandwidth-monitor.git
cd tor-bandwidth-monitor

# Install with pip
pip install -e .

# Or with optional dependencies
pip install -e ".[postgres,ldap]"
```

### Basic Configuration

```bash
# Copy example configuration
cp .env.example .env

# Edit configuration (required)
nano .env
```

Minimal `.env` configuration:
```bash
# Required: Generate a secure secret key
TOR_MONITOR_SECRET_KEY="$(openssl rand -hex 32)"

# Tor connection
TOR_CONTROL_HOST=127.0.0.1
TOR_CONTROL_PORT=9051
TOR_CONTROL_PASSWORD=your_tor_control_password

# Database (SQLite for quick start)
TOR_MONITOR_DB_URL=sqlite:///./tor_monitor.db
```

### Run Pre-flight Checks

```bash
# Validate installation and connectivity
tor-monitor-pro-check
```

### Start Monitoring

```bash
# Terminal UI (default)
tor-monitor-pro

# Web dashboard
tor-monitor-pro --web

# Background mode
tor-monitor-pro --background
```

## Documentation

### Tor Integration
- [Tor Control Protocol](https://gitweb.torproject.org/torspec.git/tree/control-spec.txt)
- [Relay Configuration](https://2019.www.torproject.org/docs/tor-manual.html.en)
- [Network Status](https://gitweb.torproject.org/torspec.git/tree/dir-spec.txt)

### Security
- [Audit Logging Standards](https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [TLS Configuration](https://ssl-config.mozilla.org/)

## Docker Deployment

### Production Setup

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f tor-monitor

# Scale monitoring instances
docker-compose up -d --scale tor-monitor=3
```

### Docker Services

| Service | Description | Port |
|---------|-------------|------|
| tor-monitor | Main application | 8080 (web), 9090 (metrics) |
| tor | Tor relay | 9050 (socks), 9051 (control) |
| postgres | Database | 5432 |

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| TOR_MONITOR_SECRET_KEY | JWT signing key | - | Yes |
| TOR_CONTROL_HOST | Tor control host | 127.0.0.1 | Yes |
| TOR_CONTROL_PORT | Tor control port | 9051 | Yes |
| TOR_MONITOR_DB_URL | Database URL | sqlite:///./tor_monitor.db | Yes |
| WEB_HOST | Web server host | 0.0.0.0 | No |
| WEB_PORT | Web server port | 8080 | No |
| PROMETHEUS_PORT | Metrics port | 9090 | No |

### Advanced Configuration

```bash
# Security settings
AUDIT_LOG_PATH=./audit.log
ANOMALY_THRESHOLD=3.0
TOKEN_EXPIRY_MINUTES=60

# Alerting
ALERT_EMAIL_FROM=alerts@yourdomain.com
ALERT_SLACK_WEBHOOK=https://hooks.slack.com/...
ALERT_PAGERDUTY_KEY=your-integration-key

# Performance
REFRESH_INTERVAL=1.0
HISTORY_SIZE=3600
DB_POOL_SIZE=10
```

## API Reference

### Authentication

```bash
# Login
curl -X POST "http://localhost:8080/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# Use token in subsequent requests
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8080/api/relays"
```

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/relays | List monitored relays |
| GET | /api/relays/{name}/metrics | Current metrics |
| GET | /api/relays/{name}/metrics/history | Historical metrics |
| GET | /api/alerts | Active alerts |
| POST | /api/alerts/{id}/acknowledge | Acknowledge alert |
| GET | /metrics | Prometheus metrics |

## Plugin System

### Creating Custom Plugins

```python
from tor_monitor_pro.plugins import PluginBase, MetricsPlugin

class CustomMetricsPlugin(MetricsPlugin):
    name = "custom_metrics"
    version = "1.0.0"
    description = "Custom relay metrics"

    def initialize(self, config: Dict[str, Any]) -> bool:
        self.custom_config = config
        return True

    def collect_metrics(self) -> Dict[str, Any]:
        return {
            "custom_bandwidth": self.measure_bandwidth(),
            "custom_latency": self.measure_latency()
        }

    def cleanup(self):
        pass
```

### Plugin Locations

- Global: /usr/local/share/tor-monitor-pro/plugins/
- User: ~/.tor-monitor-pro/plugins/
- Project: ./plugins/

## Monitoring & Metrics

### Prometheus Integration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'tor-monitor'
    static_configs:
      - targets: ['localhost:9090']
```

### Grafana Dashboard

Import the provided [Grafana dashboard](dashboards/tor-monitor-grafana.json) for comprehensive visualization.

### Key Metrics

| Metric | Type | Description |
|--------|------|-------------|
| tor_monitor_read_rate_kibs | Gauge | Download rate in KiB/s |
| tor_monitor_write_rate_kibs | Gauge | Upload rate in KiB/s |
| tor_monitor_circuit_count | Gauge | Active circuits |
| tor_monitor_alerts_active | Gauge | Active alerts by severity |
| tor_monitor_anomalies_total | Counter | Total anomalies detected |

## Security

### Audit Logging

All security events are logged with tamper-evident SHA256 chaining:

```bash
# Verify audit log integrity
python -c "
from tor_monitor_pro.audit import AuditLogger
logger = AuditLogger('./audit.log')
print('Audit log integrity:', 'VALID' if logger.verify_chain() else 'COMPROMISED')
"
```

### PGP Key Verification

For secure distribution, releases are signed with PGP:

Maintainer PGP Key: 0xCF09157628A7E811
Email: satisdatio@proton.me


## Testing

### Run Test Suite

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run tests
pytest

# With coverage
pytest --cov=tor_monitor_pro --cov-report=html
```

### Installation Test

```bash
# Quick installation verification
python test_installation.py
```

## Development Setup

```bash
# Fork and clone
git clone https://github.com/satisdatio/tor-bandwidth-monitor.git
cd tor-bandwidth-monitor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Start development server
tor-monitor-pro --debug --web
```

### Code Quality

```bash
# Format code
black tor_monitor_pro/
isort tor_monitor_pro/

# Lint code
ruff tor_monitor_pro/
mypy tor_monitor_pro/

# Security audit
bandit -r tor_monitor_pro/
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

MIT License

Copyright (c) 2026 Tor Monitor Pro Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

## Acknowledgments

- [Tor Project](https://www.torproject.org/) - For the Tor anonymity network
- [Stem](https://stem.torproject.org/) - Python Tor control library
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Rich](https://rich.readthedocs.io/) - Beautiful terminal interfaces
- [Prometheus](https://prometheus.io/) - Metrics collection and alerting

## Support

For issues or questions, visit the [GitHub repository](https://github.com/satisdatio/tor-bandwidth-monitor.git).

---

Tor Monitor Pro - Professional monitoring for Tor relay operators
