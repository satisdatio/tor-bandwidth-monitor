"""Security audit logging for compliance."""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
from logging.handlers import RotatingFileHandler
import hashlib


class AuditLogger:
    """
    Security audit logger for compliance requirements.
    
    Logs all security-relevant actions with tamper-evident hashing.
    """
    
    def __init__(self, log_path: str, retention_days: int = 365):
        self.log_path = Path(log_path)
        self.retention_days = retention_days
        self._last_hash: Optional[str] = None
        
        # Setup rotating file handler
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger("tor_monitor_audit")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        
        handler = RotatingFileHandler(
            self.log_path,
            maxBytes=100*1024*1024,  # 100MB
            backupCount=10
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(handler)
    
    def _compute_hash(self, entry: Dict[str, Any]) -> str:
        """Compute hash for tamper evidence."""
        content = json.dumps(entry, sort_keys=True, default=str)
        hash_input = content + (self._last_hash or "")
        return hashlib.sha256(hash_input.encode()).hexdigest()
    
    def log(self, action: str, user_id: Optional[str] = None,
           resource: Optional[str] = None, result: str = "SUCCESS",
           details: Optional[Dict] = None, ip_address: Optional[str] = None,
           user_agent: Optional[str] = None):
        """
        Log an audit event.
        
        Args:
            action: Action performed (e.g., "login", "config_change")
            user_id: User identifier
            resource: Resource accessed
            result: SUCCESS or FAILURE
            details: Additional details
            ip_address: Client IP address
            user_agent: Client user agent
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "user_id": user_id,
            "resource": resource,
            "result": result,
            "details": details or {},
            "ip_address": ip_address,
            "user_agent": user_agent
        }
        
        # Add chain hash for tamper evidence
        entry["hash"] = self._compute_hash(entry)
        entry["prev_hash"] = self._last_hash
        self._last_hash = entry["hash"]
        
        self.logger.info(json.dumps(entry))
    
    def log_login(self, user_id: str, ip_address: str, 
                 user_agent: str, success: bool, 
                 method: str = None):
        """Log login attempt."""
        self.log(
            action="login",
            user_id=user_id,
            result="SUCCESS" if success else "FAILURE",
            details={"method": method},
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def log_config_change(self, user_id: str, setting: str,
                        old_value: Any, new_value: Any,
                        ip_address: str = None):
        """Log configuration change."""
        self.log(
            action="config_change",
            user_id=user_id,
            resource=setting,
            details={
                "old_value": str(old_value),
                "new_value": str(new_value)
            },
            ip_address=ip_address
        )
    
    def log_alert_ack(self, user_id: str, alert_id: str,
                     ip_address: str = None):
        """Log alert acknowledgment."""
        self.log(
            action="alert_acknowledge",
            user_id=user_id,
            resource=alert_id,
            ip_address=ip_address
        )
    
    def log_api_access(self, user_id: str, endpoint: str,
                      method: str, status_code: int,
                      ip_address: str, user_agent: str):
        """Log API access."""
        self.log(
            action="api_access",
            user_id=user_id,
            resource=f"{method} {endpoint}",
            result="SUCCESS" if status_code < 400 else "FAILURE",
            details={"status_code": status_code},
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def verify_chain(self) -> bool:
        """
        Verify audit log chain integrity.
        
        Returns:
            True if chain is intact, False if tampering detected
        """
        prev_hash = None
        
        try:
            with open(self.log_path) as f:
                for line in f:
                    entry = json.loads(line.strip())
                    expected_hash = entry.get("hash")
                    entry_prev = entry.get("prev_hash")
                    
                    if entry_prev != prev_hash:
                        return False
                    
                    # Recompute hash
                    test_entry = {k: v for k, v in entry.items() 
                                 if k not in ("hash", "prev_hash")}
                    content = json.dumps(test_entry, sort_keys=True, default=str)
                    hash_input = content + (prev_hash or "")
                    computed = hashlib.sha256(hash_input.encode()).hexdigest()
                    
                    if computed != expected_hash:
                        return False
                    
                    prev_hash = expected_hash
            
            return True
        except Exception:
            return False