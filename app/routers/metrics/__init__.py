from fastapi import APIRouter
from app.routers.metrics.agent_metrics import router as agent_router
from app.routers.metrics.event_metrics import router as event_router
from app.routers.metrics.performance_metrics import router as performance_router
from app.routers.metrics.session_metrics import router as session_router

# Create the main metrics router with proper base tag
router = APIRouter(tags=["Metrics"])

# Include the different metric routers with standardized tag naming
router.include_router(agent_router, prefix="/agents", tags=["Agent Metrics"])
router.include_router(event_router, prefix="/events", tags=["Event Metrics"])
router.include_router(performance_router, prefix="/performance", tags=["Performance Metrics"])
router.include_router(session_router, prefix="/sessions", tags=["Session Metrics"]) 