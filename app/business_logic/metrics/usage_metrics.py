"""
Usage Metrics module.

This module provides metric calculators for tracking usage patterns by framework, model, and agent.
Each calculator focuses on a specific usage metric for better modularity.
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta, UTC
import statistics
from collections import Counter, defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, desc

from app.business_logic.metrics.base import BaseMetricCalculator, metric_registry
from app.models.event import Event
from app.models.framework_details import FrameworkDetails
from app.models.model_details import ModelDetails


class FrameworkUsageCalculator(BaseMetricCalculator):
    """Calculator for framework usage metrics.
    
    Calculates metrics related to which frameworks are being used.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 top_n: int = 10,
                 **kwargs) -> Dict[str, Any]:
        """Calculate framework usage metrics.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            top_n: Number of top frameworks to return
            
        Returns:
            Dict containing framework usage metrics:
                - framework_distribution: Dict mapping framework name to usage count
                - top_frameworks: List of (framework_name, count) tuples for top frameworks
                - total_events: Total number of events analyzed
        """
        # Build base query
        query = db.query(
            FrameworkDetails.name,
            func.count(FrameworkDetails.id).label('count')
        ).join(Event)
        
        # Apply filters
        if start_time:
            query = query.filter(Event.timestamp >= start_time)
        
        if end_time:
            query = query.filter(Event.timestamp <= end_time)
        
        if agent_id:
            query = query.filter(Event.agent_id == agent_id)
        
        if session_id:
            query = query.filter(Event.session_id == session_id)
        
        # Group by framework and get counts
        query = query.group_by(FrameworkDetails.name).order_by(desc('count'))
        
        # Execute query
        framework_counts = query.all()
        
        # Format results
        framework_distribution = {name: count for name, count in framework_counts}
        top_frameworks = [(name, count) for name, count in framework_counts[:top_n]]
        total_events = sum(framework_distribution.values())
        
        return {
            "framework_distribution": framework_distribution,
            "top_frameworks": top_frameworks,
            "total_events": total_events
        }


class ModelUsageCalculator(BaseMetricCalculator):
    """Calculator for model usage metrics.
    
    Calculates metrics related to which models are being used.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 top_n: int = 10,
                 **kwargs) -> Dict[str, Any]:
        """Calculate model usage metrics.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            top_n: Number of top models to return
            
        Returns:
            Dict containing model usage metrics:
                - model_distribution: Dict mapping model name to usage count
                - top_models: List of (model_name, count) tuples for top models
                - total_events: Total number of events analyzed
        """
        # Build base query
        query = db.query(
            ModelDetails.model_name,
            func.count(ModelDetails.id).label('count')
        ).join(Event)
        
        # Apply filters
        if start_time:
            query = query.filter(Event.timestamp >= start_time)
        
        if end_time:
            query = query.filter(Event.timestamp <= end_time)
        
        if agent_id:
            query = query.filter(Event.agent_id == agent_id)
        
        if session_id:
            query = query.filter(Event.session_id == session_id)
        
        # Group by model and get counts
        query = query.group_by(ModelDetails.model_name).order_by(desc('count'))
        
        # Execute query
        model_counts = query.all()
        
        # Format results
        model_distribution = {name: count for name, count in model_counts}
        top_models = [(name, count) for name, count in model_counts[:top_n]]
        total_events = sum(model_distribution.values())
        
        return {
            "model_distribution": model_distribution,
            "top_models": top_models,
            "total_events": total_events
        }


class AgentUsageCalculator(BaseMetricCalculator):
    """Calculator for agent usage metrics.
    
    Calculates metrics related to which agents are being used.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 top_n: int = 10,
                 **kwargs) -> Dict[str, Any]:
        """Calculate agent usage metrics.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            top_n: Number of top agents to return
            
        Returns:
            Dict containing agent usage metrics:
                - agent_distribution: Dict mapping agent ID to event count
                - top_agents: List of (agent_id, count) tuples for top agents
                - total_events: Total number of events analyzed
        """
        # Build base query
        query = db.query(
            Event.agent_id,
            func.count(Event.id).label('count')
        )
        
        # Apply filters
        if start_time:
            query = query.filter(Event.timestamp >= start_time)
        
        if end_time:
            query = query.filter(Event.timestamp <= end_time)
        
        # Group by agent and get counts
        query = query.group_by(Event.agent_id).order_by(desc('count'))
        
        # Execute query
        agent_counts = query.all()
        
        # Format results
        agent_distribution = {agent_id: count for agent_id, count in agent_counts}
        top_agents = [(agent_id, count) for agent_id, count in agent_counts[:top_n]]
        total_events = sum(agent_distribution.values())
        
        return {
            "agent_distribution": agent_distribution,
            "top_agents": top_agents,
            "total_events": total_events
        }


