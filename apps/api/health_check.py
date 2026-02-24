"""
Health Check & Monitoring System
Tracks service health, latency, and logs for alerts
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import asyncio
import time
import logging
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["monitoring"])


class HealthStatus(str, Enum):
    """Health status enum"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ServiceHealth:
    """Service health status"""

    def __init__(self):
        self.status = HealthStatus.HEALTHY
        self.checks = {}
        self.last_check = None
        self.startup_time = datetime.utcnow()
        self.request_count = 0
        self.error_count = 0
        self.avg_response_time = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        uptime_seconds = (datetime.utcnow() - self.startup_time).total_seconds()

        return {
            "status": self.status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": uptime_seconds,
            "checks": self.checks,
            "requests": {
                "total": self.request_count,
                "errors": self.error_count,
                "error_rate": self.error_count / max(self.request_count, 1)
            },
            "performance": {
                "avg_response_time_ms": round(self.avg_response_time, 2)
            }
        }


# Global health tracker
service_health = ServiceHealth()


@router.get("")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint
    Returns current service health status
    """
    # Update timestamp
    service_health.last_check = datetime.utcnow()

    return {
        "status": service_health.status.value,
        "timestamp": datetime.utcnow().isoformat(),
        "version": "7.0"
    }


@router.get("/detailed")
async def detailed_health() -> Dict[str, Any]:
    """
    Detailed health check with all metrics
    """
    return {
        "service": service_health.to_dict(),
        "checks": await _run_health_checks()
    }


@router.get("/database")
async def database_health() -> Dict[str, Any]:
    """Check database connection and performance"""
    try:
        from sqlalchemy.ext.asyncio import create_async_engine

        start_time = time.time()

        # Try to connect
        engine = create_async_engine(
            "postgresql://bottrading:changeme@db:5432/bottrading",
            echo=False
        )

        async with engine.connect() as conn:
            await conn.execute(
                __import__('sqlalchemy').text("SELECT 1")
            )

        response_time = (time.time() - start_time) * 1000

        return {
            "status": "healthy",
            "response_time_ms": round(response_time, 2),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/redis")
async def redis_health() -> Dict[str, Any]:
    """Check Redis connection"""
    try:
        import redis

        start_time = time.time()

        r = redis.Redis(
            host='redis',
            port=6379,
            password='changeme',
            decode_responses=True
        )

        r.ping()

        response_time = (time.time() - start_time) * 1000

        return {
            "status": "healthy",
            "response_time_ms": round(response_time, 2),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/dependencies")
async def dependencies_health() -> Dict[str, Any]:
    """Check all external dependencies"""
    db_health = await database_health()
    redis_health = await redis_health()

    all_healthy = (
        db_health.get("status") == "healthy" and
        redis_health.get("status") == "healthy"
    )

    return {
        "overall_status": "healthy" if all_healthy else "degraded",
        "database": db_health,
        "redis": redis_health,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """Get service metrics"""
    return {
        "uptime_seconds": (datetime.utcnow() - service_health.startup_time).total_seconds(),
        "requests": {
            "total": service_health.request_count,
            "errors": service_health.error_count,
            "error_rate": service_health.error_count / max(service_health.request_count, 1)
        },
        "performance": {
            "avg_response_time_ms": round(service_health.avg_response_time, 2)
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/metrics/record")
async def record_metric(
    endpoint: str,
    response_time_ms: float,
    status_code: int
) -> Dict[str, str]:
    """Record request metric"""
    service_health.request_count += 1

    if status_code >= 400:
        service_health.error_count += 1

    # Update average response time
    alpha = 0.1  # Exponential moving average factor
    service_health.avg_response_time = (
        alpha * response_time_ms +
        (1 - alpha) * service_health.avg_response_time
    )

    # Update status based on error rate
    error_rate = service_health.error_count / max(service_health.request_count, 1)
    if error_rate > 0.1:  # >10% error rate = degraded
        service_health.status = HealthStatus.DEGRADED
    elif error_rate > 0.25:  # >25% error rate = unhealthy
        service_health.status = HealthStatus.UNHEALTHY
    else:
        service_health.status = HealthStatus.HEALTHY

    return {"status": "recorded"}


async def _run_health_checks() -> Dict[str, Any]:
    """Run all health checks"""
    return {
        "database": await database_health(),
        "redis": await redis_health(),
        "dependencies": await dependencies_health()
    }


# Middleware for request timing
class HealthCheckMiddleware:
    """Middleware to track request metrics"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_time = (time.time() - start_time) * 1000

                # Record metric
                try:
                    await record_metric(
                        endpoint=scope.get("path", "unknown"),
                        response_time_ms=response_time,
                        status_code=status_code
                    )
                except:
                    pass

            await send(message)

        await self.app(scope, receive, send_wrapper)


# Alert system
class AlertManager:
    """Manages health alerts"""

    def __init__(self):
        self.alerts = []
        self.thresholds = {
            "error_rate": 0.1,  # 10%
            "response_time": 2000,  # 2 seconds
            "database_latency": 500,  # 500ms
            "redis_latency": 100  # 100ms
        }

    async def check_and_alert(self):
        """Check health and trigger alerts"""
        error_rate = service_health.error_count / max(service_health.request_count, 1)

        if error_rate > self.thresholds["error_rate"]:
            await self._send_alert(
                f"High error rate: {error_rate:.1%}",
                severity="warning"
            )

        if service_health.avg_response_time > self.thresholds["response_time"]:
            await self._send_alert(
                f"High response time: {service_health.avg_response_time:.0f}ms",
                severity="warning"
            )

    async def _send_alert(self, message: str, severity: str = "warning"):
        """Send alert (webhook, email, etc.)"""
        logger.warning(f"[ALERT] {severity.upper()}: {message}")

        # TODO: Send to external alerting system (Slack, PagerDuty, etc.)
        # await send_to_slack(message, severity)
        # await send_to_pagerduty(message, severity)

        self.alerts.append({
            "message": message,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat()
        })

    def get_recent_alerts(self, limit: int = 10) -> list:
        """Get recent alerts"""
        return self.alerts[-limit:]


# Global alert manager
alert_manager = AlertManager()


def setup_health_monitoring(app):
    """Setup health monitoring for FastAPI app"""
    app.include_router(router)
    app.add_middleware(HealthCheckMiddleware)


# Background task to check health periodically
async def periodic_health_check():
    """Run health checks periodically"""
    while True:
        try:
            await alert_manager.check_and_alert()
            await asyncio.sleep(60)  # Check every minute
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            await asyncio.sleep(60)
