"""Persistent time-series database with SQLAlchemy."""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, 
    Text, Boolean, ForeignKey, Index, func
)
from sqlalchemy.orm import (
    declarative_base, sessionmaker, relationship, Session
)
from sqlalchemy.pool import QueuePool
import json

Base = declarative_base()


class Relay(Base):
    """Relay information for multi-relay support."""
    __tablename__ = "relays"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    fingerprint = Column(String(40), unique=True)
    host = Column(String(255))
    control_port = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime)
    
    metrics = relationship("BandwidthMetric", back_populates="relay", cascade="all, delete-orphan")
    circuits = relationship("CircuitRecord", back_populates="relay", cascade="all, delete-orphan")
    alerts = relationship("AlertRecord", back_populates="relay", cascade="all, delete-orphan")


class BandwidthMetric(Base):
    """Time-series bandwidth metrics."""
    __tablename__ = "bandwidth_metrics"
    
    id = Column(Integer, primary_key=True)
    relay_id = Column(Integer, ForeignKey("relays.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    read_bytes = Column(Integer)
    write_bytes = Column(Integer)
    read_rate_kibs = Column(Float)
    write_rate_kibs = Column(Float)
    
    circuit_count = Column(Integer)
    stream_count = Column(Integer)
    latency_ms = Column(Float)
    
    relay = relationship("Relay", back_populates="metrics")
    
    __table_args__ = (
        Index("idx_relay_timestamp", "relay_id", "timestamp"),
    )


class CircuitRecord(Base):
    """Circuit history for analysis."""
    __tablename__ = "circuit_records"
    
    id = Column(Integer, primary_key=True)
    relay_id = Column(Integer, ForeignKey("relays.id"), nullable=False)
    circuit_id = Column(Integer)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    purpose = Column(String(50))
    status = Column(String(20))
    hop_count = Column(Integer)
    path = Column(Text)  # JSON-encoded path
    is_hs_circuit = Column(Boolean, default=False)
    
    relay = relationship("Relay", back_populates="circuits")


class AlertRecord(Base):
    """Alert history."""
    __tablename__ = "alert_records"
    
    id = Column(Integer, primary_key=True)
    relay_id = Column(Integer, ForeignKey("relays.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)  # INFO, WARNING, CRITICAL
    message = Column(Text, nullable=False)
    metrics = Column(Text)  # JSON-encoded context
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime)
    acknowledged_by = Column(String(255))
    
    relay = relationship("Relay", back_populates="alerts")


class AuditLog(Base):
    """Security audit log."""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(String(255))
    action = Column(String(100), nullable=False)
    resource = Column(String(255))
    result = Column(String(20))  # SUCCESS, FAILURE
    details = Column(Text)
    ip_address = Column(String(45))
    user_agent = Column(String(255))


class Database:
    """Database manager with connection pooling and retention."""
    
    def __init__(self, url: str, pool_size: int = 10, retention_days: int = 90):
        self.url = url
        self.retention_days = retention_days
        
        self.engine = create_engine(
            url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
    
    def init_db(self):
        """Initialize database schema."""
        Base.metadata.create_all(bind=self.engine)
    
    @contextmanager
    def session(self):
        """Context manager for database sessions."""
        db = self.SessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    
    def get_or_create_relay(self, name: str, fingerprint: str = None, 
                           host: str = None, port: int = None) -> Relay:
        """Get or create a relay record."""
        with self.session() as db:
            relay = db.query(Relay).filter_by(name=name).first()
            if not relay:
                relay = Relay(
                    name=name,
                    fingerprint=fingerprint,
                    host=host,
                    control_port=port
                )
                db.add(relay)
                db.flush()
            relay.last_seen = datetime.utcnow()
            db.refresh(relay)
            return relay
    
    def store_metric(self, relay_id: int, **kwargs):
        """Store a bandwidth metric."""
        with self.session() as db:
            metric = BandwidthMetric(
                relay_id=relay_id,
                timestamp=datetime.utcnow(),
                **kwargs
            )
            db.add(metric)
    
    def store_circuit(self, relay_id: int, **kwargs):
        """Store circuit information."""
        with self.session() as db:
            record = CircuitRecord(
                relay_id=relay_id,
                timestamp=datetime.utcnow(),
                **kwargs
            )
            db.add(record)
    
    def store_alert(self, relay_id: int, alert_type: str, severity: str,
                   message: str, metrics: Dict = None):
        """Store an alert."""
        with self.session() as db:
            alert = AlertRecord(
                relay_id=relay_id,
                alert_type=alert_type,
                severity=severity,
                message=message,
                metrics=json.dumps(metrics) if metrics else None
            )
            db.add(alert)
    
    def store_audit(self, action: str, user_id: str = None, resource: str = None,
                   result: str = "SUCCESS", details: str = None,
                   ip_address: str = None, user_agent: str = None):
        """Store audit log entry."""
        with self.session() as db:
            log = AuditLog(
                user_id=user_id,
                action=action,
                resource=resource,
                result=result,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent
            )
            db.add(log)
    
    def get_metrics_range(self, relay_id: int, start: datetime, 
                         end: datetime) -> List[BandwidthMetric]:
        """Get metrics within time range."""
        with self.session() as db:
            return db.query(BandwidthMetric).filter(
                BandwidthMetric.relay_id == relay_id,
                BandwidthMetric.timestamp >= start,
                BandwidthMetric.timestamp <= end
            ).order_by(BandwidthMetric.timestamp).all()
    
    def get_latest_metrics(self, relay_id: int, limit: int = 100) -> List[BandwidthMetric]:
        """Get latest metrics."""
        with self.session() as db:
            return db.query(BandwidthMetric).filter(
                BandwidthMetric.relay_id == relay_id
            ).order_by(BandwidthMetric.timestamp.desc()).limit(limit).all()
    
    def get_aggregated_stats(self, relay_id: int, hours: int = 24) -> Dict[str, Any]:
        """Get aggregated statistics."""
        with self.session() as db:
            start = datetime.utcnow() - timedelta(hours=hours)
            result = db.query(
                func.avg(BandwidthMetric.read_rate_kibs).label("avg_read"),
                func.avg(BandwidthMetric.write_rate_kibs).label("avg_write"),
                func.max(BandwidthMetric.read_rate_kibs).label("max_read"),
                func.max(BandwidthMetric.write_rate_kibs).label("max_write"),
                func.avg(BandwidthMetric.latency_ms).label("avg_latency"),
                func.count(BandwidthMetric.id).label("sample_count")
            ).filter(
                BandwidthMetric.relay_id == relay_id,
                BandwidthMetric.timestamp >= start
            ).first()
            
            return {
                "avg_read_kibs": result.avg_read or 0,
                "avg_write_kibs": result.avg_write or 0,
                "max_read_kibs": result.max_read or 0,
                "max_write_kibs": result.max_write or 0,
                "avg_latency_ms": result.avg_latency or 0,
                "sample_count": result.sample_count or 0
            }
    
    def get_unacknowledged_alerts(self, relay_id: int = None) -> List[AlertRecord]:
        """Get unacknowledged alerts."""
        with self.session() as db:
            query = db.query(AlertRecord).filter_by(acknowledged=False)
            if relay_id:
                query = query.filter_by(relay_id=relay_id)
            return query.order_by(AlertRecord.timestamp.desc()).all()
    
    def cleanup_old_data(self):
        """Remove data older than retention period."""
        cutoff = datetime.utcnow() - timedelta(days=self.retention_days)
        with self.session() as db:
            db.query(BandwidthMetric).filter(
                BandwidthMetric.timestamp < cutoff
            ).delete(synchronize_session=False)
            db.query(CircuitRecord).filter(
                CircuitRecord.timestamp < cutoff
            ).delete(synchronize_session=False)
            db.query(AlertRecord).filter(
                AlertRecord.timestamp < cutoff
            ).delete(synchronize_session=False)