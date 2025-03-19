"""
API package for the Cylestio Mini-Local Server.

This package contains the API endpoints for the Cylestio Mini-Local Server.
"""

from fastapi import APIRouter

from app.api import business_logic
from app.api import v1

# Create the main API router
api_router = APIRouter()

# Include the business logic router
api_router.include_router(
    business_logic.router,
    prefix="/business-logic",
    tags=["Business Logic"]
)

# Include the v1 API router
api_router.include_router(
    v1.router,
    prefix="/v1",
    tags=["API v1"]
)

# Export the API router
__all__ = ["api_router"] 