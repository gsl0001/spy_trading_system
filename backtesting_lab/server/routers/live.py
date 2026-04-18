"""
Live Trading API Router — Endpoints for controlling autonomous trading.
"""
from fastapi import APIRouter
from backtesting_lab.server.models import (
    LiveStartRequest, LiveStatusResponse,
    EmergencyStopResponse, StatusResponse
)

router = APIRouter(prefix="/api/live", tags=["Live Trading"])

# Global orchestrator reference (injected from main.py)
_orchestrator = None


def set_orchestrator(orchestrator):
    """Inject the trading orchestrator instance."""
    global _orchestrator
    _orchestrator = orchestrator


@router.post("/start", response_model=StatusResponse)
async def start_trading(req: LiveStartRequest):
    """Start the autonomous trading loop."""
    if _orchestrator is None:
        return StatusResponse(success=False, message="Trading engine not initialized")

    if req.mode == "live" and not req.confirm:
        return StatusResponse(
            success=False,
            message="LIVE mode requires explicit confirmation. Set confirm=true."
        )

    result = _orchestrator.start(mode=req.mode)
    return StatusResponse(**result)


@router.post("/stop", response_model=StatusResponse)
async def stop_trading():
    """Stop the autonomous trading loop gracefully."""
    if _orchestrator is None:
        return StatusResponse(success=False, message="Trading engine not initialized")

    result = _orchestrator.stop()
    return StatusResponse(**result)


@router.get("/status", response_model=LiveStatusResponse)
async def get_live_status():
    """Get current live trading status."""
    if _orchestrator is None:
        return LiveStatusResponse()

    status = _orchestrator.status
    return LiveStatusResponse(**status)


@router.get("/positions")
async def get_positions():
    """Get active positions."""
    if _orchestrator is None:
        return {"positions": []}

    return {"positions": _orchestrator.status.get("active_positions", [])}


@router.post("/emergency-stop", response_model=EmergencyStopResponse)
async def emergency_stop():
    """Emergency stop — close all positions and halt trading immediately."""
    if _orchestrator is None:
        return EmergencyStopResponse(
            success=False,
            message="Trading engine not initialized"
        )

    result = _orchestrator.emergency_stop()
    return EmergencyStopResponse(**result)
