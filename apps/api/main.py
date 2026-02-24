"""
FastAPI Server - REST API + WebSocket for dashboard
"""
import asyncio
from datetime import datetime, timedelta
from typing import List
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from packages.shared.config import settings
from packages.shared.database import AsyncSessionFactory, init_db, close_db
from packages.shared.models import (
    BotConfig,
    Event,
    Position,
    Order,
    Decision,
    RiskLog,
    AuditLog,
)
from packages.shared.schemas import RiskConfig
from packages.shared.logger import logger
from apps.api.phase4_routes import router as phase4_router


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup on startup/shutdown"""
    logger.info("api_server_starting")
    await init_db()
    yield
    logger.info("api_server_shutting_down")
    await close_db()


# Create FastAPI app
app = FastAPI(
    title="AI Trading Bot API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(phase4_router)


# Dependency to get database session
async def get_db() -> AsyncSession:
    async with AsyncSessionFactory() as session:
        yield session


# === Health & Status Endpoints ===

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/bot/status")
async def get_bot_status(db: AsyncSession = Depends(get_db)):
    """Get bot configuration and status"""
    # Get active config
    result = await db.execute(
        select(BotConfig).where(BotConfig.is_active == True).order_by(desc(BotConfig.id))
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="No active bot configuration")

    # Get last decision
    last_decision_result = await db.execute(
        select(Decision).order_by(desc(Decision.timestamp)).limit(1)
    )
    last_decision = last_decision_result.scalar_one_or_none()

    # Count positions
    positions_result = await db.execute(select(Position))
    positions_count = len(positions_result.scalars().all())

    return {
        "env": config.env,
        "version": config.version,
        "symbols": config.symbols_json,
        "risk_config": config.risk_json,
        "active_positions": positions_count,
        "last_decision_at": last_decision.timestamp.isoformat() if last_decision else None,
        "created_at": config.created_at.isoformat(),
    }


# === Events Endpoints ===

@app.get("/events")
async def get_events(
    limit: int = Query(default=100, le=1000),
    level: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get system events"""
    query = select(Event).order_by(desc(Event.timestamp))
    
    if level:
        query = query.where(Event.level == level.upper())
    
    query = query.limit(limit)
    
    result = await db.execute(query)
    events = result.scalars().all()

    return {
        "events": [
            {
                "id": e.id,
                "timestamp": e.timestamp.isoformat(),
                "level": e.level,
                "code": e.code,
                "message": e.message,
                "trace_id": e.trace_id,
                "data": e.data_json,
            }
            for e in events
        ]
    }


# === Positions Endpoints ===

@app.get("/positions")
async def get_positions(db: AsyncSession = Depends(get_db)):
    """Get all current positions"""
    result = await db.execute(select(Position).order_by(desc(Position.opened_at)))
    positions = result.scalars().all()

    return {
        "positions": [
            {
                "id": p.id,
                "symbol": p.symbol,
                "side": p.side,
                "qty": p.qty,
                "entry_price": p.entry_price,
                "unrealized_pnl": p.unrealized_pnl,
                "opened_at": p.opened_at.isoformat(),
            }
            for p in positions
        ]
    }


# === Orders Endpoints ===

@app.get("/orders")
async def get_orders(
    status: str | None = None,
    limit: int = Query(default=50, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Get orders"""
    query = select(Order).order_by(desc(Order.created_at))
    
    if status:
        query = query.where(Order.status == status)
    
    query = query.limit(limit)
    
    result = await db.execute(query)
    orders = result.scalars().all()

    return {
        "orders": [
            {
                "id": o.id,
                "client_order_id": o.client_order_id,
                "exchange_order_id": o.exchange_order_id,
                "symbol": o.symbol,
                "side": o.side,
                "order_type": o.order_type,
                "status": o.status,
                "quantity": o.quantity,
                "filled_qty": o.filled_qty,
                "avg_price": o.avg_price,
                "created_at": o.created_at.isoformat(),
            }
            for o in orders
        ]
    }


# === Risk Config Endpoints ===

@app.get("/risk/config")
async def get_risk_config(db: AsyncSession = Depends(get_db)):
    """Get active risk configuration"""
    result = await db.execute(
        select(BotConfig).where(BotConfig.is_active == True).order_by(desc(BotConfig.id))
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="No active configuration")

    return {
        "version": config.version,
        "risk_config": config.risk_json,
        "created_at": config.created_at.isoformat(),
    }


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


@app.get("/actions/status")
async def get_worker_status():
    """Get worker status (paused/running)"""
    return {
        "is_paused": worker_state["is_paused"],
        "pause_reason": worker_state["pause_reason"],
        "paused_at": worker_state["paused_at"],
    }


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
            "status": "no_reconciliation_yet",
            "message": "No reconciliation has been performed yet",
        }
    
    return {
        "status": "success",
        "summary": recon_state["last_summary"],
        "last_reconcile_at": recon_state["last_reconcile_at"],
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
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
