"""
Session Analytics Insights module.

This module provides insight extractors for session-level analytics.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, UTC
import statistics
from collections import Counter
from sqlalchemy.orm import Session

from app.business_logic.insights.base import BaseInsightExtractor, insight_registry
from app.models.event import Event


class SessionTrendsInsightExtractor(BaseInsightExtractor):
    """Extractor for session trends insights.
    
    Analyzes session patterns and provides insights about usage trends.
    """
    
    def extract(self, db: Session, start_time: Optional[datetime] = None, 
               end_time: Optional[datetime] = None, 
               agent_id: Optional[str] = None,
               session_id: Optional[str] = None,
               **kwargs) -> Dict[str, Any]:
        """Extract session trends insights.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict containing session trends insights:
                - session_frequency: Frequency of sessions over time
                - session_duration_trends: Trends in session durations
                - peak_usage_times: Peak times for session activity
                - user_retention: Metrics on returning users/sessions
        """
        # Set default time range if not provided
        if not start_time:
            # Default to last 30 days if no start time
            start_time = datetime.now(UTC) - timedelta(days=30)
        
        if not end_time:
            end_time = datetime.now(UTC)
        
        # Get all events
        events = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id
        )
        
        # Group events by session
        session_events = {}
        
        for event in events:
            if not event.session_id:
                continue
                
            if event.session_id not in session_events:
                session_events[event.session_id] = {
                    "agent_id": event.agent_id,
                    "events": [],
                    "start_time": event.timestamp,
                    "end_time": event.timestamp,
                    "day": event.timestamp.strftime("%Y-%m-%d"),
                    "hour": event.timestamp.hour
                }
            
            session_events[event.session_id]["events"].append(event)
            
            # Update session time range
            if event.timestamp < session_events[event.session_id]["start_time"]:
                session_events[event.session_id]["start_time"] = event.timestamp
            if event.timestamp > session_events[event.session_id]["end_time"]:
                session_events[event.session_id]["end_time"] = event.timestamp
        
        # Initialize results
        results = {
            "session_count": len(session_events),
            "session_frequency": {
                "daily": {},
                "weekly": {},
                "hourly": {}
            },
            "session_duration_trends": {
                "average_duration_ms": 0,
                "duration_by_day": {},
                "duration_by_hour": {}
            },
            "peak_usage_times": {
                "peak_days": [],
                "peak_hours": []
            },
            "user_retention": {
                "unique_agents": 0,
                "sessions_per_agent": {},
                "returning_agent_percentage": 0
            }
        }
        
        # Process session data
        if session_events:
            # Calculate session durations
            durations = []
            duration_by_day = {}
            duration_by_hour = {}
            sessions_by_day = {}
            sessions_by_hour = {}
            sessions_by_agent = {}
            
            for session_id, data in session_events.items():
                # Session duration in seconds
                duration_seconds = (data["end_time"] - data["start_time"]).total_seconds()
                durations.append(duration_seconds)
                
                # Group by day
                day = data["day"]
                if day not in duration_by_day:
                    duration_by_day[day] = []
                    sessions_by_day[day] = 0
                
                duration_by_day[day].append(duration_seconds)
                sessions_by_day[day] += 1
                
                # Group by hour
                hour = data["hour"]
                if hour not in duration_by_hour:
                    duration_by_hour[hour] = []
                    sessions_by_hour[hour] = 0
                
                duration_by_hour[hour].append(duration_seconds)
                sessions_by_hour[hour] += 1
                
                # Group by agent
                agent_id = data["agent_id"]
                if agent_id not in sessions_by_agent:
                    sessions_by_agent[agent_id] = 0
                
                sessions_by_agent[agent_id] += 1
            
            # Calculate average duration
            if durations:
                results["session_duration_trends"]["average_duration_ms"] = statistics.mean(durations) * 1000  # Convert to ms
            
            # Calculate average durations by day
            for day, day_durations in duration_by_day.items():
                results["session_duration_trends"]["duration_by_day"][day] = statistics.mean(day_durations) * 1000  # Convert to ms
            
            # Calculate average durations by hour
            for hour, hour_durations in duration_by_hour.items():
                results["session_duration_trends"]["duration_by_hour"][hour] = statistics.mean(hour_durations) * 1000  # Convert to ms
            
            # Calculate session frequency by day
            for day, count in sessions_by_day.items():
                results["session_frequency"]["daily"][day] = count
            
            # Calculate session frequency by hour
            for hour, count in sessions_by_hour.items():
                results["session_frequency"]["hourly"][hour] = count
            
            # Calculate weekly aggregates
            weekly_sessions = {}
            for day, count in sessions_by_day.items():
                # Convert day to datetime
                day_date = datetime.strptime(day, "%Y-%m-%d")
                # Get ISO week number
                week = f"{day_date.year}-W{day_date.isocalendar()[1]:02d}"
                
                if week not in weekly_sessions:
                    weekly_sessions[week] = 0
                
                weekly_sessions[week] += count
            
            results["session_frequency"]["weekly"] = weekly_sessions
            
            # Identify peak usage times
            # Peak days
            if sessions_by_day:
                peak_day_count = max(sessions_by_day.values())
                peak_days = [day for day, count in sessions_by_day.items() if count == peak_day_count]
                results["peak_usage_times"]["peak_days"] = peak_days
            
            # Peak hours
            if sessions_by_hour:
                peak_hour_count = max(sessions_by_hour.values())
                peak_hours = [hour for hour, count in sessions_by_hour.items() if count == peak_hour_count]
                results["peak_usage_times"]["peak_hours"] = peak_hours
            
            # User retention metrics
            unique_agents = len(sessions_by_agent)
            results["user_retention"]["unique_agents"] = unique_agents
            results["user_retention"]["sessions_per_agent"] = sessions_by_agent
            
            # Calculate returning agent percentage
            agents_with_multiple_sessions = sum(1 for agent, count in sessions_by_agent.items() if count > 1)
            if unique_agents > 0:
                results["user_retention"]["returning_agent_percentage"] = (agents_with_multiple_sessions / unique_agents) * 100
        
        return results


class UserBehaviorInsightExtractor(BaseInsightExtractor):
    """Extractor for user behavior insights.
    
    Analyzes user/agent behavior patterns across sessions.
    """
    
    def extract(self, db: Session, start_time: Optional[datetime] = None, 
               end_time: Optional[datetime] = None, 
               agent_id: Optional[str] = None,
               session_id: Optional[str] = None,
               **kwargs) -> Dict[str, Any]:
        """Extract user behavior insights.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict containing user behavior insights:
                - usage_patterns: Common usage patterns by agent
                - engagement_metrics: Metrics on agent engagement
                - feature_usage: Most commonly used features/request types
                - behavior_segments: Agent segmentation by behavior
        """
        # Set default time range if not provided
        if not start_time:
            # Default to last 30 days if no start time
            start_time = datetime.now(UTC) - timedelta(days=30)
        
        if not end_time:
            end_time = datetime.now(UTC)
        
        # Get all events
        events = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id
        )
        
        # Group events by agent and session
        agent_events = {}
        session_events = {}
        
        for event in events:
            # Group by agent
            if event.agent_id:
                if event.agent_id not in agent_events:
                    agent_events[event.agent_id] = {
                        "events": [],
                        "sessions": set(),
                        "event_types": Counter(),
                        "channels": Counter(),
                        "first_seen": event.timestamp,
                        "last_seen": event.timestamp
                    }
                
                agent_events[event.agent_id]["events"].append(event)
                
                if event.session_id:
                    agent_events[event.agent_id]["sessions"].add(event.session_id)
                
                agent_events[event.agent_id]["event_types"][event.event_type] += 1
                
                if event.channel:
                    agent_events[event.agent_id]["channels"][event.channel] += 1
                
                # Update time range
                if event.timestamp < agent_events[event.agent_id]["first_seen"]:
                    agent_events[event.agent_id]["first_seen"] = event.timestamp
                if event.timestamp > agent_events[event.agent_id]["last_seen"]:
                    agent_events[event.agent_id]["last_seen"] = event.timestamp
            
            # Group by session
            if event.session_id:
                if event.session_id not in session_events:
                    session_events[event.session_id] = {
                        "agent_id": event.agent_id,
                        "events": [],
                        "event_types": Counter(),
                        "start_time": event.timestamp,
                        "end_time": event.timestamp
                    }
                
                session_events[event.session_id]["events"].append(event)
                session_events[event.session_id]["event_types"][event.event_type] += 1
                
                # Update time range
                if event.timestamp < session_events[event.session_id]["start_time"]:
                    session_events[event.session_id]["start_time"] = event.timestamp
                if event.timestamp > session_events[event.session_id]["end_time"]:
                    session_events[event.session_id]["end_time"] = event.timestamp
        
        # Initialize results
        results = {
            "usage_patterns": {
                "by_agent": {}
            },
            "engagement_metrics": {
                "by_agent": {}
            },
            "feature_usage": {
                "top_event_types": {},
                "top_channels": {}
            },
            "behavior_segments": {
                "segments": {},
                "agent_segments": {}
            }
        }
        
        # Process agent data
        if agent_events:
            all_event_types = Counter()
            all_channels = Counter()
            
            # Extract usage patterns and engagement metrics
            for agent_id, data in agent_events.items():
                # Calculate total activity days
                first_day = data["first_seen"].date()
                last_day = data["last_seen"].date()
                total_days = (last_day - first_day).days + 1
                
                # Count of days with activity
                days_with_activity = len(set(event.timestamp.date() for event in data["events"]))
                
                # Calculate activity pattern
                if total_days > 0:
                    activity_frequency = days_with_activity / total_days
                else:
                    activity_frequency = 0
                
                activity_pattern = ""
                if activity_frequency >= 0.7:
                    activity_pattern = "frequent"
                elif activity_frequency >= 0.3:
                    activity_pattern = "regular"
                else:
                    activity_pattern = "occasional"
                
                # Calculate session frequency
                session_count = len(data["sessions"])
                sessions_per_day = session_count / total_days if total_days > 0 else 0
                
                session_frequency = ""
                if sessions_per_day >= 2:
                    session_frequency = "high"
                elif sessions_per_day >= 0.5:
                    session_frequency = "medium"
                else:
                    session_frequency = "low"
                
                # Get top event types
                top_event_types = data["event_types"].most_common(3)
                
                # Calculate feature diversity (number of unique event types)
                feature_diversity = len(data["event_types"])
                
                # Update global counters
                all_event_types.update(data["event_types"])
                all_channels.update(data["channels"])
                
                # Store agent usage pattern
                results["usage_patterns"]["by_agent"][agent_id] = {
                    "activity_frequency": activity_frequency,
                    "activity_pattern": activity_pattern,
                    "session_count": session_count,
                    "sessions_per_day": sessions_per_day,
                    "session_frequency": session_frequency,
                    "top_event_types": top_event_types,
                    "feature_diversity": feature_diversity
                }
                
                # Calculate engagement metrics
                # Total time range in days
                time_range_days = total_days
                
                # Average events per session
                events_per_session = len(data["events"]) / session_count if session_count > 0 else 0
                
                # Engagement score (0-100)
                engagement_score = min(100, (
                    (activity_frequency * 40) +
                    (min(1, sessions_per_day / 3) * 30) +
                    (min(1, events_per_session / 20) * 30)
                ))
                
                # Engagement level
                engagement_level = ""
                if engagement_score >= 70:
                    engagement_level = "high"
                elif engagement_score >= 40:
                    engagement_level = "medium"
                else:
                    engagement_level = "low"
                
                # Store agent engagement metrics
                results["engagement_metrics"]["by_agent"][agent_id] = {
                    "time_range_days": time_range_days,
                    "days_with_activity": days_with_activity,
                    "events_per_session": events_per_session,
                    "engagement_score": engagement_score,
                    "engagement_level": engagement_level
                }
            
            # Top feature usage across all agents
            results["feature_usage"]["top_event_types"] = dict(all_event_types.most_common(10))
            results["feature_usage"]["top_channels"] = dict(all_channels.most_common(5))
            
            # Behavior segmentation
            # Define behavior segments
            segments = {
                "power_users": {
                    "criteria": lambda agent_data: (
                        agent_data["engagement_metrics"]["engagement_level"] == "high" and
                        agent_data["usage_patterns"]["feature_diversity"] >= 5
                    ),
                    "agents": []
                },
                "regular_users": {
                    "criteria": lambda agent_data: (
                        agent_data["engagement_metrics"]["engagement_level"] == "medium" and
                        agent_data["usage_patterns"]["activity_pattern"] in ["regular", "frequent"]
                    ),
                    "agents": []
                },
                "occasional_users": {
                    "criteria": lambda agent_data: (
                        agent_data["engagement_metrics"]["engagement_level"] == "low" or
                        agent_data["usage_patterns"]["activity_pattern"] == "occasional"
                    ),
                    "agents": []
                },
                "new_users": {
                    "criteria": lambda agent_data: (
                        agent_data["engagement_metrics"]["time_range_days"] <= 7
                    ),
                    "agents": []
                }
            }
            
            # Segment agents
            for agent_id in agent_events.keys():
                agent_data = {
                    "usage_patterns": results["usage_patterns"]["by_agent"][agent_id],
                    "engagement_metrics": results["engagement_metrics"]["by_agent"][agent_id]
                }
                
                assigned_segment = None
                
                # Check segments in priority order
                for segment_name, segment_info in segments.items():
                    if segment_info["criteria"](agent_data):
                        segment_info["agents"].append(agent_id)
                        assigned_segment = segment_name
                        break
                
                # Store agent segment
                results["behavior_segments"]["agent_segments"][agent_id] = assigned_segment
            
            # Store segment information
            for segment_name, segment_info in segments.items():
                results["behavior_segments"]["segments"][segment_name] = {
                    "count": len(segment_info["agents"]),
                    "agents": segment_info["agents"]
                }
        
        return results


# Register the insight extractors
insight_registry.register(SessionTrendsInsightExtractor())
insight_registry.register(UserBehaviorInsightExtractor()) 