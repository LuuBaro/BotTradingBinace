"""
Phase 5 API Routes - AI Orchestrator and PromptPack management
Integrates AI decision making with risk and execution
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import uuid
import logging

# Assuming these imports from existing codebase
# from apps.api.auth import get_current_user, User
# from apps.api.risk import risk_manager
# from apps.api.websocket import ws_manager

from packages.shared.prompt_pack import PromptPackSchema
from packages.shared.ai_decision import AIDecisionOutput, DecisionType, DecisionStatus
from packages.shared.ai_orchestrator import AIOrchestrator
from packages.shared.llm_adapter import get_llm_adapter
from packages.shared.model_phase5 import PromptPack, AIDecision, DecisionEvent, AIMetrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["phase5-ai"])

# Global orchestrator instance
ai_orchestrator: Optional[AIOrchestrator] = None


def get_ai_orchestrator() -> AIOrchestrator:
    """Get or initialize AI orchestrator"""
    global ai_orchestrator
    if ai_orchestrator is None:
        # Initialize with LLM adapter (can be configured via env)
        llm_adapter = get_llm_adapter(provider="mock")  # Use gpt4, claude in production
        ai_orchestrator = AIOrchestrator(llm_adapter)
    return ai_orchestrator


# ============================================================================
# PromptPack Management Endpoints
# ============================================================================

@router.post("/prompt-packs")
async def create_prompt_pack(
    config: Dict[str, Any],
    # current_user: User = Depends(get_current_user)  # Admin only
) -> Dict[str, Any]:
    """
    Create new prompt pack (trader configuration)
    
    Args:
        config: PromptPackSchema as dict
        
    Returns:
        Created prompt pack with ID and version
    """
    try:
        # Validate against schema
        pack = PromptPackSchema(**config)

        # Store to database
        pack_id = str(uuid.uuid4())
        pack_record = {
            "id": pack_id,
            "name": pack.name,
            "version": pack.version,
            "description": pack.description,
            "active": pack.active,
            "config": pack.dict(),
            "created_by": "admin",  # current_user.username
            "created_at": datetime.utcnow().isoformat(),
            "symbols": pack.symbols,
            "is_default": False
        }

        logger.info(f"✅ Created prompt pack: {pack.name} v{pack.version}")

        return {
            "success": True,
            "prompt_pack": pack_record
        }

    except Exception as e:
        logger.error(f"❌ Failed to create prompt pack: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/prompt-packs")
async def list_prompt_packs(
    active: bool = True,
    limit: int = Query(50, ge=1, le=200)
) -> Dict[str, Any]:
    """
    List all prompt packs
    
    Args:
        active: Filter by active status
        limit: Limit number of results
        
    Returns:
        List of prompt packs
    """
    # Would query database for real implementation
    return {
        "prompt_packs": [],
        "total": 0
    }


@router.get("/prompt-packs/{pack_id}")
async def get_prompt_pack(pack_id: str) -> Dict[str, Any]:
    """
    Get specific prompt pack by ID
    
    Args:
        pack_id: Prompt pack ID
        
    Returns:
        Prompt pack configuration
    """
    # Database lookup
    return {
        "prompt_pack": None
    }


@router.put("/prompt-packs/{pack_id}")
async def update_prompt_pack(
    pack_id: str,
    config: Dict[str, Any],
    # current_user: User = Depends(get_current_user)  # Admin only
) -> Dict[str, Any]:
    """
    Update prompt pack (creates new version)
    
    Args:
        pack_id: Prompt pack ID
        config: Updated configuration
        
    Returns:
        New version of prompt pack
    """
    try:
        # Validate schema
        pack = PromptPackSchema(**config)

        # Create new version (don't overwrite old)
        new_version = pack.version + 1

        logger.info(f"✅ Updated prompt pack {pack_id} to v{new_version}")

        return {
            "success": True,
            "new_version": new_version
        }

    except Exception as e:
        logger.error(f"❌ Failed to update prompt pack: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/prompt-packs/{pack_id}/activate")
async def activate_prompt_pack(pack_id: str) -> Dict[str, Any]:
    """Activate a prompt pack"""
    return {"success": True, "message": f"Activated prompt pack {pack_id}"}


@router.post("/prompt-packs/{pack_id}/deactivate")
async def deactivate_prompt_pack(pack_id: str) -> Dict[str, Any]:
    """Deactivate a prompt pack"""
    return {"success": True, "message": f"Deactivated prompt pack {pack_id}"}


# ============================================================================
# AI Decision Endpoints
# ============================================================================

@router.post("/ai/decisions")
async def make_ai_decision(
    market_snapshot: Dict[str, Any],
    prompt_pack_id: str,
    current_positions: Optional[List[Dict[str, Any]]] = None,
    background_tasks: BackgroundTasks = None
) -> Dict[str, Any]:
    """
    Request AI to make trading decision
    
    Args:
        market_snapshot: Current market data
        prompt_pack_id: Which prompt pack to use
        current_positions: Current open positions
        
    Returns:
        {
            "valid": bool,
            "decision": AIDecisionOutput,
            "errors": [],
            "trace_id": str
        }
    """
    trace_id = str(uuid.uuid4())
    
    try:
        logger.info(f"[{trace_id}] Starting AI decision process")

        # Get orchestrator
        orchestrator = get_ai_orchestrator()

        # Load prompt pack (from database)
        # prompt_pack = db.query(PromptPack).filter(id=prompt_pack_id).first()
        # For now, use mock
        prompt_pack = PromptPackSchema(
            name="Demo Pack",
            symbols=["ETHUSDT"],
            regimes=[{"name": "Trending Up", "indicators": {}, "description": ""}],
            entry_playbooks=[{"side": "LONG", "regime": "Trending Up", "conditions": []}],
            exit_playbooks=[{"side": "LONG", "profit_target": "2xR", "stop_loss": "EMA20"}]
        )

        # Make decision
        result = await orchestrator.make_decision(
            market_snapshot=market_snapshot,
            prompt_pack=prompt_pack,
            current_positions=current_positions
        )

        # Store decision to database
        if result["valid"]:
            logger.info(f"[{trace_id}] ✅ Valid decision: {result['decision'].decision_type} ({result['decision'].confidence:.2%})")

            # Store AI decision
            decision_record = {
                "trace_id": trace_id,
                "prompt_pack_id": prompt_pack_id,
                "decision_type": result["decision"].decision_type,
                "status": "VALIDATED",
                "confidence": result["decision"].confidence,
                "rationale": result["decision"].rationale,
                "market_regime": result["decision"].market_regime,
                "decision_json": result["decision"].dict(),
                "is_valid_json": True,
                "created_at": datetime.utcnow().isoformat()
            }

            # Add event
            event = {
                "trace_id": trace_id,
                "event_type": "AI_GENERATED",
                "status": "SUCCESS",
                "message": f"AI generated {result['decision'].decision_type} with {result['decision'].confidence:.2%} confidence"
            }

            # Send WebSocket update
            if background_tasks:
                background_tasks.add_task(
                    _broadcast_decision_event,
                    event
                )

            result["trace_id"] = trace_id
            return result

        else:
            logger.warning(f"[{trace_id}] ❌ Invalid decision: {result['errors']}")

            # Store failed decision for audit
            decision_record = {
                "trace_id": trace_id,
                "prompt_pack_id": prompt_pack_id,
                "decision_type": "NO_TRADE",
                "status": "REJECTED",
                "confidence": 0.0,
                "is_valid_json": False,
                "validation_errors": result["errors"],
                "created_at": datetime.utcnow().isoformat()
            }

            result["trace_id"] = trace_id
            return result

    except Exception as e:
        logger.error(f"[{trace_id}] ❌ Decision process failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Decision process failed: {str(e)}")


@router.get("/ai/decisions/{trace_id}")
async def get_decision_details(trace_id: str) -> Dict[str, Any]:
    """
    Get full decision details by trace_id
    
    Shows complete pipeline: AI → Risk → Execution
    """
    return {
        "trace_id": trace_id,
        "decision": None,
        "events": []
    }


@router.get("/ai/decisions")
async def list_decisions(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """
    List AI decisions with filtering
    
    Args:
        status: Filter by decision status (PENDING, APPROVED, REJECTED, EXECUTED)
        limit: Limit results
        offset: Pagination offset
        
    Returns:
        List of decisions
    """
    return {
        "decisions": [],
        "total": 0,
        "limit": limit,
        "offset": offset
    }


@router.get("/ai/decisions/{trace_id}/events")
async def get_decision_events(trace_id: str) -> Dict[str, Any]:
    """
    Get all events for a decision
    
    Shows pipeline: AI_GENERATED → VALIDATION_PASSED → RISK_APPROVED → EXECUTED
    """
    return {
        "trace_id": trace_id,
        "events": []
    }


# ============================================================================
# AI Risk Approval Endpoints
# ============================================================================

@router.post("/ai/decisions/{trace_id}/approve")
async def approve_decision(
    trace_id: str,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Approve AI decision to proceed to execution
    
    Risk module has already validated, this is final approval
    """
    logger.info(f"[{trace_id}] Risk module approved decision")

    # Create event
    event = {
        "trace_id": trace_id,
        "event_type": "RISK_APPROVED",
        "status": "SUCCESS",
        "message": "Risk module approved decision"
    }

    background_tasks.add_task(_broadcast_decision_event, event)

    return {
        "success": True,
        "message": f"Decision {trace_id} approved for execution"
    }


