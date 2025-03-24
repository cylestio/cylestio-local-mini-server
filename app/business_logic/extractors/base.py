"""
Base module for event data extractors.

This module provides base classes and registry for extractors that normalize
complex nested JSON data from events into dedicated relational fields.
"""

from typing import Dict, Any, List, Type, Set, Optional, Callable, Union, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from abc import ABC, abstractmethod
import traceback
import json
from datetime import datetime

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
    async def process(self, event, db_session: AsyncSession) -> None:
        """Process the event and extract data.
        
        Args:
            event: The event to process
            db_session: Database session for persistence
        """
        pass
    
    def safe_extract(self, data: Dict[str, Any], path: Union[str, List[str]], 
                     default: Any = None) -> Any:
        """Safely extract a value from a nested dictionary using a path.
        
        Args:
            data: The data dictionary to extract from
            path: A dot-notation string or list of keys representing the path to the value
            default: Default value to return if the path doesn't exist
            
        Returns:
            The extracted value or the default if not found
        """
        if not data:
            return default
            
        if isinstance(path, str):
            path = path.split('.')
            
        current = data
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
                
        return current
    
    def multi_path_extract(self, data: Dict[str, Any], paths: List[Union[str, List[str]]], 
                          default: Any = None) -> Any:
        """Extract a value from multiple possible paths in a nested dictionary.
        
        Tries each path in order until a non-default value is found.
        
        Args:
            data: The data dictionary to extract from
            paths: List of paths to try (dot-notation strings or lists of keys)
            default: Default value to return if none of the paths exist
            
        Returns:
            The first extracted non-default value or the default if none found
        """
        for path in paths:
            value = self.safe_extract(data, path, default)
            if value != default:
                return value
                
        return default
    
    def convert_value(self, value: Any, target_type: Type, default: Any = None) -> Any:
        """Convert a value to the target type, with error handling.
        
        Args:
            value: The value to convert
            target_type: The type to convert to
            default: Default value to return if conversion fails
            
        Returns:
            The converted value or the default if conversion fails
        """
        if value is None:
            return default
            
        try:
            if target_type == bool and isinstance(value, str):
                return value.lower() in ('true', 'yes', '1', 'y')
                
            if target_type == datetime and isinstance(value, str):
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
                
            return target_type(value)
        except (ValueError, TypeError) as e:
            logger.debug(f"Error converting value '{value}' to {target_type.__name__}: {str(e)}")
            return default
    
    def extract_and_convert(self, data: Dict[str, Any], path: Union[str, List[str]], 
                           target_type: Type, default: Any = None) -> Any:
        """Extract a value from a nested dictionary and convert it to the target type.
        
        Args:
            data: The data dictionary to extract from
            path: Path to the value (dot-notation string or list of keys)
            target_type: The type to convert to
            default: Default value to return if extraction or conversion fails
            
        Returns:
            The extracted and converted value or the default if either step fails
        """
        value = self.safe_extract(data, path)
        return self.convert_value(value, target_type, default)
    
    def get_list_item(self, data_list: List[Any], index: int, default: Any = None) -> Any:
        """Safely get an item from a list by index.
        
        Args:
            data_list: The list to get the item from
            index: The index of the item to get
            default: Default value to return if the index is out of bounds
            
        Returns:
            The item at the specified index or the default if out of bounds
        """
        if not isinstance(data_list, list):
            return default
            
        try:
            return data_list[index]
        except IndexError:
            return default
    
    def extract_nested_structures(self, data: Dict[str, Any], path: Union[str, List[str]], 
                                 process_fn: Callable[[Any], Any]) -> Any:
        """Extract and process a nested structure from the data.
        
        Args:
            data: The data dictionary to extract from
            path: Path to the structure (dot-notation string or list of keys)
            process_fn: Function to process the extracted structure
            
        Returns:
            The processed structure or None if extraction fails
        """
        structure = self.safe_extract(data, path)
        if structure is None:
            return None
            
        try:
            return process_fn(structure)
        except Exception as e:
            logger.error(f"Error processing nested structure at {path}: {str(e)}")
            return None
    
    def safe_process(self, event, db_session: AsyncSession) -> Tuple[bool, Optional[Exception]]:
        """Safely process an event with error handling.
        
        Args:
            event: The event to process
            db_session: Database session for persistence
            
        Returns:
            Tuple of (success, exception)
        """
        try:
            self.process(event, db_session)
            return True, None
        except Exception as e:
            logger.error(f"Error in {self.get_name()} processing event {event.id}: {str(e)}")
            logger.debug(traceback.format_exc())
            return False, e


class ExtractorRegistry:
    """Registry for data extractors.
    
    Keeps track of all available extractors and provides
    methods to access them.
    """
    
    def __init__(self):
        """Initialize the registry."""
        self._extractors = []
        self._extractors_by_name = {}
        self._extractors_by_event_type = {}
    
    def register(self, extractor: BaseExtractor) -> None:
        """Register an extractor.
        
        Args:
            extractor: The extractor to register
        """
        self._extractors.append(extractor)
        self._extractors_by_name[extractor.get_name()] = extractor
        logger.info(f"Registered extractor: {extractor.get_name()}")
    
    def register_for_event_type(self, event_type: str, extractor: BaseExtractor) -> None:
        """Register an extractor specifically for an event type.
        
        Args:
            event_type: The event type to register for
            extractor: The extractor to register
        """
        if event_type not in self._extractors_by_event_type:
            self._extractors_by_event_type[event_type] = []
            
        self._extractors_by_event_type[event_type].append(extractor)
        logger.info(f"Registered extractor {extractor.get_name()} for event type {event_type}")
    
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
        # First try extractors specific to this event type
        event_type_extractors = self._extractors_by_event_type.get(event.event_type, [])
        
        # Also include extractors that explicitly say they can process this event
        generic_extractors = [ext for ext in self._extractors 
                             if ext not in event_type_extractors and ext.can_process(event)]
        
        return event_type_extractors + generic_extractors
    
    def get_extractor_by_name(self, name: str) -> Optional[BaseExtractor]:
        """Get an extractor by name.
        
        Args:
            name: The name of the extractor to get
            
        Returns:
            The extractor with the given name, or None if not found
        """
        return self._extractors_by_name.get(name)


# Create a global extractor registry
extractor_registry = ExtractorRegistry() 