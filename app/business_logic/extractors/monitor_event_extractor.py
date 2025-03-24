"""
MonitorEventExtractor module.

This module extracts information from monitor_init and monitor_shutdown events.
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError

from app.models.session import Session
from app.business_logic.extractors.base import BaseExtractor, extractor_registry

# Set up logging
logger = logging.getLogger(__name__)


class MonitorEventExtractor(BaseExtractor):
    """Extractor for monitor initialization and shutdown events.
    
    Extracts information from monitor_init and monitor_shutdown events
    to track session lifecycle and configuration details.
    """
    
    def can_process(self, event) -> bool:
        """Determine if this extractor can process the given event.
        
        Args:
            event: The event to check
            
        Returns:
            True if this is a monitor event, False otherwise
        """
        return event.event_type in ["monitor_init", "monitor_shutdown"]
    
    async def process(self, event, db_session) -> None:
        """Process the event and extract data.
        
        Args:
            event: The event to process
            db_session: Database session for persistence
        """
        if not event.data:
            logger.warning(f"No data in monitor event {event.id}")
            return
        
        # For monitor_init events, create a new session
        if event.event_type == "monitor_init":
            await self._process_monitor_init(event, db_session)
        
        # For monitor_shutdown events, update the session
        elif event.event_type == "monitor_shutdown":
            await self._process_monitor_shutdown(event, db_session)
    
    async def _process_monitor_init(self, event, db_session) -> Optional[Session]:
        """Process monitor_init event data.
        
        Args:
            event: The monitor_init event
            db_session: Database session for persistence
            
        Returns:
            The created Session object or None if error
        """
        try:
            data = event.data
            
            # Get configuration details from the event
            debug_level = data.get("debug_level", "INFO")
            api_endpoint = data.get("api_endpoint", "Not configured")
            log_file = data.get("log_file")
            llm_provider = data.get("llm_provider", "Unknown")
            development_mode = data.get("development_mode", False)
            
            # Generate the session ID
            session_id = event.session_id if event.session_id else f"monitor-{event.timestamp.isoformat()}"
            
            # Check if a session with this ID already exists
            result = await db_session.execute(
                select(Session).filter(Session.session_id == session_id)
            )
            existing_session = result.scalars().first()
            
            if existing_session:
                logger.info(f"Session {session_id} already exists, updating instead of creating")
                # Update the existing session
                existing_session.session_metadata = {
                    "debug_level": debug_level,
                    "api_endpoint": api_endpoint,
                    "log_file": log_file,
                    "llm_provider": llm_provider,
                    "development_mode": development_mode
                }
                return existing_session
            
            # Create a new session record
            session = Session(
                session_id=session_id,
                agent_id=event.agent_id,
                start_time=event.timestamp,
                end_time=None,  # Will be set on shutdown
                session_metadata={
                    "debug_level": debug_level,
                    "api_endpoint": api_endpoint,
                    "log_file": log_file,
                    "llm_provider": llm_provider,
                    "development_mode": development_mode
                }
            )
            
            # Add to session
            db_session.add(session)
            logger.info(f"Created new session for agent {event.agent_id} from monitor_init event {event.id}")
            
            return session
        except IntegrityError as e:
            # Handle integrity errors (like duplicate session_id)
            logger.warning(f"Session integrity error for event {event.id}: {str(e)}")
            await db_session.rollback()
            return None
        except Exception as e:
            logger.error(f"Error processing monitor_init event {event.id}: {str(e)}")
            return None
    
    async def _process_monitor_shutdown(self, event, db_session) -> Optional[Session]:
        """Process monitor_shutdown event data.
        
        Args:
            event: The monitor_shutdown event
            db_session: Database session for persistence
            
        Returns:
            The updated Session object or None if error
        """
        try:
            # Find the most recent session for this agent where end_time is null
            result = await db_session.execute(
                select(Session).filter(
                    Session.agent_id == event.agent_id,
                    Session.end_time == None
                ).order_by(Session.start_time.desc())
            )
            session = result.scalars().first()
            
            if not session:
                # Try to find any session for this agent, regardless of end_time
                result = await db_session.execute(
                    select(Session).filter(
                        Session.agent_id == event.agent_id
                    ).order_by(Session.start_time.desc())
                )
                session = result.scalars().first()
                
                if not session:
                    logger.warning(f"No session found for agent {event.agent_id} for shutdown event {event.id}. Creating a new session.")
                    # Create a new session if none exists
                    session = Session(
                        session_id=f"{event.agent_id}-{event.timestamp.strftime('%Y%m%d%H%M%S')}",
                        agent_id=event.agent_id,
                        start_time=event.timestamp,
                        end_time=event.timestamp,
                        session_metadata={
                            "auto_created": True,
                            "reason": "Missing session for shutdown event",
                            "event_id": event.id
                        }
                    )
                    db_session.add(session)
                    return session
                else:
                    logger.info(f"Found closed session for agent {event.agent_id}, updating end time")
            
            # Update the session with end time
            session.end_time = event.timestamp
            
            logger.info(f"Updated session for agent {event.agent_id} with shutdown event {event.id}")
            
            return session
        except Exception as e:
            logger.error(f"Error processing monitor_shutdown event {event.id}: {str(e)}")
            return None


# Register the extractor
extractor_registry.register(MonitorEventExtractor()) 