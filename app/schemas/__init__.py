"""
API schemas for the Cylestio Mini-Local Server.

This module contains Pydantic models for API requests and responses.
"""

from app.schemas.errors import ErrorResponse, ValidationErrorItem, ErrorDetail
from app.schemas.event import EventCreate, EventRead, EventUpdate, EventList
from app.schemas.telemetry import (
    TelemetryRecord, TelemetryResponse, 
    TelemetryBatchRequest, TelemetryBatchResponse
)

# Export schemas
__all__ = [
    "ErrorResponse", "ValidationErrorItem", "ErrorDetail",
    "EventCreate", "EventRead", "EventUpdate", "EventList",
    "TelemetryRecord", "TelemetryResponse", 
    "TelemetryBatchRequest", "TelemetryBatchResponse"
] 