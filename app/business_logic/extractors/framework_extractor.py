"""
Framework extractor module.

This module provides the extractor for framework information,
particularly for framework_patch events.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, Union

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.business_logic.extractors.base import BaseExtractor, extractor_registry
from app.models.framework_details import FrameworkDetails

# Set up logging
logger = logging.getLogger(__name__)


class FrameworkExtractor(BaseExtractor):
    """Extractor for framework information.
    
    This extractor processes events containing framework information,
    with a focus on framework_patch events that indicate framework integrations
    and modifications.
    """
    
    def can_process(self, event) -> bool:
        """Determine if this extractor can process the given event.
        
        Args:
            event: The event to check
            
        Returns:
            True if this event contains framework information
        """
        # Check if it's a framework_patch event
        if event.event_type == "framework_patch":
            return True
            
        # Check if the event has framework data
        if hasattr(event, 'data') and event.data:
            if 'framework' in event.data:
                return True
                
            # Check for framework data in components
            if 'components' in event.data:
                return True
                
        return False
    
    async def process(self, event, db_session) -> None:
        """Process the event and extract framework details.
        
        Args:
            event: The event to process
            db_session: Database session for persistence
        """
        try:
            # Extract framework details from the event
            framework_details = await self._extract_framework_details(event, db_session)
            
            if framework_details:
                # Add to session
                db_session.add(framework_details)
                logger.info(f"Extracted framework details for event {event.id}: {framework_details.name} {framework_details.version}")
                
        except Exception as e:
            # Log the error but allow processing to continue
            logger.error(f"Error extracting framework details for event {event.id}: {str(e)}")
    
    async def _extract_framework_details(self, event, db_session) -> Optional[FrameworkDetails]:
        """Extract framework details from the event.
        
        Args:
            event: The event to extract framework details from
            db_session: Database session for persistence
            
        Returns:
            FrameworkDetails model instance or None if no framework details found
        """
        try:
            # No need to check for existing framework details - event processor guarantees
            # this extractor runs exactly once per event
            
            data = event.data
            framework_name = "unknown"
            framework_version = "unknown"
            component_name = None
            component_type = None
            components_json = {}
            method_name = None
            
            # Extract framework details from data
            if 'framework' in data:
                if isinstance(data['framework'], dict):
                    framework = data['framework']
                    framework_name = framework.get('name', framework_name)
                    framework_version = framework.get('version', framework_version)
                    
                    # Extract component information
                    if 'component' in framework:
                        component_name = framework.get('component')
                        component_type = "framework_component"
                    
                    # Extract detailed components if available
                    if 'components' in framework and isinstance(framework['components'], dict):
                        components_json = framework['components']
                else:
                    framework_name = str(data['framework'])
            
            # Framework version may be in a separate field
            if 'version' in data and not framework_version:
                framework_version = str(data['version'])
            
            # For framework_patch events, extract method information
            if event.event_type == "framework_patch" and 'method' in data:
                method_name = data.get('method')
                
                # If no component name but there is a method, use it to infer component
                if not component_name and method_name:
                    # Extract class name from method (e.g., "ChatAnthropic._generate" -> "ChatAnthropic")
                    if '.' in method_name:
                        component_name = method_name.split('.')[0]
                        component_type = "patched_class"
            
            # Check components field for additional framework info
            if 'components' in data and isinstance(data['components'], dict):
                components = data['components']
                components_json = components
                
                # Extract additional component information
                if not component_name:
                    if 'chain_type' in components and components['chain_type'] != "None":
                        component_name = components['chain_type']
                        component_type = "chain_type"
                    elif 'llm_type' in components and components['llm_type'] != "None":
                        component_name = components['llm_type']
                        component_type = "llm_type"
                    elif 'tool_type' in components and components['tool_type'] != "None":
                        component_name = components['tool_type']
                        component_type = "tool_type"
            
            # Create a new framework details instance with the correct field names
            return FrameworkDetails(
                event_id=event.id,
                name=framework_name,
                version=framework_version,
                component=component_name,
                chain_type=component_type if component_type == "chain_type" else None,
                llm_type=component_type if component_type == "llm_type" else None,
                tool_type=component_type if component_type == "tool_type" else None,
                model_name=None  # Can be extracted from other events if needed
            )
        except Exception as e:
            logger.error(f"Error in _extract_framework_details for event {event.id}: {str(e)}")
            return None


# Register the extractor
extractor_registry.register(FrameworkExtractor())
extractor_registry.register_for_event_type("framework_patch", FrameworkExtractor()) 