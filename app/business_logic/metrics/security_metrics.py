"""
Security Metrics module.

This module provides metric calculators for security alerts and risks.
Each calculator focuses on a specific metric for better modularity.
"""

from typing import Dict, Any, Optional, List, Counter
from datetime import datetime, timedelta, UTC
from collections import defaultdict
from sqlalchemy.orm import Session

from app.business_logic.metrics.base import BaseMetricCalculator, metric_registry
from app.models.event import Event


class SecurityAlertCountCalculator(BaseMetricCalculator):
    """Calculator for security alert counts.
    
    Calculates total number of security alerts and the alert rate.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """Calculate security alert count metrics.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict containing security alert count metrics:
                - total_events: Total number of events in the period
                - total_security_alerts: Total number of security alerts
                - alert_rate: Percentage of events that are security alerts
        """
        # Get all events
        all_events = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id
        )
        
        # Get security alert events
        security_events = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["security_alert"]
        )
        
        # Count totals
        total_events = len(all_events)
        total_security_alerts = len(security_events)
        
        # Calculate alert rate
        alert_rate = (total_security_alerts / total_events) * 100 if total_events > 0 else 0
        
        return {
            "total_events": total_events,
            "total_security_alerts": total_security_alerts,
            "alert_rate": alert_rate
        }

    def get_filtered_events(self, db: Session, start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           agent_id: Optional[str] = None,
                           session_id: Optional[str] = None,
                           event_types: Optional[List[str]] = None,
                           channels: Optional[List[str]] = None,
                           levels: Optional[List[str]] = None,
                           directions: Optional[List[str]] = None) -> List[Event]:
        """Get filtered events based on parameters with direction filter."""
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
            
        if directions:
            query = query.filter(Event.direction.in_(directions))
        
        return query.all()


class AlertsBySeverityCalculator(BaseMetricCalculator):
    """Calculator for security alerts by severity level.
    
    Calculates the distribution of security alerts by severity level.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """Calculate security alerts by severity metrics.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict containing security alerts by severity metrics:
                - alerts_by_level: Counts of alerts grouped by severity level
                - total_alerts: Total number of security alerts
        """
        # Get security alert events
        security_events = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["security_alert"]
        )
        
        # Count alerts by severity level
        alerts_by_level = defaultdict(int)
        
        for event in security_events:
            # Extract severity level from event data
            severity = "unknown"
            
            if event.data and "severity" in event.data:
                severity = event.data["severity"]
            elif event.level:
                # Use event level as fallback
                severity = event.level
                
            alerts_by_level[severity] += 1
        
        return {
            "alerts_by_level": dict(alerts_by_level),
            "total_alerts": len(security_events)
        }

    def get_filtered_events(self, db: Session, start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           agent_id: Optional[str] = None,
                           session_id: Optional[str] = None,
                           event_types: Optional[List[str]] = None,
                           channels: Optional[List[str]] = None,
                           levels: Optional[List[str]] = None,
                           directions: Optional[List[str]] = None) -> List[Event]:
        """Get filtered events based on parameters with direction filter."""
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
            
        if directions:
            query = query.filter(Event.direction.in_(directions))
        
        return query.all()


class AlertsByCategoryCalculator(BaseMetricCalculator):
    """Calculator for security alerts by category.
    
    Calculates the distribution of security alerts by category.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """Calculate security alerts by category metrics.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict containing security alerts by category metrics:
                - alerts_by_category: Counts of alerts grouped by category
                - total_alerts: Total number of security alerts
        """
        # Get security alert events
        security_events = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["security_alert"]
        )
        
        # Count alerts by category
        alerts_by_category = defaultdict(int)
        
        for event in security_events:
            # Extract category from event data
            category = "unknown"
            
            if event.data:
                if "category" in event.data:
                    category = event.data["category"]
                elif "type" in event.data:
                    # Use event type as fallback
                    category = event.data["type"]
                    
            alerts_by_category[category] += 1
        
        return {
            "alerts_by_category": dict(alerts_by_category),
            "total_alerts": len(security_events)
        }

    def get_filtered_events(self, db: Session, start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           agent_id: Optional[str] = None,
                           session_id: Optional[str] = None,
                           event_types: Optional[List[str]] = None,
                           channels: Optional[List[str]] = None,
                           levels: Optional[List[str]] = None,
                           directions: Optional[List[str]] = None) -> List[Event]:
        """Get filtered events based on parameters with direction filter."""
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
            
        if directions:
            query = query.filter(Event.direction.in_(directions))
        
        return query.all()


class AlertsByAgentCalculator(BaseMetricCalculator):
    """Calculator for security alerts by agent.
    
    Calculates the distribution of security alerts by agent.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """Calculate security alerts by agent metrics.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict containing security alerts by agent metrics:
                - alerts_by_agent: Counts of alerts grouped by agent
                - total_alerts: Total number of security alerts
        """
        # Skip agent filtering for this metric if an agent_id is specified
        # So we can compare different agents
        filtered_agent_id = None
        
        # Get security alert events
        security_events = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=filtered_agent_id,
            session_id=session_id,
            event_types=["security_alert"]
        )
        
        # Count alerts by agent
        alerts_by_agent = defaultdict(int)
        
        for event in security_events:
            # Skip if no agent_id
            if not event.agent_id:
                continue
                
            alerts_by_agent[event.agent_id] += 1
        
        return {
            "alerts_by_agent": dict(alerts_by_agent),
            "total_alerts": len(security_events)
        }

    def get_filtered_events(self, db: Session, start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           agent_id: Optional[str] = None,
                           session_id: Optional[str] = None,
                           event_types: Optional[List[str]] = None,
                           channels: Optional[List[str]] = None,
                           levels: Optional[List[str]] = None,
                           directions: Optional[List[str]] = None) -> List[Event]:
        """Get filtered events based on parameters with direction filter."""
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
            
        if directions:
            query = query.filter(Event.direction.in_(directions))
        
        return query.all()


