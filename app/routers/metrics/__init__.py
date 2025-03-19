from fastapi import APIRouter
from app.routers.metrics.agent_metrics import router as agent_router
from app.routers.metrics.event_metrics import router as event_router
from app.routers.metrics.performance_metrics import router as performance_router
from app.routers.metrics.session_metrics import router as session_router

# Create the main metrics router
router = APIRouter()

# Include the different metric routers
router.include_router(agent_router, prefix="/agents", tags=["agent metrics"])
router.include_router(event_router, prefix="/events", tags=["event metrics"])
router.include_router(performance_router, prefix="/performance", tags=["performance metrics"])
router.include_router(session_router, prefix="/sessions", tags=["session metrics"]) 