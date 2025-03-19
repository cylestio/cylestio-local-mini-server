"""
Base classes for metric calculations.

This module provides abstract base classes for all metric calculators,
ensuring consistent interfaces and behavior.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from app.models.event import Event


class BaseMetricCalculator(ABC):
    """Base class for all metric calculators.
    
    All metric calculators should inherit from this class and implement
    the calculate method.
    """
    
    def __init__(self):
        self.name = self.__class__.__name__
    
    @abstractmethod
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """Calculate metrics based on events within the given parameters.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            **kwargs: Additional parameters specific to the metric calculator
            
        Returns:
            Dict containing calculated metrics
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


class MetricRegistry:
    """Registry for all metric calculators.
    
    This class maintains a registry of metric calculators and provides
    methods to register, unregister, and run calculators.
    """
    
    def __init__(self):
        self.calculators = {}
    
    def register(self, calculator: BaseMetricCalculator) -> None:
        """Register a metric calculator.
        
        Args:
            calculator: The metric calculator to register
        """
        self.calculators[calculator.name] = calculator
    
    def unregister(self, calculator_name: str) -> None:
        """Unregister a metric calculator.
        
        Args:
            calculator_name: The name of the calculator to unregister
        """
        if calculator_name in self.calculators:
            del self.calculators[calculator_name]
    
    def run_all(self, db: Session, start_time: Optional[datetime] = None,
               end_time: Optional[datetime] = None,
               agent_id: Optional[str] = None,
               session_id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Run all registered metric calculators.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict mapping calculator names to their results
        """
        results = {}
        for name, calculator in self.calculators.items():
            results[name] = calculator.calculate(
                db=db,
                start_time=start_time,
                end_time=end_time,
                agent_id=agent_id,
                session_id=session_id
            )
        return results
    
    def run_selected(self, calculator_names: List[str], db: Session,
                   start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None,
                   agent_id: Optional[str] = None,
                   session_id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Run selected metric calculators.
        
        Args:
            calculator_names: List of calculator names to run
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict mapping calculator names to their results
        """
        results = {}
        for name in calculator_names:
            if name in self.calculators:
                results[name] = self.calculators[name].calculate(
                    db=db,
                    start_time=start_time,
                    end_time=end_time,
                    agent_id=agent_id,
                    session_id=session_id
                )
        return results


# Create a global registry instance
metric_registry = MetricRegistry() 