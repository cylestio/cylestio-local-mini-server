"""
ModelRequestExtractor module.

This module provides an extractor for model_request events,
which extracts model information, framework details, and prompt data.
"""

from typing import Dict, Any, Optional
import logging
from datetime import datetime

from app.business_logic.extractors.base import BaseExtractor, extractor_registry
from app.models.framework_details import FrameworkDetails

# Set up logging
logger = logging.getLogger(__name__)


class ModelRequestExtractor(BaseExtractor):
    """Extractor for model_request events.
    
    Extracts model information, framework details, and prompt data
    from model_request events.
    """
    
    def can_process(self, event) -> bool:
        """Determine if this extractor can process the given event.
        
        Args:
            event: The event to check
            
        Returns:
            True if this is a model_request event, False otherwise
        """
        return event.event_type == "model_request"
    
    async def process(self, event, db_session) -> None:
        """Process the event and extract data.
        
        Args:
            event: The event to process
            db_session: Database session for persistence
        """
        if not event.data:
            logger.warning(f"No data in model_request event {event.id}")
            return
        
        # Extract framework details
        await self._extract_framework_details(event, db_session)
    
    async def _extract_framework_details(self, event, db_session) -> Optional[FrameworkDetails]:
        """Extract framework details from the event.
        
        Args:
            event: The event to extract from
            db_session: Database session for persistence
            
        Returns:
            The created FrameworkDetails object, or None if no framework data
        """
        try:
            data = event.data
            
            # Get framework information from data or from specialized framework field
            framework = data.get("framework", {})
            if not framework and "framework" in data:
                # Handle case where framework is a string
                if isinstance(data["framework"], str):
                    framework = {"name": data["framework"]}
                elif isinstance(data["framework"], dict):
                    framework = data["framework"]
            
            # If still no framework info, try common patterns
            if not framework:
                if "llm_type" in data:
                    # Construct framework info from llm_type
                    framework = {
                        "name": data.get("llm_type", "unknown"),
                        "version": data.get("framework_version")
                    }
                elif "run_id" in data and "framework_version" in data:
                    # Likely a langchain event
                    framework = {
                        "name": "langchain",
                        "version": data.get("framework_version")
                    }
            
            # Get framework details
            framework_name = None
            if isinstance(framework, dict):
                framework_name = framework.get("name")
            else:
                framework_name = str(framework) if framework else None
                
            if not framework_name:
                return None
            
            # Get version information from multiple possible locations
            framework_version = None
            if isinstance(framework, dict) and "version" in framework:
                framework_version = framework.get("version")
            if not framework_version and "framework_version" in data:
                framework_version = data.get("framework_version")
            if not framework_version and "version" in data:
                framework_version = data.get("version")
            
            # Format None values properly
            if framework_version == "None" or framework_version is None:
                framework_version = "unknown"
            
            # Get component information
            components = {}
            if isinstance(framework, dict) and "components" in framework:
                components = framework.get("components", {})
            elif "components" in data:
                components = data.get("components", {})
            
            # Determine the most specific component type
            component_name = None
            component_type = None
            
            if components:
                # Try to find non-empty component
                for comp_type, comp_val in components.items():
                    if comp_val and comp_val != "None":
                        component_type = comp_type
                        component_name = comp_val
                        break
            
            # If no component found in components, try direct fields
            if not component_name:
                if "llm_type" in data:
                    component_name = data.get("llm_type")
                    component_type = "llm_type"
                elif "model" in data and isinstance(data["model"], dict) and "name" in data["model"]:
                    component_name = data["model"]["name"]
                    component_type = "model"
            
            # Create FrameworkDetails object
            framework_details = FrameworkDetails(
                event_id=event.id,
                name=framework_name,
                version=framework_version,
                component=component_name,
                chain_type=component_type if component_type == "chain_type" else None,
                llm_type=component_type if component_type == "llm_type" else None,
                tool_type=component_type if component_type == "tool_type" else None,
                model_name=component_name if component_type == "model" else None
            )
            
            # Add to session
            db_session.add(framework_details)
            logger.info(f"Extracted framework details for event {event.id}: {framework_name} {framework_version}")
            
            return framework_details
        except Exception as e:
            logger.error(f"Error extracting framework details for event {event.id}: {str(e)}")
            return None


# Register the extractor
extractor_registry.register(ModelRequestExtractor()) 