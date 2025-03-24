"""
API v1 package for the Cylestio Mini-Local Server.

This package contains the v1 API endpoints for the dashboard.
"""

from fastapi import APIRouter

from app.api.v1 import agents, events, alerts
from app.api.v1.metrics import router as metrics_router
from app.routers.telemetry import router as telemetry_router
from app.routers.business_logic import router as business_logic_router

# Create the main v1 API router 
router = APIRouter()

# Include the telemetry router with specific tag
router.include_router(telemetry_router, prefix="/telemetry", tags=["Telemetry"])

# Include the business logic router
router.include_router(business_logic_router, prefix="/business-logic", tags=["Business Logic"])

# Include the various API routers with specific tags
router.include_router(agents.router, prefix="/agents", tags=["Agents"])
router.include_router(events.router, prefix="/events", tags=["Events"])
router.include_router(metrics_router)
router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])

# Export the API router
__all__ = ["router"] 