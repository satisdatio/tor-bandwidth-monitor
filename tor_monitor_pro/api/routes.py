"""API routes for Tor Monitor Pro."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from ..config import Config
from ..controller import MultiRelayController, RelayConnection
from ..database import Database
from ..alerts import AlertManager, Alert, Severity
from ..anomaly import AnomalyDetector
from ..audit import AuditLogger
from .auth import (
    get_current_active_user, require_role, User, Token,
    authenticate_user, create_access_token, ROLE_ADMIN, ROLE_OPERATOR
)

router = APIRouter()


# ============ Authentication ============

class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/auth/login", response_model=Token)
async def login(request: Request, login_data: LoginRequest):
    """Authenticate and get access token."""
    config: Config = request.app.state.config
    
    user = authenticate_user(login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )
    
    access_token, expires_in = create_access_token(
        config,
        data={"sub": user.username, "roles": user.roles}
    )
    
    return Token(access_token=access_token, expires_in=expires_in)


@router.get("/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """Get current user info."""
    return current_user


# ============ Relays ============

@router.get("/relays", dependencies=[Depends(get_current_active_user)])
async def list_relays(request: Request) -> List[Dict[str, Any]]:
    """List all monitored relays."""
    controller: MultiRelayController = request.app.state.controller
    
    result = []
    for name, relay in controller.relays.items():
        result.append({
            "name": relay.name,
            "host": relay.host,
            "port": relay.port,
            "is_connected": relay.is_connected,
            "fingerprint": relay.fingerprint,
            "version": relay.version,
            "uptime_seconds": relay.uptime,
            "error": relay.error
        })
    
    return result


@router.get("/relays/{relay_name}/metrics", dependencies=[Depends(get_current_active_user)])
async def get_relay_metrics(
    request: Request,
    relay_name: str,
    hours: int = Query(24, ge=1, le=720)
) -> Dict[str, Any]:
    """Get metrics for a specific relay."""
    controller: MultiRelayController = request.app.state.controller
    database: Database = request.app.state.database
    
    relay = controller.get_relay(relay_name)
    if not relay:
        raise HTTPException(status_code=404, detail="Relay not found")
    
    # Get current metrics
    current = controller.get_metrics(relay_name)
    
    # Get aggregated stats
    db_relay = database.get_or_create_relay(name=relay_name)
    stats = database.get_aggregated_stats(db_relay.id, hours=hours)
    
    return {
        "relay": relay_name,
        "current": current,
        "stats": stats,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/relays/{relay_name}/metrics/history", dependencies=[Depends(get_current_active_user)])
async def get_metrics_history(
    request: Request,
    relay_name: str,
    hours: int = Query(24, ge=1, le=720),
    limit: int = Query(1000, ge=1, le=10000)
) -> List[Dict[str, Any]]:
    """Get historical metrics."""
    database: Database = request.app.state.database
    
    db_relay = database.get_or_create_relay(name=relay_name)
    end = datetime.utcnow()
    start = end - timedelta(hours=hours)
    
    metrics = database.get_metrics_range(db_relay.id, start, end)
    
    return [
        {
            "timestamp": m.timestamp.isoformat(),
            "read_rate_kibs": m.read_rate_kibs,
            "write_rate_kibs": m.write_rate_kibs,
            "latency_ms": m.latency_ms,
            "circuit_count": m.circuit_count
        }
        for m in metrics[-limit:]
    ]


# ============ Alerts ============

@router.get("/alerts", dependencies=[Depends(get_current_active_user)])
async def list_alerts(
    request: Request,
    active_only: bool = Query(True),
    severity: Optional[str] = None
) -> List[Dict[str, Any]]:
    """List alerts."""
    alert_manager: AlertManager = request.app.state.alert_manager
    
    if active_only:
        sev = Severity(severity) if severity else None
        alerts = alert_manager.get_active_alerts(sev)
    else:
        alerts = alert_manager.alert_history[-100:]
    
    return [
        {
            "id": a.id,
            "rule_name": a.rule_name,
            "alert_type": a.alert_type.value,
            "severity": a.severity.value,
            "message": a.message,
            "timestamp": a.timestamp.isoformat(),
            "resolved": a.resolved,
            "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
            "metrics": a.metrics
        }
        for a in alerts
    ]


@router.post("/alerts/{alert_id}/acknowledge", dependencies=[Depends(require_role(ROLE_OPERATOR))])
async def acknowledge_alert(
    request: Request,
    alert_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, str]:
    """Acknowledge an alert."""
    alert_manager: AlertManager = request.app.state.alert_manager
    audit_logger: AuditLogger = request.app.state.audit_logger
    
    alert_manager.resolve_alert(alert_id)
    
    audit_logger.log_alert_ack(
        user_id=current_user.username,
        alert_id=alert_id,
        ip_address=request.client.host if request.client else None
    )
    
    return {"status": "acknowledged", "alert_id": alert_id}


@router.get("/alerts/stats", dependencies=[Depends(get_current_active_user)])
async def get_alert_stats(request: Request) -> Dict[str, int]:
    """Get alert statistics."""
    alert_manager: AlertManager = request.app.state.alert_manager
    return alert_manager.get_alert_stats()


# ============ Anomalies ============

@router.get("/anomalies", dependencies=[Depends(get_current_active_user)])
async def list_anomalies(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    severity: Optional[str] = None
) -> List[Dict[str, Any]]:
    """List detected anomalies."""
    anomaly_detector: AnomalyDetector = request.app.state.anomaly_detector
    
    if not anomaly_detector:
        return []
    
    anomalies = anomaly_detector.get_recent_anomalies(limit=limit, severity=severity)
    
    return [
        {
            "type": a.anomaly_type,
            "severity": a.severity,
            "message": a.message,
            "timestamp": a.timestamp.isoformat(),
            "confidence": a.confidence,
            "details": a.details
        }
        for a in anomalies
    ]


@router.get("/anomalies/stats", dependencies=[Depends(get_current_active_user)])
async def get_anomaly_stats(request: Request) -> Dict[str, Any]:
    """Get anomaly statistics."""
    anomaly_detector: AnomalyDetector = request.app.state.anomaly_detector
    
    if not anomaly_detector:
        return {"enabled": False}
    
    return {
        "enabled": True,
        **anomaly_detector.get_anomaly_stats()
    }


# ============ Configuration ============

@router.get("/config", dependencies=[Depends(require_role(ROLE_ADMIN))])
async def get_config(request: Request) -> Dict[str, Any]:
    """Get current configuration."""
    config: Config = request.app.state.config
    return config.model_dump()


@router.patch("/config", dependencies=[Depends(require_role(ROLE_ADMIN))])
async def update_config(
    request: Request,
    updates: Dict[str, Any],
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, str]:
    """Update configuration."""
    config: Config = request.app.state.config
    audit_logger: AuditLogger = request.app.state.audit_logger
    
    for key, value in updates.items():
        old_value = getattr(config, key, None)
        if old_value != value:
            setattr(config, key, value)
            audit_logger.log_config_change(
                user_id=current_user.username,
                setting=key,
                old_value=old_value,
                new_value=value,
                ip_address=request.client.host if request.client else None
            )
    
    return {"status": "updated"}


# ============ System ============

@router.get("/system/info", dependencies=[Depends(get_current_active_user)])
async def get_system_info(request: Request) -> Dict[str, Any]:
    """Get system information."""
    config: Config = request.app.state.config
    controller: MultiRelayController = request.app.state.controller
    plugin_manager = request.app.state.plugin_manager
    
    return {
        "version": config.version,
        "app_name": config.app_name,
        "debug": config.debug,
        "relays": {
            "total": len(controller.relays),
            "connected": len(controller.get_connected_relays())
        },
        "plugins": {
            "loaded": list(plugin_manager.plugins.keys()),
            "count": len(plugin_manager.plugins)
        },
        "features": {
            "web_dashboard": config.web.enable_dashboard,
            "api": config.web.enable_api,
            "prometheus": config.web.enable_prometheus,
            "anomaly_detection": config.security.enable_anomaly_detection,
            "multi_relay": config.multi_relay
        }
    }