"""
Metrics API utility module.

This module provides shared utilities and parameter handling for metrics endpoints.
"""

from fastapi import Query
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel

class TimeRangeParams:
    """
    Time range and filtering parameters for metrics endpoints.
    
    Provides consistent parameter handling for:
    - Time range (start_time, end_time)
    - Agent and session filtering
    """
    def __init__(
        self,
        start_time: Optional[str] = Query(None, description="Start time in ISO format"),
        end_time: Optional[str] = Query(None, description="End time in ISO format"),
        agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
        session_id: Optional[str] = Query(None, description="Filter by session ID"),
    ):
        # Convert ISO string to datetime object
        self.start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00')) if start_time else None
        self.end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00')) if end_time else None
        
        # If end_time not provided, use current time
        if not self.end_time:
            self.end_time = datetime.now()
            
        # If start_time not provided, default to 24 hours before end_time
        if not self.start_time:
            self.start_time = self.end_time - timedelta(days=1)
            
        self.agent_id = agent_id
        self.session_id = session_id
        
    def get_metadata(self) -> Dict[str, Any]:
        """Get time range parameters as metadata dictionary."""
        return {
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "agent_id": self.agent_id,
            "session_id": self.session_id
        }

def format_response(data: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format API response with consistent structure.
    
    Args:
        data: The metrics data to return
        metadata: Additional metadata about the request
        
    Returns:
        Formatted response dictionary with data and metadata sections
    """
    return {
        "data": data,
        "metadata": metadata
    } 