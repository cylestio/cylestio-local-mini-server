"""
Example extractor module.

This module provides an example extractor that demonstrates the features
of the extraction framework. It handles extracting user data from events.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from app.business_logic.extractors.base import BaseExtractor
from app.business_logic.extractors.utils import (
    extract_schema_fields,
    normalize_string,
    extract_datetime
)
from app.models.event import Event
from sqlalchemy.ext.asyncio import AsyncSession

# Set up logging
logger = logging.getLogger(__name__)


class UserActivityExtractor(BaseExtractor):
    """Example extractor for user activity data.
    
    Demonstrates how to use the extraction framework to handle
    different JSON structures and extract consistent data.
    """
    
    def can_process(self, event: Event) -> bool:
        """Determine if this extractor can process the given event.
        
        Processes events that contain user activity information.
        
        Args:
            event: The event to check
            
        Returns:
            True if this extractor can process the event, False otherwise
        """
        # Check if this is a user-related event type
        if not event.event_type or not event.data:
            return False
            
        user_event_types = ["user_login", "user_action", "user_logout", "user_error"]
        
        # Process specific event types
        if event.event_type in user_event_types:
            return True
            
        # Also process any event with user data
        if self._has_user_data(event.data):
            return True
            
        return False
    
    async def process(self, event: Event, db_session: AsyncSession) -> None:
        """Process the event and extract user activity data.
        
        Args:
            event: The event to process
            db_session: Database session for persistence
        """
        logger.info(f"Processing user activity in event {event.id}")
        
        try:
            # Extract user information using multiple possible paths
            user_data = self._extract_user_data(event.data)
            if not user_data or not user_data.get("user_id"):
                logger.warning(f"No valid user data found in event {event.id}")
                return
                
            # Extract activity timestamp
            activity_time = self._extract_activity_timestamp(event)
            
            # Extract activity type and details
            activity_type = self._extract_activity_type(event)
            details = self._extract_activity_details(event.data)
            
            # Process user activity
            await self._process_user_activity(
                event.id,
                user_data,
                activity_time,
                activity_type,
                details,
                db_session
            )
            
        except Exception as e:
            logger.error(f"Error processing user activity in event {event.id}: {str(e)}")
    
    def _has_user_data(self, data: Dict[str, Any]) -> bool:
        """Check if the data contains user information.
        
        Args:
            data: The data to check
            
        Returns:
            True if user data is present, False otherwise
        """
        user_paths = [
            "user.id",
            "user_id",
            "userId",
            "account.user.id",
            "user_info.id",
            "auth.user_id"
        ]
        
        for path in user_paths:
            if self.safe_extract(data, path):
                return True
                
        return False
    
    def _extract_user_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract user data from the event data.
        
        Handles multiple possible JSON structures for user data.
        
        Args:
            data: The event data
            
        Returns:
            Dictionary with normalized user data
        """
        # Define schema mapping for user fields
        schema_mapping = {
            "user_id": ["user.id", "user_id", "userId", "account.user.id", "user_info.id", "auth.user_id"],
            "username": ["user.name", "user.username", "username", "user_info.name", "name"],
            "email": ["user.email", "email", "user_info.email", "account.email"],
            "role": ["user.role", "role", "user_role", "user_info.role", "auth.role"]
        }
        
        # Extract fields based on schema
        user_data = extract_schema_fields(data, schema_mapping)
        
        # Normalize extracted values
        if "username" in user_data and isinstance(user_data["username"], str):
            user_data["username"] = normalize_string(user_data["username"])
            
        if "email" in user_data and isinstance(user_data["email"], str):
            user_data["email"] = user_data["email"].lower().strip()
            
        if "role" in user_data and isinstance(user_data["role"], str):
            user_data["role"] = normalize_string(user_data["role"])
        
        return user_data
    
    def _extract_activity_timestamp(self, event: Event) -> datetime:
        """Extract the activity timestamp from the event.
        
        Tries multiple possible locations for the timestamp.
        
        Args:
            event: The event
            
        Returns:
            The activity timestamp
        """
        # First try to get from event data
        timestamp_paths = [
            "timestamp",
            "time",
            "activity.time",
            "metadata.timestamp",
            "created_at"
        ]
        
        for path in timestamp_paths:
            ts_value = self.safe_extract(event.data, path)
            if ts_value:
                parsed_ts = extract_datetime(ts_value)
                if parsed_ts:
                    return parsed_ts
        
        # Fall back to event timestamp
        return event.timestamp
    
    def _extract_activity_type(self, event: Event) -> str:
        """Extract the activity type from the event.
        
        Args:
            event: The event
            
        Returns:
            The activity type
        """
        # Try getting from event data
        activity_paths = [
            "activity.type",
            "action",
            "activity",
            "event_subtype",
            "type"
        ]
        
        for path in activity_paths:
            activity = self.safe_extract(event.data, path)
            if activity:
                return normalize_string(str(activity))
        
        # Fall back to event type
        if event.event_type.startswith("user_"):
            # Remove "user_" prefix if present
            return event.event_type[5:]
            
        return event.event_type
    
    def _extract_activity_details(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract activity details from the event data.
        
        Args:
            data: The event data
            
        Returns:
            Dictionary with activity details
        """
        # Look for details in common locations
        details_paths = [
            "details",
            "activity.details",
            "metadata",
            "action_details",
            "context"
        ]
        
        for path in details_paths:
            details = self.safe_extract(data, path)
            if isinstance(details, dict) and details:
                return details
        
        # If no structured details found, collect all data not related to user info
        result = {}
        user_keys = ["user", "user_id", "userId", "username", "email", "role", "user_info"]
        
        for key, value in data.items():
            if key not in user_keys and key != "timestamp":
                result[key] = value
                
        return result
    
    async def _process_user_activity(
        self,
        event_id: str,
        user_data: Dict[str, Any],
        activity_time: datetime,
        activity_type: str,
        details: Dict[str, Any],
        db_session: AsyncSession
    ) -> None:
        """Process the extracted user activity data.
        
        This is where you would create or update database records,
        perform calculations, etc.
        
        Args:
            event_id: The event ID
            user_data: The user data
            activity_time: The activity timestamp
            activity_type: The activity type
            details: The activity details
            db_session: Database session for persistence
        """
        # This is a placeholder for the actual processing logic
        # In a real implementation, you would create or update models
        # and save them to the database
        
        logger.info(
            f"Processed user activity: event_id={event_id}, "
            f"user_id={user_data.get('user_id')}, "
            f"activity={activity_type}, "
            f"time={activity_time.isoformat()}"
        )
        
        # Example of how you might save to a database model
        # user_activity = UserActivity(
        #     event_id=event_id,
        #     user_id=user_data["user_id"],
        #     username=user_data.get("username"),
        #     activity_type=activity_type,
        #     activity_time=activity_time,
        #     details=details
        # )
        # db_session.add(user_activity)
        # await db_session.commit() 