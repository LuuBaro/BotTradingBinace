"""
Phase 4 Dashboard API Endpoints
Dashboard authentication, config versioning, WebSocket streams
"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.database import AsyncSessionFactory
from packages.shared.logger import logger
from apps.api.auth import jwt_handler, user_manager, Token
from apps.api.websocket import ws_manager, WsStreamConnection
from packages.shared.config_versioning import ConfigVersionManager


# Request models
class LoginRequest(BaseModel):
    username: str
    password: str


router = APIRouter(prefix="/api", tags=["dashboard"])
security = HTTPBearer()


# ===== Authentication Endpoints =====

@router.post("/auth/login", response_model=dict)
async def login(request: LoginRequest):
    """Login and get JWT token"""
    if not user_manager.verify_password(request.username, request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    user = user_manager.get_user(request.username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    token = jwt_handler.create_access_token(user)

    logger.info("user_login", username=request.username, role=user.role)

    return {
        "access_token": token.access_token,
        "token_type": token.token_type,
        "expires_in": token.expires_in,
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
        },
    }


@router.post("/auth/logout")
async def logout(credentials: Any = Depends(security)):
    """Logout (invalidate token)"""
    user = jwt_handler.verify_token(credentials.credentials)
    if user:
        logger.info("user_logout", username=user.username)
    return {"detail": "Logged out successfully"}


@router.post("/auth/refresh")
async def refresh_token(token: str, credentials: Any = Depends(security)):
    """Refresh JWT token"""
    user = jwt_handler.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    new_token = jwt_handler.create_access_token(user)
    return {
        "access_token": new_token.access_token,
        "token_type": new_token.token_type,
        "expires_in": new_token.expires_in,
    }


# ===== Bot Status Endpoints =====

@router.get("/bot/status")
async def get_bot_status(credentials: Any = Depends(security)):
    """Get bot status"""
    user = jwt_handler.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # TODO: Connect to actual worker state
    return {
        "mode": "BINANCE",
        "uptime_seconds": 3600,
        "paused": False,
        "total_positions": 5,
        "total_orders": 12,
    }


@router.get("/health/status")
async def get_health_status(credentials: Any = Depends(security)):
    """Get system health status"""
    user = jwt_handler.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # TODO: Connect to actual health checks
    return {
        "ws_connected": True,
        "ws_reconnects": 0,
        "rest_healthy": True,
        "rest_last_request": "2024-01-15T12:00:00Z",
        "rest_errors": 0,
        "db_healthy": True,
        "db_connected": True,
        "db_pool_size": 5,
        "db_pool_max": 10,
        "circuit_breaker_state": "CLOSED",
        "is_safe_for_trading": True,
    }


@router.get("/health/latency")
async def get_latency_metrics(credentials: Any = Depends(security)):
    """Get latency metrics"""
    user = jwt_handler.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # TODO: Connect to actual metrics
    return {
        "ws_p95": 45,
        "rest_p95": 120,
        "clock_skew": 50,
    }


# ===== Risk Configuration Endpoints =====

@router.get("/config/risk")
async def get_risk_config(credentials: Any = Depends(security)):
    """Get current risk configuration"""
    user = jwt_handler.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    async with AsyncSessionFactory() as session:
        manager = ConfigVersionManager(session)
        config = await manager.get_current_config("risk")

        if not config:
            # Return default config
            config = {
                "max_leverage": 10,
                "max_position_size": 1.0,
                "max_daily_loss": 1000.0,
                "min_win_rate": 0.55,
            }

        return config


@router.post("/config/risk")
async def update_risk_config(
    config: dict,
    credentials: Any = Depends(security),
):
    """Update risk configuration (creates new version)"""
    user = jwt_handler.verify_token(credentials.credentials)
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    async with AsyncSessionFactory() as session:
        manager = ConfigVersionManager(session)
        version = await manager.create_version(
            config_type="risk",
            config=config,
            created_by=user.username,
            description=f"Updated by {user.username}",
        )

        return config


@router.get("/config/risk/versions")
async def get_config_versions(credentials: Any = Depends(security)):
    """Get risk configuration versions"""
    user = jwt_handler.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    async with AsyncSessionFactory() as session:
        manager = ConfigVersionManager(session)
        versions = await manager.get_all_versions("risk", limit=50)

        return [v.to_dict() for v in versions]


@router.post("/config/risk/rollback/{version_id}")
async def rollback_config(
    version_id: str,
    credentials: Any = Depends(security),
):
    """Rollback to specific config version"""
    user = jwt_handler.verify_token(credentials.credentials)
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    async with AsyncSessionFactory() as session:
        manager = ConfigVersionManager(session)
        version = await manager.rollback_to_version(version_id, user.username)

        return version.config_json


# ===== WebSocket Endpoint =====

@router.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket, token: str = None):
    """WebSocket stream for real-time updates"""
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user = jwt_handler.verify_token(token)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    connection = await ws_manager.connect(websocket, user.id)

    try:
        while True:
            # Receive client messages (subscribe/unsubscribe)
            data = await websocket.receive_json()
            await ws_manager.process_client_message(user.id, data)

    except WebSocketDisconnect:
        ws_manager.disconnect(user.id)
        logger.info("ws_disconnected", user_id=user.id)

    except Exception as e:
        logger.error("ws_error", error=str(e))
        ws_manager.disconnect(user.id)


# ===== Positions & Orders (Existing - Updated for Dashboard) =====

@router.get("/positions")
async def get_positions(credentials: Any = Depends(security)):
    """Get all positions"""
    user = jwt_handler.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    async with AsyncSessionFactory() as session:
        from sqlalchemy import select
        from packages.shared.models import Position

        result = await session.execute(select(Position))
        positions = result.scalars().all()

        return [
            {
                "id": str(p.id),
                "symbol": p.symbol,
                "qty": p.qty,
                "entry_price": float(p.entry_price),
                "unrealized_pnl": float(p.unrealized_pnl) if p.unrealized_pnl else 0,
                "stop_loss": float(p.stop_loss) if p.stop_loss else None,
                "take_profit": float(p.take_profit) if p.take_profit else None,
                "leverage": float(p.leverage) if p.leverage else 1,
            }
            for p in positions
        ]


@router.get("/orders")
async def get_orders(credentials: Any = Depends(security)):
    """Get all orders"""
    user = jwt_handler.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    async with AsyncSessionFactory() as session:
        from sqlalchemy import select
        from packages.shared.models import Order

        result = await session.execute(select(Order))
        orders = result.scalars().all()

        return [
            {
                "id": str(o.id),
                "symbol": o.symbol,
                "side": o.side,
                "quantity": float(o.quantity),
                "status": o.status,
                "avg_price": float(o.avg_price) if o.avg_price else 0,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in orders
        ]


@router.get("/decisions")
async def get_decisions(
    limit: int = 100,
    credentials: Any = Depends(security),
):
    """Get recent decisions"""
    user = jwt_handler.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    async with AsyncSessionFactory() as session:
        from sqlalchemy import select
        from packages.shared.models import Decision

        result = await session.execute(
            select(Decision)
            .order_by(Decision.timestamp.desc())
            .limit(limit)
        )
        decisions = result.scalars().all()

        return [
            {
                "id": str(d.id),
                "symbol": d.decision_json.get("symbol", ""),
                "action": d.decision_json.get("action", ""),
                "confidence": float(d.confidence),
                "regime": d.regime,
                "timestamp": d.timestamp.isoformat(),
                "trace_id": d.trace_id,
            }
            for d in decisions
        ]


@router.get("/decisions/{trace_id}")
async def get_decision_trace(
    trace_id: str,
    credentials: Any = Depends(security),
):
    """Get full decision trace pipeline"""
    user = jwt_handler.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    async with AsyncSessionFactory() as session:
        from sqlalchemy import select
        from packages.shared.models import Decision, Order, Event

        # Get decision
        result = await session.execute(
            select(Decision).where(Decision.trace_id == trace_id)
        )
        decision = result.scalar_one_or_none()

        if not decision:
            raise HTTPException(status_code=404, detail="Trace not found")

        # Get related events
        result = await session.execute(
            select(Event)
            .where(Event.trace_id == trace_id)
            .order_by(Event.timestamp)
        )
        events = result.scalars().all()

        return {
            "trace_id": trace_id,
            "decision_json": decision.decision_json,
            "confidence": float(decision.confidence),
            "risk_passed": decision.risk_passed,
            "order_id": decision.order_id,
            "events": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "level": e.level,
                    "message": e.message,
                    "details": e.details_json,
                }
                for e in events
            ],
        }


@router.get("/recon/summary")
async def get_recon_summary(credentials: Any = Depends(security)):
    """Get reconciliation summary"""
    user = jwt_handler.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # TODO: Connect to actual reconciliation state
    return {
        "last_sync": "2024-01-15T12:00:00Z",
        "total_mismatches": 0,
        "position_mismatches": 0,
        "order_mismatches": 0,
    }


@router.get("/audit")
async def get_audit_log(
    limit: int = 100,
    offset: int = 0,
    credentials: Any = Depends(security),
):
    """Get audit log"""
    user = jwt_handler.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    async with AsyncSessionFactory() as session:
        from sqlalchemy import select
        from packages.shared.models import AuditLog

        result = await session.execute(
            select(AuditLog)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        logs = result.scalars().all()

        return [
            {
                "timestamp": l.timestamp.isoformat(),
                "actor": l.actor,
                "action": l.action,
                "target": l.target,
                "details_json": l.details_json,
            }
            for l in logs
        ]


# ===== Control Actions =====

@router.post("/actions/pause")
async def pause_action(credentials: Any = Depends(security)):
    """Pause trading"""
    user = jwt_handler.verify_token(credentials.credentials)
    if not user or user.role not in ("admin", "trader"):
        raise HTTPException(status_code=403, detail="Forbidden")

    logger.info("pause_action_triggered", user=user.username)

    # TODO: Call worker pause endpoint
    return {"detail": "Trading paused"}


@router.post("/actions/resume")
async def resume_action(credentials: Any = Depends(security)):
    """Resume trading"""
    user = jwt_handler.verify_token(credentials.credentials)
    if not user or user.role not in ("admin", "trader"):
        raise HTTPException(status_code=403, detail="Forbidden")

    logger.info("resume_action_triggered", user=user.username)

    # TODO: Call worker resume endpoint
    return {"detail": "Trading resumed"}


@router.post("/actions/sync_now")
async def sync_now_action(credentials: Any = Depends(security)):
    """Force reconciliation"""
    user = jwt_handler.verify_token(credentials.credentials)
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    logger.info("sync_now_action_triggered", user=user.username)

    # TODO: Call worker sync endpoint
    return {"detail": "Sync started"}
