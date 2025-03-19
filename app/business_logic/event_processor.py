"""
Event processor module.

This module provides the central EventProcessor class that coordinates
the processing of events through extractors and metric calculators.
"""

from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.business_logic.extractors.base import extractor_registry, BaseExtractor
from app.business_logic.base import metric_registry, insight_registry

# Set up logging
logger = logging.getLogger(__name__)


class EventProcessor:
    """Coordinates the processing of events through the business logic layer."""
    
    def __init__(self, extractors=None):
        """Initialize the event processor.
        
        Args:
            extractors: Optional list of extractors to use instead of the registry
        """
        self.extractors = extractors or extractor_registry.get_all_extractors()
        logger.info(f"Initialized EventProcessor with {len(self.extractors)} extractors")
    
    async def process_event(self, event: Event, db_session: AsyncSession) -> Event:
        """Process a single event through the business logic layer.
        
        Args:
            event: The event to process
            db_session: Database session for persistence
            
        Returns:
            The processed event
        """
        if not event:
            logger.warning("Received empty event to process")
            return None
        
        logger.info(f"Processing event {event.id} of type {event.event_type}")
        
        try:
            # Process through type-specific extractors
            applicable_extractors = [ext for ext in self.extractors if ext.can_process(event)]
            logger.info(f"Found {len(applicable_extractors)} applicable extractors for event {event.id}")
            
            for extractor in applicable_extractors:
                try:
                    logger.debug(f"Applying extractor {extractor.get_name()} to event {event.id}")
                    await extractor.process(event, db_session)
                except Exception as e:
                    # Log the error but continue with other extractors
                    logger.error(f"Error in extractor {extractor.get_name()} for event {event.id}: {str(e)}")
            
            # Mark event as processed
            event.is_processed = True
            await db_session.commit()
            
            return event
        except Exception as e:
            logger.error(f"Error processing event {event.id}: {str(e)}")
            await db_session.rollback()
            raise
    
    async def process_events(self, events: List[Event], db_session: AsyncSession) -> List[Event]:
        """Process multiple events through the business logic layer.
        
        Args:
            events: The events to process
            db_session: Database session for persistence
            
        Returns:
            The processed events
        """
        processed_events = []
        
        for event in events:
            try:
                processed_event = await self.process_event(event, db_session)
                if processed_event:
                    processed_events.append(processed_event)
            except Exception as e:
                logger.error(f"Error processing event batch: {str(e)}")
        
        return processed_events
    
    @classmethod
    async def get_extractors_for_event_type(cls, event_type: str) -> List[BaseExtractor]:
        """Get all extractors that can process events of the given type.
        
        Args:
            event_type: The event type to get extractors for
            
        Returns:
            List of extractors that can process the event type
        """
        mock_event = type('MockEvent', (), {'event_type': event_type})
        return extractor_registry.get_extractors_for_event(mock_event) 