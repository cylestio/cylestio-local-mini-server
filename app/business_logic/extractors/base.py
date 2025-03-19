"""
Base module for event data extractors.

This module provides base classes and registry for extractors that normalize
complex nested JSON data from events into dedicated relational fields.
"""

from typing import Dict, Any, List, Type, Set, Optional, Callable
from sqlalchemy.orm import Session
import logging
from abc import ABC, abstractmethod

# Set up logging
logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """Base class for data extractors.
    
    Extractors are responsible for parsing event data and extracting
    specific information into normalized relational models.
    """
    
    def get_name(self) -> str:
        """Get the name of the extractor.
        
        Returns the class name by default, can be overridden for custom names.
        """
        return self.__class__.__name__
    
    @abstractmethod
    def can_process(self, event) -> bool:
        """Determine if this extractor can process the given event.
        
        Args:
            event: The event to check
            
        Returns:
            True if this extractor can process the event, False otherwise
        """
        pass
    
    @abstractmethod
    async def process(self, event, db_session) -> None:
        """Process the event and extract data.
        
        Args:
            event: The event to process
            db_session: Database session for persistence
        """
        pass


class ExtractorRegistry:
    """Registry for data extractors.
    
    Keeps track of all available extractors and provides
    methods to access them.
    """
    
    def __init__(self):
        """Initialize the registry."""
        self._extractors = []
    
    def register(self, extractor: BaseExtractor) -> None:
        """Register an extractor.
        
        Args:
            extractor: The extractor to register
        """
        self._extractors.append(extractor)
        logger.info(f"Registered extractor: {extractor.get_name()}")
    
    def get_all_extractors(self) -> List[BaseExtractor]:
        """Get all registered extractors.
        
        Returns:
            List of all registered extractors
        """
        return self._extractors.copy()
    
    def get_extractors_for_event(self, event) -> List[BaseExtractor]:
        """Get all extractors that can process the given event.
        
        Args:
            event: The event to get extractors for
            
        Returns:
            List of extractors that can process the event
        """
        return [ext for ext in self._extractors if ext.can_process(event)]


# Create a global extractor registry
extractor_registry = ExtractorRegistry() 