"""
Agent Health Insights module.

This module provides insight extractors for agent health and activity metrics.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, UTC
from collections import Counter
from sqlalchemy.orm import Session

from app.business_logic.insights.base import BaseInsightExtractor, insight_registry
from app.business_logic.metrics.performance_metrics import ResponseTimeCalculator
from app.business_logic.metrics.error_metrics import ErrorRateCalculator
from app.models.event import Event


class AgentHealthInsightExtractor(BaseInsightExtractor):
    """Extractor for agent health insights.
    
    Analyzes agent activities and provides insights about their health and status.
    """
    
    def extract(self, db: Session, start_time: Optional[datetime] = None, 
               end_time: Optional[datetime] = None, 
               agent_id: Optional[str] = None,
               session_id: Optional[str] = None,
               **kwargs) -> Dict[str, Any]:
        """Extract agent health insights.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict containing agent health insights:
                - agent_status: Status assessment for each agent
                - health_score: Numerical score for agent health (0-100)
                - activity_level: Assessment of agent activity level
                - response_time_assessment: Assessment of agent response times
                - error_rate_assessment: Assessment of agent error rates
                - recommendations: List of recommendations for improving agent health
        """
        # Set default time range if not provided
        if not start_time:
            # Default to last day if no start time
            start_time = datetime.now(UTC) - timedelta(days=1)
        
        if not end_time:
            end_time = datetime.now(UTC)
        
        # Calculate metrics needed for insights
        response_time_calculator = ResponseTimeCalculator()
        response_metrics = response_time_calculator.calculate(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id
        )
        
        error_rate_calculator = ErrorRateCalculator()
        error_metrics = error_rate_calculator.calculate(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id
        )
        
        # Get all events to analyze activity
        all_events = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id
        )
        
        # Group events by agent
        events_by_agent = {}
        for event in all_events:
            if event.agent_id not in events_by_agent:
                events_by_agent[event.agent_id] = []
            events_by_agent[event.agent_id].append(event)
        
        # Initialize insight results
        results = {
            "agent_insights": {}
        }
        
        # Process each agent
        for agent_id, events in events_by_agent.items():
            # Calculate activity level
            events_per_hour = len(events) / max(1, (end_time - start_time).total_seconds() / 3600)
            
            if events_per_hour < 1:
                activity_level = "inactive"
            elif events_per_hour < 10:
                activity_level = "low"
            elif events_per_hour < 50:
                activity_level = "moderate"
            else:
                activity_level = "high"
            
            # Calculate response time assessment
            agent_response_times = []
            for event in events:
                if event.event_type == "model_response" and event.data and event.data.get("performance", {}).get("duration_ms"):
                    duration_ms = float(event.data["performance"]["duration_ms"])
                    agent_response_times.append(duration_ms)
            
            avg_response_time = sum(agent_response_times) / max(1, len(agent_response_times))
            
            if avg_response_time < 500:
                response_time_assessment = "excellent"
            elif avg_response_time < 1000:
                response_time_assessment = "good"
            elif avg_response_time < 2000:
                response_time_assessment = "fair"
            else:
                response_time_assessment = "poor"
            
            # Calculate error rate assessment
            agent_error_rate = 0
            for event in events:
                if event.level in ["ERROR", "WARNING"]:
                    agent_error_rate += 1
            
            agent_error_rate = (agent_error_rate / max(1, len(events))) * 100
            
            if agent_error_rate < 1:
                error_rate_assessment = "excellent"
            elif agent_error_rate < 5:
                error_rate_assessment = "good"
            elif agent_error_rate < 10:
                error_rate_assessment = "fair"
            else:
                error_rate_assessment = "poor"
            
            # Calculate overall health score (0-100)
            # Weight factors: activity 20%, response time 40%, error rate 40%
            activity_score = 0
            if activity_level == "high":
                activity_score = 100
            elif activity_level == "moderate":
                activity_score = 75
            elif activity_level == "low":
                activity_score = 50
            else:  # inactive
                activity_score = 0
            
            response_time_score = 0
            if response_time_assessment == "excellent":
                response_time_score = 100
            elif response_time_assessment == "good":
                response_time_score = 75
            elif response_time_assessment == "fair":
                response_time_score = 50
            else:  # poor
                response_time_score = 25
            
            error_rate_score = 0
            if error_rate_assessment == "excellent":
                error_rate_score = 100
            elif error_rate_assessment == "good":
                error_rate_score = 75
            elif error_rate_assessment == "fair":
                error_rate_score = 50
            else:  # poor
                error_rate_score = 25
            
            health_score = (
                activity_score * 0.2 +
                response_time_score * 0.4 +
                error_rate_score * 0.4
            )
            
            # Determine overall status
            if health_score >= 80:
                status = "healthy"
            elif health_score >= 60:
                status = "stable"
            elif health_score >= 40:
                status = "degraded"
            else:
                status = "unhealthy"
            
            # Generate recommendations
            recommendations = []
            
            if activity_level == "inactive" or activity_level == "low":
                recommendations.append("Increase agent activity or check for configuration issues")
            
            if response_time_assessment == "fair" or response_time_assessment == "poor":
                recommendations.append("Optimize response times by using a faster LLM model or reducing prompt complexity")
            
            if error_rate_assessment == "fair" or error_rate_assessment == "poor":
                recommendations.append("Investigate and fix errors to improve stability")
            
            # Count event types for activity breakdown
            event_types = Counter([event.event_type for event in events])
            
            # Store agent insights
            results["agent_insights"][agent_id] = {
                "status": status,
                "health_score": health_score,
                "activity_level": activity_level,
                "events_per_hour": events_per_hour,
                "response_time_assessment": response_time_assessment,
                "average_response_time_ms": avg_response_time,
                "error_rate_assessment": error_rate_assessment,
                "error_rate_percentage": agent_error_rate,
                "recommendations": recommendations,
                "activity_breakdown": dict(event_types),
                "total_events": len(events)
            }
        
        # Add overall insights
        if len(events_by_agent) > 0:
            # Calculate average health score across all agents
            avg_health_score = sum(agent["health_score"] for agent in results["agent_insights"].values()) / len(results["agent_insights"])
            
            # Count agents by status
            status_counts = Counter([agent["status"] for agent in results["agent_insights"].values()])
            
            results["overall_insights"] = {
                "average_health_score": avg_health_score,
                "agent_status_counts": dict(status_counts),
                "total_agents": len(events_by_agent),
                "time_range_hours": (end_time - start_time).total_seconds() / 3600
            }
            
            # Add overall assessment
            if avg_health_score >= 80:
                results["overall_insights"]["assessment"] = "System is healthy with good agent performance"
            elif avg_health_score >= 60:
                results["overall_insights"]["assessment"] = "System is stable but some agents may need attention"
            elif avg_health_score >= 40:
                results["overall_insights"]["assessment"] = "System is degraded and requires investigation"
            else:
                results["overall_insights"]["assessment"] = "System is unhealthy and requires immediate attention"
        
        return results


class AgentActivityInsightExtractor(BaseInsightExtractor):
    """Extractor for agent activity insights.
    
    Analyzes agent activities over time and provides activity pattern insights.
    """
    
    def extract(self, db: Session, start_time: Optional[datetime] = None, 
               end_time: Optional[datetime] = None, 
               agent_id: Optional[str] = None,
               session_id: Optional[str] = None,
               interval: str = "hour",
               **kwargs) -> Dict[str, Any]:
        """Extract agent activity insights.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            interval: Time interval for grouping ("hour", "day", "week")
            
        Returns:
            Dict containing agent activity insights:
                - activity_patterns: Activity patterns over time
                - active_periods: Most active time periods
                - inactive_periods: Least active or inactive time periods
                - activity_trends: Trends in activity over time
        """
        # Set default time range if not provided
        if not start_time:
            # Default to last week if no start time
            start_time = datetime.now(UTC) - timedelta(days=7)
        
        if not end_time:
            end_time = datetime.now(UTC)
        
        # Get time format string based on interval
        if interval == "hour":
            time_format = "%Y-%m-%d %H:00"
        elif interval == "day":
            time_format = "%Y-%m-%d"
        elif interval == "week":
            time_format = "%Y-%W"  # ISO week number
        else:
            time_format = "%Y-%m-%d %H:00"  # Default to hour
        
        # Get all events
        all_events = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id
        )
        
        # Group events by agent and time interval
        activity_by_agent_time = {}
        
        for event in all_events:
            agent_id = event.agent_id
            time_key = event.timestamp.strftime(time_format)
            
            if agent_id not in activity_by_agent_time:
                activity_by_agent_time[agent_id] = {}
            
            if time_key not in activity_by_agent_time[agent_id]:
                activity_by_agent_time[agent_id][time_key] = {
                    "total_events": 0,
                    "event_types": Counter()
                }
            
            activity_by_agent_time[agent_id][time_key]["total_events"] += 1
            activity_by_agent_time[agent_id][time_key]["event_types"][event.event_type] += 1
        
        # Process activity data for each agent
        results = {
            "agent_activity_insights": {},
            "overall_activity": {}
        }
        
        overall_activity_by_time = {}
        
        for agent_id, activity_data in activity_by_agent_time.items():
            # Sort time periods by activity level
            sorted_periods = sorted(
                activity_data.items(),
                key=lambda x: x[1]["total_events"],
                reverse=True
            )
            
            # Get most active periods (top 20%)
            num_active_periods = max(1, len(sorted_periods) // 5)
            active_periods = sorted_periods[:num_active_periods]
            
            # Get inactive periods (bottom 20%)
            num_inactive_periods = max(1, len(sorted_periods) // 5)
            inactive_periods = sorted_periods[-num_inactive_periods:]
            
            # Identify activity trends
            if len(sorted_periods) >= 2:
                time_ordered_periods = sorted(sorted_periods, key=lambda x: x[0])
                
                # Calculate moving average of activity
                window_size = min(3, len(time_ordered_periods))
                activity_trend = []
                
                for i in range(len(time_ordered_periods) - window_size + 1):
                    window = time_ordered_periods[i:i+window_size]
                    avg_activity = sum(period[1]["total_events"] for period in window) / window_size
                    activity_trend.append((window[-1][0], avg_activity))
                
                # Determine trend direction
                if len(activity_trend) >= 2:
                    first_avg = activity_trend[0][1]
                    last_avg = activity_trend[-1][1]
                    
                    if last_avg > first_avg * 1.2:
                        trend_direction = "increasing"
                    elif last_avg < first_avg * 0.8:
                        trend_direction = "decreasing"
                    else:
                        trend_direction = "stable"
                else:
                    trend_direction = "unknown"
            else:
                trend_direction = "unknown"
            
            # Format results for this agent
            agent_result = {
                "active_periods": [
                    {
                        "time_period": period[0],
                        "event_count": period[1]["total_events"],
                        "event_types": dict(period[1]["event_types"])
                    }
                    for period in active_periods
                ],
                "inactive_periods": [
                    {
                        "time_period": period[0],
                        "event_count": period[1]["total_events"],
                        "event_types": dict(period[1]["event_types"])
                    }
                    for period in inactive_periods
                ],
                "activity_trend": trend_direction,
                "total_active_periods": len(sorted_periods),
                "average_events_per_period": sum(period[1]["total_events"] for period in sorted_periods) / len(sorted_periods) if sorted_periods else 0
            }
            
            results["agent_activity_insights"][agent_id] = agent_result
            
            # Aggregate for overall activity
            for time_key, data in activity_data.items():
                if time_key not in overall_activity_by_time:
                    overall_activity_by_time[time_key] = {
                        "total_events": 0,
                        "active_agents": set()
                    }
                
                overall_activity_by_time[time_key]["total_events"] += data["total_events"]
                overall_activity_by_time[time_key]["active_agents"].add(agent_id)
        
        # Process overall activity
        if overall_activity_by_time:
            # Convert to list and sort by time
            overall_activity_list = [
                {
                    "time_period": time_key,
                    "total_events": data["total_events"],
                    "active_agent_count": len(data["active_agents"])
                }
                for time_key, data in overall_activity_by_time.items()
            ]
            
            # Sort by time
            overall_activity_list.sort(key=lambda x: x["time_period"])
            
            # Find peak activity periods
            sorted_by_activity = sorted(
                overall_activity_list,
                key=lambda x: x["total_events"],
                reverse=True
            )
            
            num_peak_periods = max(1, len(sorted_by_activity) // 5)
            peak_activity_periods = sorted_by_activity[:num_peak_periods]
            
            # Determine overall trend
            if len(overall_activity_list) >= 2:
                first_activity = overall_activity_list[0]["total_events"]
                last_activity = overall_activity_list[-1]["total_events"]
                
                if last_activity > first_activity * 1.2:
                    overall_trend = "increasing"
                elif last_activity < first_activity * 0.8:
                    overall_trend = "decreasing"
                else:
                    overall_trend = "stable"
            else:
                overall_trend = "unknown"
            
            results["overall_activity"] = {
                "activity_by_time": overall_activity_list,
                "peak_activity_periods": peak_activity_periods,
                "overall_trend": overall_trend,
                "total_events": sum(item["total_events"] for item in overall_activity_list),
                "time_periods_count": len(overall_activity_list)
            }
        
        return results


# Register the insight extractors
insight_registry.register(AgentHealthInsightExtractor())
insight_registry.register(AgentActivityInsightExtractor()) 