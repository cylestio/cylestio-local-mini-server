"""
Base classes for insight extraction.

This module provides abstract base classes for all insight extractors,
ensuring consistent interfaces and behavior.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from app.models.event import Event


class BaseInsightExtractor(ABC):
    """Base class for all insight extractors.
    
    All insight extractors should inherit from this class and implement
    the extract method.
    """
    
    def __init__(self):
        self.name = self.__class__.__name__
    
    @abstractmethod
    def extract(self, db: Session, start_time: Optional[datetime] = None, 
               end_time: Optional[datetime] = None, 
               agent_id: Optional[str] = None,
               session_id: Optional[str] = None,
               **kwargs) -> Dict[str, Any]:
        """Extract insights based on events within the given parameters.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            **kwargs: Additional parameters specific to the insight extractor
            
        Returns:
            Dict containing extracted insights
        """
        pass
    
    def get_filtered_events(self, db: Session, start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           agent_id: Optional[str] = None,
                           session_id: Optional[str] = None,
                           event_types: Optional[List[str]] = None,
                           channels: Optional[List[str]] = None,
                           levels: Optional[List[str]] = None) -> List[Event]:
        """Get filtered events based on parameters.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            event_types: Optional list of event types to filter
            channels: Optional list of channels to filter
            levels: Optional list of levels to filter
            
        Returns:
            List of filtered events
        """
        query = db.query(Event)
        
        if start_time:
            query = query.filter(Event.timestamp >= start_time)
        
        if end_time:
            query = query.filter(Event.timestamp <= end_time)
        
        if agent_id:
            query = query.filter(Event.agent_id == agent_id)
        
        if session_id:
            query = query.filter(Event.session_id == session_id)
        
        if event_types:
            query = query.filter(Event.event_type.in_(event_types))
        
        if channels:
            query = query.filter(Event.channel.in_(channels))
        
        if levels:
            query = query.filter(Event.level.in_(levels))
        
        return query.all()


class InsightRegistry:
    """Registry for all insight extractors.
    
    This class maintains a registry of insight extractors and provides
    methods to register, unregister, and run extractors.
    """
    
    def __init__(self):
        self.extractors = {}
    
    def register(self, extractor: BaseInsightExtractor) -> None:
        """Register an insight extractor.
        
        Args:
            extractor: The insight extractor to register
        """
        self.extractors[extractor.name] = extractor
    
    def unregister(self, extractor_name: str) -> None:
        """Unregister an insight extractor.
        
        Args:
            extractor_name: The name of the extractor to unregister
        """
        if extractor_name in self.extractors:
            del self.extractors[extractor_name]
    
    def run_all(self, db: Session, start_time: Optional[datetime] = None,
               end_time: Optional[datetime] = None,
               agent_id: Optional[str] = None,
               session_id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Run all registered insight extractors.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict mapping extractor names to their results
        """
        results = {}
        for name, extractor in self.extractors.items():
            results[name] = extractor.extract(
                db=db,
                start_time=start_time,
                end_time=end_time,
                agent_id=agent_id,
                session_id=session_id
            )
        return results
    
    def run_selected(self, extractor_names: List[str], db: Session,
                   start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None,
                   agent_id: Optional[str] = None,
                   session_id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Run selected insight extractors.
        
        Args:
            extractor_names: List of extractor names to run
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict mapping extractor names to their results
        """
        results = {}
        for name in extractor_names:
            if name in self.extractors:
                results[name] = self.extractors[name].extract(
                    db=db,
                    start_time=start_time,
                    end_time=end_time,
                    agent_id=agent_id,
                    session_id=session_id
                )
        return results
    
    def get_extractor(self, name: str) -> Optional[BaseInsightExtractor]:
        """Get an extractor by name.
        
        Args:
            name: Name of the extractor to get
            
        Returns:
            The extractor if found, None otherwise
        """
        return self.extractors.get(name)
    
    def get_all_extractors(self) -> Dict[str, BaseInsightExtractor]:
        """Get all registered extractors.
        
        Returns:
            Dict mapping extractor names to extractors
        """
        return self.extractors.copy()
        
    def get_available_insights(self) -> List[str]:
        """Get names of all available insights.
        
        Returns:
            List of insight names
        """
        return list(self.extractors.keys())


# Create a global registry instance
insight_registry = InsightRegistry() 