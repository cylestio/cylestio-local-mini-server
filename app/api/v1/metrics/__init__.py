"""
Metrics API module for the Cylestio Mini-Local Server.

This module provides fine-grained, modular metrics endpoints for the dashboard.
"""

from fastapi import APIRouter
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from app.api.v1.metrics import performance, token_usage, security, usage

# Create the main metrics router
router = APIRouter(prefix="/metrics")

# Add a simple test endpoint
@router.get("/test", tags=["Metrics"])
async def test_metrics_endpoint():
    """Test endpoint to verify metrics router is working."""
    return {
        "status": "success",
        "message": "Metrics API is working",
        "timestamp": datetime.now().isoformat()
    }

# Include the metrics routers
router.include_router(performance.router)
router.include_router(token_usage.router)
router.include_router(security.router)
router.include_router(usage.router)

# Export the router
__all__ = ["router"] 