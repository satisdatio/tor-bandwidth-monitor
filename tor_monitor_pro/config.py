"""Configuration management with Pydantic Settings."""

from pathlib import Path
from typing import Optional, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseSettings):
    """Database configuration."""
    url: str = Field("sqlite:///./tor_monitor.db", env="TOR_MONITOR_DB_URL")
    pool_size: int = Field(10, env="TOR_MONITOR_DB_POOL_SIZE")
    retention_days: int = Field(90, env="TOR_MONITOR_RETENTION_DAYS")


class TorConfig(BaseSettings):
    """Tor connection configuration."""
    host: str = Field("127.0.0.1", env="TOR_CONTROL_HOST")
    port: int = Field(9051, env="TOR_CONTROL_PORT")
    password: Optional[str] = Field(None, env="TOR_CONTROL_PASSWORD")
    cookie_path: Optional[str] = Field(None, env="TOR_COOKIE_PATH")
    timeout: float = Field(5.0, env="TOR_TIMEOUT")


class AlertConfig(BaseSettings):
    """Alerting configuration."""
    enabled: bool = Field(True, env="ALERTS_ENABLED")
    email_smtp_host: Optional[str] = Field(None, env="ALERT_SMTP_HOST")
    email_smtp_port: int = Field(587, env="ALERT_SMTP_PORT")
    email_from: Optional[str] = Field(None, env="ALERT_EMAIL_FROM")
    email_to: List[str] = Field([], env="ALERT_EMAIL_TO")
    slack_webhook: Optional[str] = Field(None, env="ALERT_SLACK_WEBHOOK")
    pagerduty_key: Optional[str] = Field(None, env="ALERT_PAGERDUTY_KEY")


class SecurityConfig(BaseSettings):
    """Security and compliance configuration."""
    audit_log_path: str = Field("./audit.log", env="AUDIT_LOG_PATH")
    audit_retention_days: int = Field(365, env="AUDIT_RETENTION_DAYS")
    enable_anomaly_detection: bool = Field(True, env="ANOMALY_DETECTION_ENABLED")
    anomaly_threshold: float = Field(3.0, env="ANOMALY_THRESHOLD")
    enable_tls: bool = Field(False, env="WEB_TLS_ENABLED")
    tls_cert_path: Optional[str] = Field(None, env="WEB_TLS_CERT")
    tls_key_path: Optional[str] = Field(None, env="WEB_TLS_KEY")
    secret_key: str = Field(..., env="TOR_MONITOR_SECRET_KEY")
    token_expiry_minutes: int = Field(60, env="TOKEN_EXPIRY_MINUTES")


class WebConfig(BaseSettings):
    """Web dashboard configuration."""
    host: str = Field("0.0.0.0", env="WEB_HOST")
    port: int = Field(8080, env="WEB_PORT")
    enable_dashboard: bool = Field(True, env="WEB_DASHBOARD_ENABLED")
    enable_api: bool = Field(True, env="WEB_API_ENABLED")
    enable_prometheus: bool = Field(True, env="PROMETHEUS_ENABLED")
    prometheus_port: int = Field(9090, env="PROMETHEUS_PORT")


class Config(BaseSettings):
    """Main configuration."""
    app_name: str = "Tor Monitor Pro"
    version: str = "1.0.0"
    debug: bool = Field(False, env="TOR_MONITOR_DEBUG")
    refresh_interval: float = Field(1.0, env="REFRESH_INTERVAL")
    history_size: int = Field(3600, env="HISTORY_SIZE")
    multi_relay: bool = Field(False, env="MULTI_RELAY_ENABLED")
    relay_name: str = Field("default", env="RELAY_NAME")
    
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    tor: TorConfig = Field(default_factory=TorConfig)
    alerts: AlertConfig = Field(default_factory=AlertConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    web: WebConfig = Field(default_factory=WebConfig)
    
    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"