class SecurityAlertTrendCalculator(BaseMetricCalculator):
    """Calculator for security alert trends.
    
    Calculates trends in security alerts over time.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 interval: str = 'hour',
                 **kwargs) -> Dict[str, Any]:
        """Calculate security alert trend metrics.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            interval: Time interval for grouping ('hour', 'day', 'week')
            
        Returns:
            Dict containing security alert trend metrics:
                - alert_trends: Alert counts grouped by time interval
                - alert_rate_trends: Alert rates grouped by time interval
                - severity_trends: Alert severity counts grouped by time interval
                - interval: The time interval used for grouping
        """
        # Set default time range if not provided based on interval
        if not start_time:
            if interval == 'hour':
                start_time = datetime.now(UTC) - timedelta(days=1)
            elif interval == 'day':
                start_time = datetime.now(UTC) - timedelta(days=7)
            else:  # 'week'
                start_time = datetime.now(UTC) - timedelta(days=30)
        
        if not end_time:
            end_time = datetime.now(UTC)
        
        # Format for grouping timestamps by interval
        if interval == 'hour':
            format_str = "%Y-%m-%d %H:00"
        elif interval == 'day':
            format_str = "%Y-%m-%d"
        else:  # 'week'
            format_str = "%Y-%W"  # Year and week number
            
        # Get all events and security alerts
        all_events = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id
        )
        
        security_events = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["security_alert"]
        )
        
        # Group events by interval
        events_by_interval = defaultdict(int)
        alerts_by_interval = defaultdict(int)
        severity_by_interval = defaultdict(lambda: defaultdict(int))
        
        for event in all_events:
            interval_key = event.timestamp.strftime(format_str)
            events_by_interval[interval_key] += 1
        
        for event in security_events:
            interval_key = event.timestamp.strftime(format_str)
            alerts_by_interval[interval_key] += 1
            
            # Extract severity level from event data
            severity = "unknown"
            
            if event.data and "severity" in event.data:
                severity = event.data["severity"]
            elif event.level:
                # Use event level as fallback
                severity = event.level
                
            severity_by_interval[interval_key][severity] += 1
        
        # Calculate alert trends and rates
        alert_trends = {}
        alert_rate_trends = {}
        severity_trends = {}
        
        # First pass: ensure all intervals have entries for all severity levels found
        all_severities = set()
        for interval_data in severity_by_interval.values():
            all_severities.update(interval_data.keys())
        
        # Second pass: build the result dictionaries
        for interval_key in sorted(events_by_interval.keys()):
            event_count = events_by_interval[interval_key]
            alert_count = alerts_by_interval.get(interval_key, 0)
            
            # Alert counts
            alert_trends[interval_key] = {
                "count": alert_count
            }
            
            # Alert rates
            alert_rate = (alert_count / event_count) * 100 if event_count > 0 else 0
            alert_rate_trends[interval_key] = {
                "rate": alert_rate,
                "alert_count": alert_count,
                "event_count": event_count
            }
            
            # Severity counts
            severity_data = {}
            for severity in all_severities:
                severity_data[severity] = severity_by_interval[interval_key].get(severity, 0)
                
            severity_trends[interval_key] = severity_data
        
        return {
            "alert_trends": alert_trends,
            "alert_rate_trends": alert_rate_trends,
            "severity_trends": severity_trends,
            "interval": interval
        }

    def get_filtered_events(self, db: Session, start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           agent_id: Optional[str] = None,
                           session_id: Optional[str] = None,
                           event_types: Optional[List[str]] = None,
                           channels: Optional[List[str]] = None,
                           levels: Optional[List[str]] = None,
                           directions: Optional[List[str]] = None) -> List[Event]:
        """Get filtered events based on parameters with direction filter."""
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
            
        if directions:
            query = query.filter(Event.direction.in_(directions))
        
        return query.all()


# Register the metric calculators
metric_registry.register(SecurityAlertCountCalculator())
metric_registry.register(AlertsBySeverityCalculator())
metric_registry.register(AlertsByCategoryCalculator())
metric_registry.register(AlertsByAgentCalculator())
metric_registry.register(SecurityAlertTrendCalculator()) 