@router.post("/ai/decisions/{trace_id}/reject")
async def reject_decision(
    trace_id: str,
    reason: str,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Reject AI decision (risk module veto)
    """
    logger.warning(f"[{trace_id}] Risk module rejected decision: {reason}")

    event = {
        "trace_id": trace_id,
        "event_type": "RISK_REJECTED",
        "status": "REJECTED",
        "message": f"Risk module rejected: {reason}"
    }

    background_tasks.add_task(_broadcast_decision_event, event)

    return {
        "success": True,
        "message": f"Decision {trace_id} rejected",
        "reason": reason
    }


@router.post("/ai/decisions/{trace_id}/modify")
async def modify_decision(
    trace_id: str,
    modifications: Dict[str, Any],
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Risk module modifies decision before execution
    
    E.g., reduce position size, tighten stop loss
    """
    logger.info(f"[{trace_id}] Risk module modified decision: {modifications}")

    event = {
        "trace_id": trace_id,
        "event_type": "RISK_MODIFIED",
        "status": "SUCCESS",
        "message": f"Risk module modified decision",
        "context": {"modifications": modifications}
    }

    background_tasks.add_task(_broadcast_decision_event, event)

    return {
        "success": True,
        "message": f"Decision {trace_id} modified",
        "modifications": modifications
    }


# ============================================================================
# AI Metrics & Statistics
# ============================================================================

@router.get("/ai/metrics")
async def get_ai_metrics(
    hours: int = Query(24, ge=1, le=168)
) -> Dict[str, Any]:
    """
    Get AI performance metrics
    
    Args:
        hours: Last N hours of data
        
    Returns:
        {
            "total_decisions": int,
            "valid_decisions": int,
            "risk_approved": int,
            "executed": int,
            "avg_confidence": float,
            "win_rate": float,
            "errors": int
        }
    """
    orchestrator = get_ai_orchestrator()
    stats = orchestrator.get_stats()

    return {
        "metrics": stats
    }


@router.get("/ai/metrics/by-pack")
async def get_metrics_by_pack() -> Dict[str, Any]:
    """
    Get AI metrics broken down by prompt pack
    """
    return {
        "by_pack": []
    }


# ============================================================================
# Helper Functions
# ============================================================================

async def _broadcast_decision_event(event: Dict[str, Any]):
    """Broadcast decision event via WebSocket"""
    try:
        # ws_manager.broadcast_event(event)
        logger.debug(f"Broadcasted event: {event['event_type']}")
    except Exception as e:
        logger.error(f"Failed to broadcast event: {str(e)}")


# ============================================================================
# LLM Configuration Endpoints
# ============================================================================

@router.get("/ai/llm-config")
async def get_llm_config() -> Dict[str, Any]:
    """Get current LLM configuration"""
    orchestrator = get_ai_orchestrator()
    return {
        "model": orchestrator.llm.model,
        "temperature": orchestrator.llm.temperature,
        "max_tokens": orchestrator.llm.max_tokens
    }


@router.post("/ai/llm-config")
async def update_llm_config(
    model: str,
    temperature: float = 0.3,
    max_tokens: int = 2000
) -> Dict[str, Any]:
    """Update LLM configuration"""
    global ai_orchestrator

    # Create new adapter with updated config
    llm_adapter = get_llm_adapter(
        provider="mock",  # Detect from model name in production
        model=model,
        temperature=temperature,
        max_tokens=max_tokens
    )

    ai_orchestrator = AIOrchestrator(llm_adapter)

    logger.info(f"✅ Updated LLM config: {model}")

    return {
        "success": True,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens
    }
