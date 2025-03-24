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
        """Process a single event through extractors.
        
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
        
        # Process each extractor in a separate transaction to isolate failures
        # Find applicable extractors for this event
        applicable_extractors = [ext for ext in self.extractors if ext.can_process(event)]
        logger.info(f"Found {len(applicable_extractors)} applicable extractors for event {event.id}")
        
        # Apply each extractor
        for extractor in applicable_extractors:
            try:
                logger.debug(f"Applying extractor {extractor.get_name()} to event {event.id}")
                await extractor.process(event, db_session)
                await db_session.flush()  # Flush changes but don't commit yet
            except IntegrityError as e:
                # Handle integrity errors like duplicate constraint violations
                logger.warning(f"Integrity error in extractor {extractor.get_name()} for event {event.id}: {str(e)}")
                await db_session.rollback()  # Roll back the transaction
            except Exception as e:
                # Log the error but continue with other extractors
                logger.error(f"Error in extractor {extractor.get_name()} for event {event.id}: {str(e)}")
                await db_session.rollback()  # Roll back the transaction
        
        try:
            # Mark event as processed
            event.is_processed = True
            await db_session.commit()
            return event
        except Exception as e:
            logger.error(f"Error marking event {event.id} as processed: {str(e)}")
            await db_session.rollback()
            return None
    
    async def process_events(self, events: List[Event], db_session: AsyncSession) -> List[Event]:
        """Process multiple events through extractors.
        
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