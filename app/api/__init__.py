"""
API package for the Cylestio Mini-Local Server.

This package contains the API endpoints for the Cylestio Mini-Local Server.
"""

from fastapi import APIRouter

from app.api import v1

# Create the main API router
api_router = APIRouter()

# Include the v1 API router without adding tags (will use the tags from sub-routers)
api_router.include_router(
    v1.router,
    prefix="/v1"
)

# Export the API router
__all__ = ["api_router"] 