class SessionCountCalculator(BaseMetricCalculator):
    """Calculator for session count metrics.
    
    Calculates metrics related to session activity.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """Calculate session count metrics.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            
        Returns:
            Dict containing session count metrics:
                - total_sessions: Total number of unique sessions
                - average_events_per_session: Average number of events per session
                - sessions_by_agent: Dict mapping agent ID to session count
        """
        # Build base query for sessions
        session_query = db.query(
            Event.session_id,
            Event.agent_id,
            func.count(Event.id).label('event_count')
        ).filter(Event.session_id.isnot(None))
        
        # Apply filters
        if start_time:
            session_query = session_query.filter(Event.timestamp >= start_time)
        
        if end_time:
            session_query = session_query.filter(Event.timestamp <= end_time)
        
        if agent_id:
            session_query = session_query.filter(Event.agent_id == agent_id)
        
        # Group by session and agent
        session_query = session_query.group_by(Event.session_id, Event.agent_id)
        
        # Execute query
        session_data = session_query.all()
        
        # Count sessions by agent
        sessions_by_agent = defaultdict(int)
        event_counts = []
        
        for session_id, agent_id, event_count in session_data:
            sessions_by_agent[agent_id] += 1
            event_counts.append(event_count)
        
        # Calculate metrics
        total_sessions = len(session_data)
        avg_events_per_session = statistics.mean(event_counts) if event_counts else 0
        
        return {
            "total_sessions": total_sessions,
            "average_events_per_session": avg_events_per_session,
            "sessions_by_agent": dict(sessions_by_agent)
        }


class EventTypeDistributionCalculator(BaseMetricCalculator):
    """Calculator for event type distribution metrics.
    
    Calculates metrics related to the distribution of event types.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 top_n: int = 10,
                 **kwargs) -> Dict[str, Any]:
        """Calculate event type distribution metrics.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            top_n: Number of top event types to return
            
        Returns:
            Dict containing event type distribution metrics:
                - event_type_distribution: Dict mapping event type to count
                - top_event_types: List of (event_type, count) tuples for top event types
                - total_events: Total number of events analyzed
        """
        # Build base query
        query = db.query(
            Event.event_type,
            func.count(Event.id).label('count')
        )
        
        # Apply filters
        if start_time:
            query = query.filter(Event.timestamp >= start_time)
        
        if end_time:
            query = query.filter(Event.timestamp <= end_time)
        
        if agent_id:
            query = query.filter(Event.agent_id == agent_id)
        
        if session_id:
            query = query.filter(Event.session_id == session_id)
        
        # Group by event type and get counts
        query = query.group_by(Event.event_type).order_by(desc('count'))
        
        # Execute query
        event_type_counts = query.all()
        
        # Format results
        event_type_distribution = {event_type: count for event_type, count in event_type_counts}
        top_event_types = [(event_type, count) for event_type, count in event_type_counts[:top_n]]
        total_events = sum(event_type_distribution.values())
        
        return {
            "event_type_distribution": event_type_distribution,
            "top_event_types": top_event_types,
            "total_events": total_events
        }


class ChannelDistributionCalculator(BaseMetricCalculator):
    """Calculator for channel distribution metrics.
    
    Calculates metrics related to the distribution of channels.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """Calculate channel distribution metrics.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict containing channel distribution metrics:
                - channel_distribution: Dict mapping channel to count
                - total_events: Total number of events analyzed
        """
        # Build base query
        query = db.query(
            Event.channel,
            func.count(Event.id).label('count')
        )
        
        # Apply filters
        if start_time:
            query = query.filter(Event.timestamp >= start_time)
        
        if end_time:
            query = query.filter(Event.timestamp <= end_time)
        
        if agent_id:
            query = query.filter(Event.agent_id == agent_id)
        
        if session_id:
            query = query.filter(Event.session_id == session_id)
        
        # Group by channel and get counts
        query = query.group_by(Event.channel).order_by(desc('count'))
        
        # Execute query
        channel_counts = query.all()
        
        # Format results
        channel_distribution = {channel: count for channel, count in channel_counts}
        total_events = sum(channel_distribution.values())
        
        return {
            "channel_distribution": channel_distribution,
            "total_events": total_events
        }


# Register all calculators
metric_registry.register(FrameworkUsageCalculator())
metric_registry.register(ModelUsageCalculator())
metric_registry.register(AgentUsageCalculator())
metric_registry.register(SessionCountCalculator())
metric_registry.register(EventTypeDistributionCalculator())
metric_registry.register(ChannelDistributionCalculator()) 