from fastapi import APIRouter
from app.routers.event_create import router as create_router
from app.routers.event_queries import router as query_router

# Main events router that includes the other routers
router = APIRouter()

# Include the create and query routers with the same prefix
router.include_router(create_router, prefix="")
router.include_router(query_router, prefix="") 