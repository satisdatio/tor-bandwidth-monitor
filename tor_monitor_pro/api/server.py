"""FastAPI server with authentication and routes."""

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
import logging
import time

from ..config import Config
from ..controller import MultiRelayController
from ..database import Database
from ..alerts import AlertManager
from ..anomaly import AnomalyDetector
from ..audit import AuditLogger
from ..prometheus import PrometheusExporter
from ..plugins import PluginManager
from .auth import get_current_user, User
from .routes import router as api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info("Tor Monitor Pro API starting...")
    
    # Initialize background tasks
    app.state.metrics_task = None
    
    yield
    
    # Shutdown
    logger.info("Tor Monitor Pro API shutting down...")
    
    if app.state.metrics_task:
        app.state.metrics_task.cancel()


def create_api_server(
    config: Config,
    controller: MultiRelayController,
    database: Database,
    alert_manager: AlertManager,
    anomaly_detector: Optional[AnomalyDetector],
    audit_logger: AuditLogger,
    prometheus: Optional[PrometheusExporter],
    plugin_manager: PluginManager
) -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="Tor Monitor Pro API",
        description="Professional Tor relay monitoring API",
        version=config.version,
        lifespan=lifespan,
        docs_url="/api/docs" if config.debug else None,
        redoc_url="/api/redoc" if config.debug else None
    )
    
    # Store dependencies in app state
    app.state.config = config
    app.state.controller = controller
    app.state.database = database
    app.state.alert_manager = alert_manager
    app.state.anomaly_detector = anomaly_detector
    app.state.audit_logger = audit_logger
    app.state.prometheus = prometheus
    app.state.plugin_manager = plugin_manager
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )
    
    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = (time.time() - start_time) * 1000
        
        # Log to audit
        user_id = "anonymous"
        if hasattr(request.state, "user"):
            user_id = request.state.user.username
        
        audit_logger.log_api_access(
            user_id=user_id,
            endpoint=str(request.url.path),
            method=request.method,
            status_code=response.status_code,
            ip_address=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent", "")
        )
        
        logger.debug(f"{request.method} {request.url.path} - {response.status_code} - {duration:.2f}ms")
        return response
    
    # Error handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(exc) if config.debug else None}
        )
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        relays = controller.get_connected_relays()
        return {
            "status": "healthy",
            "version": config.version,
            "relays_connected": len(relays),
            "relays_total": len(controller.relays)
        }
    
    # Prometheus metrics endpoint
    if prometheus:
        @app.get("/metrics")
        async def metrics():
            """Prometheus metrics endpoint."""
            return Response(
                content=prometheus.generate(),
                media_type=prometheus.get_content_type()
            )
    
    # Include API routes
    app.include_router(api_router, prefix="/api")
    
    # Mount static files for dashboard
    web_dir = Path(__file__).parent.parent / "web" / "static"
    if web_dir.exists():
        app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")
        
        @app.get("/dashboard")
        async def dashboard():
            """Serve dashboard HTML."""
            from fastapi.responses import FileResponse
            index_path = web_dir / "index.html"
            if index_path.exists():
                return FileResponse(index_path)
            return JSONResponse(
                status_code=404,
                content={"error": "Dashboard not found"}
            )
    
    return app


# Helper to get dependencies
def get_controller(request: Request) -> MultiRelayController:
    return request.app.state.controller


def get_database(request: Request) -> Database:
    return request.app.state.database


def get_alert_manager(request: Request) -> AlertManager:
    return request.app.state.alert_manager


def get_config(request: Request) -> Config:
    return request.app.state.config