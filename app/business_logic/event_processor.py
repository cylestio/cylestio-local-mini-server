"""
Event processor module.

This module provides the EventProcessor class that coordinates
the processing of events through extractors.
"""

from typing import List, Optional
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models.event import Event
from app.business_logic.extractors.base import extractor_registry, BaseExtractor

# Set up logging
logger = logging.getLogger(__name__)


class EventProcessor:
    """Coordinates the extraction of data from event JSON."""
    
    def __init__(self, extractors=None):
        """Initialize the event processor.
        
        Args:
            extractors: Optional list of extractors to use instead of the registry
        """
        self.extractors = extractors or extractor_registry.get_all_extractors()
        logger.info(f"Initialized EventProcessor with {len(self.extractors)} extractors")
    
    async def process_event(self, event: Event, db_session: AsyncSession) -> Event:
        """Process a single event through extractors exactly once.
        
        Args:
            event: The event to process
            db_session: Database session for persistence
            
        Returns:
            The processed event or None if processing failed
        """
        if not event:
            logger.warning("Received empty event to process")
            return None
        
        # Check if already processed to ensure idempotency
        if event.is_processed:
            logger.info(f"Event {event.id} already marked as processed, skipping")
            return event
        
        logger.info(f"Processing event {event.id} of type {event.event_type}")
        
        # Find applicable extractors for this event by checking can_process for each
        applicable_extractors = [ext for ext in self.extractors if ext.can_process(event)]
        logger.info(f"Found {len(applicable_extractors)} applicable extractors for event {event.id}")
        
        # Process ALL extractors in a SINGLE transaction
        try:
            # Apply each extractor
            for extractor in applicable_extractors:
                logger.debug(f"Applying extractor {extractor.get_name()} to event {event.id}")
                await extractor.process(event, db_session)
            
            # Mark event as processed ONLY after all extractors run
            event.is_processed = True
            await db_session.commit()
            logger.info(f"Successfully processed event {event.id}")
            return event
            
        except Exception as e:
            # If ANY extractor fails, roll back the ENTIRE transaction
            logger.error(f"Error processing event {event.id}: {str(e)}")
            await db_session.rollback()
            return None
    
    async def process_events(self, events: List[Event], db_session: AsyncSession) -> List[Event]:
        """Process multiple events sequentially.
        
        Each event is processed in its own transaction to isolate failures.
        
        Args:
            events: The events to process
            db_session: Database session for persistence
            
        Returns:
            The list of successfully processed events
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