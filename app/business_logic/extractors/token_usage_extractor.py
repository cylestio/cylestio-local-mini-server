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
            "LLM_call_finish",
            "model_request",
            "LLM_call_start",
            "conversation_response",
            "embedding_request",
            "embedding_response"
        }
        
        # Check if event type is in our known list
        if event.event_type in token_event_types:
            return True
            
        # For other event types, check if data has token usage fields
        data = event.data
        
        # Check for common token usage patterns in the data
        has_token_info = False
        
        # Check for usage field
        if "response" in data and isinstance(data["response"], dict):
            response = data["response"]
            if "usage" in response or "llm_output" in response:
                has_token_info = True
                
        # Check for token_usage field
        if "token_usage" in data:
            has_token_info = True
            
        # Check for message with usage metadata
        if "message" in data and isinstance(data["message"], dict) and "usage_metadata" in data["message"]:
            has_token_info = True
            
        return has_token_info
    
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
            logger.info(f"Added token usage for event {event.id}: {token_usage.input_tokens} in, {token_usage.output_tokens} out")
    
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
            
            # Extract model name first - might be in multiple places
            model = self._extract_model_name(data)
            
            if event.event_type == "model_response":
                # Extract from model_response format
                if "response" in data:
                    # First check for structured usage data in llm_output
                    if "llm_output" in data["response"] and "usage" in data["response"]["llm_output"]:
                        usage_data = data["response"]["llm_output"]["usage"]
                        input_tokens = int(usage_data.get("input_tokens", 0))
                        output_tokens = int(usage_data.get("output_tokens", 0))
                        cache_read_tokens = int(usage_data.get("cache_read_input_tokens", 0))
                        cache_creation_tokens = int(usage_data.get("cache_creation_input_tokens", 0))
                        if not model:
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
                            
                            # Check for input token details if present
                            if "input_token_details" in metadata:
                                details = metadata["input_token_details"]
                                cache_read_tokens = int(details.get("cache_read", 0))
                                cache_creation_tokens = int(details.get("cache_creation", 0))
                    
                    # Try to extract directly from response if it has usage field
                    elif "usage" in data["response"]:
                        usage_data = data["response"]["usage"]
                        input_tokens = int(usage_data.get("input_tokens", 0))
                        output_tokens = int(usage_data.get("output_tokens", 0))
                        total_tokens = int(usage_data.get("total_tokens", 0))
                        cache_read_tokens = int(usage_data.get("cache_read_input_tokens", 0))
                        cache_creation_tokens = int(usage_data.get("cache_creation_input_tokens", 0))
                        if not model:
                            model = data["response"].get("model", data["response"].get("model_name"))
                    
                    # Try to parse from text representation
                    elif "text" in data["response"]:
                        text = data["response"]["text"]
                        # Extract tokens using regex - handle tuple representation or other formats
                        input_match = re.search(r"['\"]?input_tokens['\"]?\s*[=:]\s*(\d+)", text)
                        output_match = re.search(r"['\"]?output_tokens['\"]?\s*[=:]\s*(\d+)", text)
                        
                        if input_match and output_match:
                            input_tokens = int(input_match.group(1))
                            output_tokens = int(output_match.group(1))
                            
                            # Try to extract model name
                            if not model:
                                model_match = re.search(r"['\"]?model['\"]?\s*[=:]\s*['\"]?([^'\"]+)['\"]?", text)
                                if model_match:
                                    model = model_match.group(1)
            
            elif event.event_type == "LLM_call_finish":
                # Extract from LLM_call_finish format
                if "response" in data and "usage" in data["response"]:
                    usage_data = data["response"]["usage"]
                    input_tokens = int(usage_data.get("input_tokens", 
                        usage_data.get("prompt_tokens", 0)))
                    output_tokens = int(usage_data.get("output_tokens", 
                        usage_data.get("completion_tokens", 0)))
                    total_tokens = int(usage_data.get("total_tokens", 0))
                    cache_read_tokens = int(usage_data.get("cache_read_input_tokens", 0))
                    cache_creation_tokens = int(usage_data.get("cache_creation_input_tokens", 0))
                    if not model:
                        model = data["response"].get("model", data["response"].get("model_name"))
                
                # Handle direct token usage in data
                elif "token_usage" in data:
                    usage_data = data["token_usage"]
                    input_tokens = int(usage_data.get("input_tokens", 0))
                    output_tokens = int(usage_data.get("output_tokens", 0))
                    total_tokens = int(usage_data.get("total_tokens", 0))
                    if not model:
                        model = data.get("model")
            
            elif event.event_type in ["model_request", "LLM_call_start"]:
                # For request events, we might only have input tokens
                if "request" in data and "metadata" in data["request"]:
                    metadata = data["request"]["metadata"]
                    if "token_count" in metadata:
                        input_tokens = int(metadata.get("token_count", 0))
                    elif "input_tokens" in metadata:
                        input_tokens = int(metadata.get("input_tokens", 0))
                        
                # Check for estimated tokens field
                if "estimated_input_tokens" in data:
                    input_tokens = int(data.get("estimated_input_tokens", 0))
                
                # For conversation events
                if "conversation" in data and "metadata" in data["conversation"]:
                    metadata = data["conversation"]["metadata"]
                    input_tokens = int(metadata.get("input_tokens", 0))
                    
            elif "usage" in data:
                # Generic usage field extraction
                usage_data = data["usage"]
                input_tokens = int(usage_data.get("input_tokens", 
                    usage_data.get("prompt_tokens", 0)))
                output_tokens = int(usage_data.get("output_tokens", 
                    usage_data.get("completion_tokens", 0)))
                total_tokens = int(usage_data.get("total_tokens", 0))
            
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
            
    def _extract_model_name(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract model name from various locations in the data.
        
        Args:
            data: Event data dictionary
            
        Returns:
            Model name if found, None otherwise
        """
        # Check common locations for model name
        if "model" in data:
            if isinstance(data["model"], dict) and "name" in data["model"]:
                return data["model"]["name"]
            elif isinstance(data["model"], str):
                return data["model"]
        
        # Check in response data
        if "response" in data and isinstance(data["response"], dict):
            response = data["response"]
            
            if "model" in response:
                return response["model"]
                
            if "model_name" in response:
                return response["model_name"]
                
            if "llm_output" in response and isinstance(response["llm_output"], dict):
                llm_output = response["llm_output"]
                if "model" in llm_output:
                    return llm_output["model"]
                if "model_name" in llm_output:
                    return llm_output["model_name"]
        
        # Check in request data
        if "request" in data and isinstance(data["request"], dict):
            request = data["request"]
            
            if "model" in request:
                return request["model"]
                
            if "model_name" in request:
                return request["model_name"]
                
            if "metadata" in request and isinstance(request["metadata"], dict):
                metadata = request["metadata"]
                if "model" in metadata:
                    return metadata["model"]
                if "model_name" in metadata:
                    return metadata["model_name"]
        
        # Check in config
        if "config" in data and isinstance(data["config"], dict):
            config = data["config"]
            if "model" in config:
                return config["model"]
            if "model_name" in config:
                return config["model_name"]
        
        return None 