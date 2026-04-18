"""
Config API Router — Endpoints for reading and updating system configuration.
"""
from fastapi import APIRouter
from backtesting_lab.server.models import ConfigUpdateRequest, ConfigHistoryItem, StatusResponse
from backtesting_lab.config.config_manager import get_config, update_config, reset_config, get_config_manager

router = APIRouter(prefix="/api/config", tags=["Configuration"])


@router.get("")
async def get_current_config():
    """Get the current active configuration."""
    return get_config().model_dump()


@router.put("", response_model=StatusResponse)
async def update_system_config(req: ConfigUpdateRequest):
    """Update configuration with partial values. Saves snapshot before applying."""
    try:
        update_config(req.updates)
        return StatusResponse(
            success=True,
            message="Configuration updated successfully",
            data={"updated_keys": list(req.updates.keys())}
        )
    except Exception as e:
        return StatusResponse(success=False, message=f"Config update failed: {str(e)}")


@router.post("/reset", response_model=StatusResponse)
async def reset_system_config():
    """Reset configuration to defaults."""
    try:
        reset_config()
        return StatusResponse(success=True, message="Configuration reset to defaults")
    except Exception as e:
        return StatusResponse(success=False, message=f"Reset failed: {str(e)}")


@router.get("/history", response_model=list[ConfigHistoryItem])
async def get_config_history():
    """Get config change history."""
    manager = get_config_manager()
    return manager.get_history()
