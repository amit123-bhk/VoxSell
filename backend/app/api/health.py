"""
Health check endpoints for container readiness, liveness, and monitor checks.
"""

from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import APIRouter, status

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Application Health Check",
    response_description="Returns application health status and server time.",
)
async def health_check() -> Dict[str, Any]:
    """
    Liveness probe.
    Returns 200 OK if the FastAPI process is responsive.
    """
    return {
        "status": "ok",
        "app": "VoxSell",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
