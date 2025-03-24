"""
ModelInfoExtractor module.

This module extracts information about language models from events.
"""

import logging
from typing import Dict, Any, Optional

from app.models.model_details import ModelDetails
from app.business_logic.extractors.base import BaseExtractor

# Set up logging
logger = logging.getLogger(__name__)


class ModelInfoExtractor(BaseExtractor):
    """Extractor for model and framework information.
    
    Extracts details about the language models and frameworks used,
    from various event types that include this information.
    """
    
    def can_process(self, event) -> bool:
        """Check if this event contains model info data.
        
        Args:
            event: The event to check
            
        Returns:
            True if this event type might contain model info
        """
        if not event.data:
            return False
        
        # Event types that typically contain model info
        model_event_types = {
            "model_request",
            "model_response",
            "framework_patch",
            "LLM_call_finish"
        }
        
        return event.event_type in model_event_types
    
    async def process(self, event, db_session) -> None:
        """Extract model information from the event.
        
        Args:
            event: The event to process
            db_session: Database session for persistence
        """
        model_details = await self._extract_model_details(event)
        
        if model_details:
            db_session.add(model_details)
    
    async def _extract_model_details(self, event) -> Optional[ModelDetails]:
        """Extract model details from various event formats.
        
        Handles different JSON structures based on event type.
        
        Args:
            event: The event to extract from
            
        Returns:
            ModelDetails object or None if no data found
        """
        try:
            # Get event data
            data = event.data
            
            # Base details
            model_name = None
            model_provider = None
            model_type = None
            model_version = None
            
            if event.event_type == "model_request":
                # Extract from model_request events
                if "model" in data:
                    model = data["model"]
                    model_name = model.get("name")
                    model_provider = model.get("provider")
                    model_type = model.get("type")
                else:
                    # Some events have direct llm_type
                    model_name = data.get("llm_type")
                
                # Components information
                if "components" in data:
                    components = data["components"]
                    model_name = model_name or components.get("llm_type")
            
            elif event.event_type == "model_response":
                # Extract from model_response events
                if "response" in data and "llm_output" in data["response"]:
                    llm_output = data["response"]["llm_output"]
                    model_name = llm_output.get("model", llm_output.get("model_name"))
            
            elif event.event_type == "LLM_call_finish":
                # Extract from LLM_call_finish events
                if "response" in data:
                    response = data["response"]
                    model_name = response.get("model")
            
            # If we found model data, create the object
            if model_name:
                return ModelDetails(
                    event_id=event.id,
                    model_name=model_name,
                    model_provider=model_provider,
                    model_type=model_type,
                    model_version=model_version
                )
            
            return None
        
        except Exception as e:
            logger.error(f"Error extracting model details from event {event.id}: {str(e)}")
            return None 