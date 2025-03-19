"""
API v1 package for the Cylestio Mini-Local Server.

This package contains the v1 API endpoints for the dashboard.
"""

from fastapi import APIRouter

from app.api.v1 import agents, events, metrics, alerts

# Create the main v1 API router
router = APIRouter()

# Include the various API routers
router.include_router(agents.router, prefix="/agents", tags=["Agents"])
router.include_router(events.router, prefix="/agents", tags=["Events"])
router.include_router(metrics.router, prefix="/agents", tags=["Metrics"])
router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])

# Export the API router
__all__ = ["router"] 