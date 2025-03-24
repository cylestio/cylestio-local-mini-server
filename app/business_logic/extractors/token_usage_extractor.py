"""
TokenUsageExtractor module.

This module extracts token usage data from events that include LLM token information.
"""

import logging
import re
from typing import Dict, Any, Optional

from app.models.token_usage import TokenUsage
from app.business_logic.extractors.base import BaseExtractor
from sqlalchemy import select

# Set up logging
logger = logging.getLogger(__name__)


class TokenUsageExtractor(BaseExtractor):
    """Extractor for token usage data.
    
    Extracts token usage metrics from various event types, handling
    different JSON structures that contain token information.
    """
    
    def can_process(self, event) -> bool:
        """Check if this event contains token usage data.
        
        Args:
            event: The event to check
            
        Returns:
            True if this event type might contain token data
        """
        if not event.data:
            return False
            
        # Event types that typically contain token usage data
        token_event_types = {
            "model_response", 
            "LLM_call_finish"
        }
        
        return event.event_type in token_event_types
    
    async def process(self, event, db_session) -> None:
        """Extract token usage data from the event.
        
        Args:
            event: The event to process
            db_session: Database session for persistence
        """
        # Check if token usage already exists for this event
        result = await db_session.execute(
            select(TokenUsage).where(TokenUsage.event_id == event.id)
        )
        existing_token_usage = result.scalars().first()
        
        if existing_token_usage:
            logger.info(f"Token usage already exists for event {event.id}, skipping extraction")
            return
        
        token_usage = await self._extract_token_usage(event)
        
        if token_usage:
            db_session.add(token_usage)
    
    async def _extract_token_usage(self, event) -> Optional[TokenUsage]:
        """Extract token usage data from various event formats.
        
        Handles different JSON structures based on event type.
        
        Args:
            event: The event to extract from
            
        Returns:
            TokenUsage object or None if no token data found
        """
        try:
            # Get event data
            data = event.data
            
            # Base token usage fields
            input_tokens = 0
            output_tokens = 0
            total_tokens = 0
            cache_read_tokens = 0
            cache_creation_tokens = 0
            model = None
            
            if event.event_type == "model_response":
                # Extract from model_response format
                if "response" in data:
                    # First check for structured usage data
                    if "llm_output" in data["response"] and "usage" in data["response"]["llm_output"]:
                        usage_data = data["response"]["llm_output"]["usage"]
                        input_tokens = int(usage_data.get("input_tokens", 0))
                        output_tokens = int(usage_data.get("output_tokens", 0))
                        cache_read_tokens = int(usage_data.get("cache_read_input_tokens", 0))
                        cache_creation_tokens = int(usage_data.get("cache_creation_input_tokens", 0))
                        model = data["response"]["llm_output"].get("model", 
                               data["response"]["llm_output"].get("model_name"))
                    
                    # Try to extract from message's usage_metadata
                    elif "message" in data["response"]:
                        message = data["response"]["message"]
                        if isinstance(message, dict) and "usage_metadata" in message:
                            metadata = message["usage_metadata"]
                            input_tokens = int(metadata.get("input_tokens", 0))
                            output_tokens = int(metadata.get("output_tokens", 0))
                            total_tokens = int(metadata.get("total_tokens", 0))
                    
                    # Try to parse from text representation
                    elif "text" in data["response"]:
                        text = data["response"]["text"]
                        # Extract tokens using regex - handle tuple representation
                        input_match = re.search(r"'input_tokens':\s*(\d+)", text)
                        output_match = re.search(r"'output_tokens':\s*(\d+)", text)
                        
                        if input_match and output_match:
                            input_tokens = int(input_match.group(1))
                            output_tokens = int(output_match.group(1))
            
            elif event.event_type == "LLM_call_finish":
                # Extract from LLM_call_finish format
                if "response" in data and "usage" in data["response"]:
                    usage_data = data["response"]["usage"]
                    input_tokens = int(usage_data.get("input_tokens", 0))
                    output_tokens = int(usage_data.get("output_tokens", 0))
                    model = data["response"].get("model")
            
            # If we found token data, create the object
            if input_tokens > 0 or output_tokens > 0:
                # Calculate total tokens if not provided
                if total_tokens == 0:
                    total_tokens = input_tokens + output_tokens
                
                # Create and return the token usage object
                return TokenUsage(
                    event_id=event.id,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    cache_read_tokens=cache_read_tokens,
                    cache_creation_tokens=cache_creation_tokens,
                    model=model
                )
            
            return None
        
        except Exception as e:
            logger.error(f"Error extracting token usage from event {event.id}: {str(e)}")
            return None 