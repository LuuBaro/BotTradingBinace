"""
FastAPI Server - REST API + WebSocket for dashboard
"""
import asyncio
import sqlite3
from datetime import datetime, timedelta
from typing import List
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from packages.shared.config import settings
from packages.shared.database import AsyncSessionFactory, init_db, close_db, get_db
from packages.shared.models import (
    BotConfig,
    Event,
    Position,
    Order,
    Decision,
    RiskLog,
    AuditLog,
    Signal,
)
from packages.shared.schemas import RiskConfig
from packages.shared.logger import logger
from apps.api.phase4_routes import router as phase4_router
from apps.api.phase6_routes import router as phase6_router
from apps.api.websocket import ws_manager


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup on startup/shutdown"""
    logger.info("api_server_starting")
    try:
        await init_db()
    except sqlite3.OperationalError as exc:
        logger.warning("api_init_db_skipped", error=str(exc))
    # Start background polling tasks
    polling_task = asyncio.create_task(poll_and_broadcast_events())
    yield
    polling_task.cancel()
    try:
        await polling_task
    except asyncio.CancelledError:
        pass
    logger.info("api_server_shutting_down")
    await close_db()

async def poll_and_broadcast_events():
    """Poll database for new events and broadcast via WebSocket"""
    last_event_id = 0
    
    # Get initial last_event_id to only broadcast new ones
    try:
        async with AsyncSessionFactory() as session:
            result = await session.execute(select(Event).order_by(desc(Event.id)).limit(1))
            last_event = result.scalar_one_or_none()
            if last_event:
                last_event_id = last_event.id
    except Exception as e:
        logger.error("initial_event_id_fetch_failed", error=str(e))

    while True:
        try:
            async with AsyncSessionFactory() as session:
                query = select(Event).where(Event.id > last_event_id).order_by(Event.id.asc())
                result = await session.execute(query)
                new_events = result.scalars().all()
                
                for event in new_events:
                    event_data = {
                        "id": event.id,
                        "timestamp": event.timestamp.isoformat() + "Z" if not event.timestamp.tzinfo else event.timestamp.isoformat(),
                        "level": event.level.lower(),
                        "code": event.code,
                        "message": event.message,
                        "data": event.data_json
                    }
                    await ws_manager.broadcast_event(event_data)
                    last_event_id = event.id
                    
        except Exception as e:
            logger.error("event_polling_failed", error=str(e))
            
        await asyncio.sleep(2) # Poll every 2 seconds


# Create FastAPI app
app = FastAPI(
    title="AI Trading Bot API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware - explicit origins required when using Authorization headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
app.include_router(phase4_router, prefix="/api")
app.include_router(phase6_router, prefix="/api")


#Dependency imported from packages.shared.database


# Endpoints consolidated in phase4_routes.py


@app.post("/risk/config")
async def update_risk_config(
    risk_config: RiskConfig,
    db: AsyncSession = Depends(get_db),
):
    """Create new risk configuration version"""
    # Deactivate current config
    result = await db.execute(
        select(BotConfig).where(BotConfig.is_active == True)
    )
    current_configs = result.scalars().all()
    for config in current_configs:
        config.is_active = False

    # Get next version number
    last_version_result = await db.execute(
        select(BotConfig).order_by(desc(BotConfig.version)).limit(1)
    )
    last_config = last_version_result.scalar_one_or_none()
    next_version = (last_config.version + 1) if last_config else 1

    # Create new config
    new_config = BotConfig(
        env=settings.env,
        symbols_json={"symbols": ["BTCUSDT"]},  # Default symbols
        risk_json=risk_config.model_dump(),
        version=next_version,
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(new_config)

    # Add audit log
    audit = AuditLog(
        timestamp=datetime.utcnow(),
        actor="api",
        action="update_risk_config",
        target=f"version_{next_version}",
        details_json=risk_config.model_dump(),
    )
    db.add(audit)

    await db.commit()

    logger.info("risk_config_updated", version=next_version)

    return {
        "status": "success",
        "version": next_version,
        "message": "Risk configuration updated",
    }


# === Worker Control Endpoints (Phase 2) ===

# Global state for worker control
worker_state = {
    "is_paused": False,
    "pause_reason": None,
    "paused_at": None,
}


@app.post("/actions/pause")
async def pause_worker(reason: str = "Manual pause"):
    """Pause worker (stop new orders)"""
    worker_state["is_paused"] = True
    worker_state["pause_reason"] = reason
    worker_state["paused_at"] = datetime.utcnow().isoformat()
    
    logger.info("worker_paused", reason=reason)
    
    return {
        "status": "success",
        "message": "Worker paused",
        "paused_at": worker_state["paused_at"],
    }


@app.post("/actions/resume")
async def resume_worker(db: AsyncSession = Depends(get_db)):
    """Resume worker (allow new orders)"""
    worker_state["is_paused"] = False
    worker_state["pause_reason"] = None
    paused_duration = (
        datetime.utcnow() - datetime.fromisoformat(worker_state["paused_at"])
    ).total_seconds() if worker_state["paused_at"] else 0
    
    # Log resume event
    event = Event(
        timestamp=datetime.utcnow(),
        level="INFO",
        code="WORKER_RESUMED",
        message=f"Worker resumed after {paused_duration:.1f}s pause",
        data_json={"paused_duration_sec": paused_duration},
    )
    db.add(event)
    await db.commit()
    
    logger.info("worker_resumed", paused_duration_sec=paused_duration)
    
    return {
        "status": "success",
        "message": "Worker resumed",
        "paused_duration_sec": paused_duration,
    }


# Actions status and approval endpoints moved to phase4_routes.py


# === Reconciliation Endpoints (Phase 2) ===

# Global reconciliation state
recon_state = {
    "last_summary": None,
    "last_reconcile_at": None,
}


@app.post("/actions/sync_now")
async def trigger_reconciliation(db: AsyncSession = Depends(get_db)):
    """Trigger reconciliation immediately (instead of waiting for interval)"""
    # This will be called by worker
    # For now, just log the request
    logger.info("reconciliation_triggered_manually")
    
    return {
        "status": "success",
        "message": "Reconciliation triggered",
        "sync_started_at": datetime.utcnow().isoformat(),
    }


@app.get("/recon/summary")
async def get_reconciliation_summary():
    """Get last reconciliation summary"""
    if not recon_state["last_summary"]:
        return {
            "total_mismatches": 0,
            "position_mismatches": 0,
            "last_sync": datetime.utcnow().isoformat(),
            "status": "SYNCHRONIZED"
        }
    
    summary = recon_state["last_summary"]
    return {
        "total_mismatches": summary.get("total_mismatches", 0),
        "position_mismatches": summary.get("position_mismatches", 0),
        "last_sync": recon_state["last_reconcile_at"],
        "status": "SYNCHRONIZED" if summary.get("total_mismatches", 0) == 0 else "MISMATCH"
    }


# === Circuit Breaker Endpoints (Phase 2) ===

# Global circuit breaker instance
circuit_breaker = None


@app.get("/circuit-breaker/status")
async def get_circuit_breaker_status():
    """Get circuit breaker status (safe/unsafe for trading)"""
    if circuit_breaker is None:
        return {"status": "error", "message": "Circuit breaker not initialized"}
    
    return {
        "circuit_breaker": circuit_breaker.get_status(),
        "safe_for_trading": circuit_breaker.is_safe_for_trading(),
    }


# === WebSocket Endpoint ===

class ConnectionManager:
    """Manage WebSocket connections"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("websocket_connected", total_connections=len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info("websocket_disconnected", total_connections=len(self.active_connections))

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error("websocket_broadcast_error", error=str(e))


manager = ConnectionManager()


@app.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket stream for real-time updates"""
    await manager.connect(websocket)
    
    try:
        while True:
            # Send mock status updates every 2 seconds
            async with AsyncSessionFactory() as db:
                # Get recent data
                events_result = await db.execute(
                    select(Event).order_by(desc(Event.timestamp)).limit(5)
                )
                recent_events = events_result.scalars().all()

                positions_result = await db.execute(select(Position))
                positions = positions_result.scalars().all()

                # Send update
                await websocket.send_json({
                    "type": "status",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {
                        "positions_count": len(positions),
                        "recent_events": [
                            {
                                "level": e.level,
                                "code": e.code,
                                "message": e.message,
                            }
                            for e in recent_events
                        ],
                    },
                })

            await asyncio.sleep(2)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error("websocket_error", error=str(e))
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "apps.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
