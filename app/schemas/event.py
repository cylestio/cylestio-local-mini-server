"""
Event schemas for the Cylestio Monitor.

This module defines the Pydantic schemas for event data validation and serialization.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class EventCreate(BaseModel):
    """Schema for creating a new Event."""
    
    timestamp: datetime = Field(..., description="The timestamp when the event occurred")
    level: str = Field(..., description="The log level of the event")
    agent_id: str = Field(..., description="The ID of the agent that generated the event")
    event_type: str = Field(..., description="The type of the event")
    channel: str = Field("UNKNOWN", description="The channel the event was sent through")
    direction: Optional[str] = Field(None, description="The direction of the event (outgoing or incoming)")
    session_id: Optional[str] = Field(None, description="The session ID for the event")
    relationship_id: Optional[str] = Field(None, description="ID for tracking related events")
    data: Optional[Dict[str, Any]] = Field(None, description="The full event data as JSON")
    duration_ms: Optional[float] = Field(None, description="The duration of the event in milliseconds")
    caller_file: Optional[str] = Field(None, description="The file that called the event")
    caller_line: Optional[int] = Field(None, description="The line number that called the event")
    caller_function: Optional[str] = Field(None, description="The function that called the event")
    alert: Optional[str] = Field(None, description="Alert status for security events")
    
    class Config:
        from_attributes = True


class EventRead(EventCreate):
    """Schema for reading an Event."""
    
    id: int = Field(..., description="The unique ID of the event")
    is_processed: bool = Field(..., description="Whether the event has been processed")
    
    class Config:
        from_attributes = True


class EventUpdate(BaseModel):
    """Schema for updating an Event."""
    
    level: Optional[str] = Field(None, description="The log level of the event")
    data: Optional[Dict[str, Any]] = Field(None, description="The full event data as JSON")
    is_processed: Optional[bool] = Field(None, description="Whether the event has been processed")
    alert: Optional[str] = Field(None, description="Alert status for security events")
    
    class Config:
        from_attributes = True


class EventList(BaseModel):
    """Schema for a list of events."""
    
    events: List[EventRead] = Field(..., description="List of events")
    total: int = Field(..., description="Total number of events")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of events per page")
    
    class Config:
        from_attributes = True 