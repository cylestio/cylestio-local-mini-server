"""
Telemetry schemas for the Cylestio Monitor.

This module defines the Pydantic schemas for telemetry data validation and serialization.
"""

from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator


class TelemetryRecord(BaseModel):
    """Schema for a telemetry record received from an agent."""
    
    timestamp: Union[datetime, str] = Field(..., description="The timestamp when the event occurred")
    agent_id: str = Field(..., description="The ID of the agent that generated the event")
    event_type: str = Field(..., description="The type of the event")
    level: Optional[str] = Field("INFO", description="The log level of the event")
    channel: Optional[str] = Field("UNKNOWN", description="The channel the event was sent through")
    direction: Optional[str] = Field(None, description="The direction of the event (outgoing or incoming)")
    session_id: Optional[str] = Field(None, description="The session ID for the event")
    caller: Optional[Dict[str, Any]] = Field(None, description="Information about the caller")
    data: Optional[Dict[str, Any]] = Field(None, description="The event data payload")
    
    @validator('timestamp', pre=True)
    def validate_timestamp(cls, v):
        """Convert string timestamp to datetime if needed."""
        if isinstance(v, str):
            try:
                # Handle ISO format with timezone
                if 'Z' in v:
                    v = v.replace('Z', '+00:00')
                return datetime.fromisoformat(v)
            except ValueError:
                # If not ISO format, try other formats or raise an error
                raise ValueError("Invalid timestamp format")
        return v
    
    class Config:
        from_attributes = True


class TelemetryResponse(BaseModel):
    """Schema for the response to a telemetry record submission."""
    
    status: str = Field(..., description="Status of the telemetry record processing")
    message: str = Field(..., description="Message about the processing result")
    event_id: Optional[int] = Field(None, description="The ID of the created event")
    
    class Config:
        from_attributes = True


class TelemetryBatchRequest(BaseModel):
    """Schema for a batch of telemetry records."""
    
    records: List[TelemetryRecord] = Field(..., description="List of telemetry records")
    
    class Config:
        from_attributes = True


class TelemetryBatchResponse(BaseModel):
    """Schema for the response to a batch of telemetry records."""
    
    status: str = Field(..., description="Status of the batch processing")
    message: str = Field(..., description="Message about the processing result")
    processed: int = Field(..., description="Number of records processed")
    failed: int = Field(..., description="Number of records that failed processing")
    event_ids: List[int] = Field(..., description="List of created event IDs")
    
    class Config:
        from_attributes = True 