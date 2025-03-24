"""
CommonExtractor module.

This module extracts common fields that are present in most event types.
"""

import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.event import Event
from app.models.agent import Agent
from app.models.session import Session as SessionModel
from app.business_logic.extractors.base import BaseExtractor

# Set up logging
logger = logging.getLogger(__name__)


class CommonExtractor(BaseExtractor):
    """Extractor for common fields across event types.
    
    Handles agent and session information that appears in most events.
    """
    
    def can_process(self, event) -> bool:
        """All events can be processed by this extractor.
        
        Args:
            event: The event to check
            
        Returns:
            Always True, as this extractor handles common fields
        """
        return True
    
    async def process(self, event, db_session) -> None:
        """Extract common information from the event.
        
        Args:
            event: The event to process
            db_session: Database session for persistence
        """
        # Extract and process agent information
        await self._process_agent_info(event, db_session)
        
        # Extract and process session information
        if event.session_id:
            await self._process_session_info(event, db_session)
        
        # Extract caller information if present
        if event.data and "caller" in event.data:
            self._extract_caller_info(event)
    
    async def _process_agent_info(self, event, db_session) -> None:
        """Process agent information from the event.
        
        Args:
            event: The event to process
            db_session: Database session for persistence
        """
        # Check if agent exists, create if not
        result = await db_session.execute(
            select(Agent).filter(Agent.agent_id == event.agent_id)
        )
        agent = result.scalars().first()
        
        if not agent:
            # Create new agent
            agent = Agent(
                agent_id=event.agent_id,
                first_seen=event.timestamp,
                last_seen=event.timestamp
            )
            
            # Try to extract LLM provider if available
            if event.event_type == "monitor_init" and event.data and "llm_provider" in event.data:
                agent.llm_provider = event.data["llm_provider"]
            
            db_session.add(agent)
        else:
            # Update last_seen timestamp
            agent.last_seen = event.timestamp
    
    async def _process_session_info(self, event, db_session) -> None:
        """Process session information from the event.
        
        Args:
            event: The event to process
            db_session: Database session for persistence
        """
        # Check if session exists, create if not
        result = await db_session.execute(
            select(SessionModel).filter(
                SessionModel.session_id == event.session_id
            )
        )
        session = result.scalars().first()
        
        if not session:
            # Create new session
            session = SessionModel(
                session_id=event.session_id,
                agent_id=event.agent_id,
                start_time=event.timestamp
            )
            db_session.add(session)
        
        # Update total events
        if session.total_events is None:
            session.total_events = 1  # Initialize to 1 (first event)
        else:
            session.total_events += 1
    
    def _extract_caller_info(self, event) -> None:
        """Extract caller information from the event data.
        
        Args:
            event: The event to process
        """
        caller_data = event.data.get("caller", {})
        
        if caller_data:
            event.caller_file = caller_data.get("file")
            event.caller_line = caller_data.get("line")
            event.caller_function = caller_data.get("function") 