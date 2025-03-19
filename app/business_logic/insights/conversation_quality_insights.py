"""
Conversation Quality Insights module.

This module provides insight extractors for conversation quality metrics.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import statistics
from collections import Counter
from sqlalchemy.orm import Session

from app.business_logic.insights.base import BaseInsightExtractor, insight_registry
from app.models.event import Event


class ConversationQualityInsightExtractor(BaseInsightExtractor):
    """Extractor for conversation quality insights.
    
    Analyzes conversations and provides insights about their quality.
    """
    
    def extract(self, db: Session, start_time: Optional[datetime] = None, 
               end_time: Optional[datetime] = None, 
               agent_id: Optional[str] = None,
               session_id: Optional[str] = None,
               **kwargs) -> Dict[str, Any]:
        """Extract conversation quality insights.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict containing conversation quality insights:
                - response_quality: Assessment of response quality for each session
                - response_time_quality: Assessment of response times for each session
                - conversation_flow: Assessment of conversation flow for each session
                - overall_quality_score: Overall quality score for each session
                - quality_by_agent: Quality metrics aggregated by agent
        """
        # Set default time range if not provided
        if not start_time:
            # Default to last week if no start time
            start_time = datetime.utcnow() - timedelta(days=7)
        
        if not end_time:
            end_time = datetime.utcnow()
        
        # Get model requests and responses
        requests = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["model_request"],
            directions=["outgoing"]
        )
        
        responses = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["model_response"],
            directions=["incoming"]
        )
        
        # Group by session
        sessions = {}
        requests_by_session = {}
        responses_by_session = {}
        session_agents = {}
        
        # Group requests by session
        for request in requests:
            if not request.session_id:
                continue
                
            if request.session_id not in requests_by_session:
                requests_by_session[request.session_id] = []
                sessions[request.session_id] = {
                    "agent_id": request.agent_id,
                    "start_time": request.timestamp,
                    "end_time": request.timestamp,
                    "total_requests": 0,
                    "total_responses": 0,
                    "response_times": []
                }
                session_agents[request.session_id] = request.agent_id
            
            requests_by_session[request.session_id].append(request)
            sessions[request.session_id]["total_requests"] += 1
            
            # Update session time range
            if request.timestamp < sessions[request.session_id]["start_time"]:
                sessions[request.session_id]["start_time"] = request.timestamp
            if request.timestamp > sessions[request.session_id]["end_time"]:
                sessions[request.session_id]["end_time"] = request.timestamp
        
        # Group responses by session
        for response in responses:
            if not response.session_id:
                continue
                
            if response.session_id not in responses_by_session:
                responses_by_session[response.session_id] = []
                if response.session_id not in sessions:
                    sessions[response.session_id] = {
                        "agent_id": response.agent_id,
                        "start_time": response.timestamp,
                        "end_time": response.timestamp,
                        "total_requests": 0,
                        "total_responses": 0,
                        "response_times": []
                    }
                    session_agents[response.session_id] = response.agent_id
            
            responses_by_session[response.session_id].append(response)
            sessions[response.session_id]["total_responses"] += 1
            
            # Get response time if available
            if response.data and response.data.get("performance", {}).get("duration_ms"):
                duration_ms = float(response.data["performance"]["duration_ms"])
                sessions[response.session_id]["response_times"].append(duration_ms)
            
            # Update session time range
            if response.timestamp < sessions[response.session_id]["start_time"]:
                sessions[response.session_id]["start_time"] = response.timestamp
            if response.timestamp > sessions[response.session_id]["end_time"]:
                sessions[response.session_id]["end_time"] = response.timestamp
        
        # Initialize results
        results = {
            "session_insights": {},
            "agent_insights": {}
        }
        
        # Process each session
        for session_id, session_data in sessions.items():
            # Calculate session duration in seconds
            duration_seconds = (session_data["end_time"] - session_data["start_time"]).total_seconds()
            
            # Calculate average response time
            avg_response_time = 0
            if session_data["response_times"]:
                avg_response_time = statistics.mean(session_data["response_times"])
            
            # Calculate response rate
            response_rate = 0
            if session_data["total_requests"] > 0:
                response_rate = session_data["total_responses"] / session_data["total_requests"] * 100
            
            # Assess response time quality
            response_time_quality = ""
            if avg_response_time < 500:
                response_time_quality = "excellent"
            elif avg_response_time < 1000:
                response_time_quality = "good"
            elif avg_response_time < 2000:
                response_time_quality = "fair"
            else:
                response_time_quality = "poor"
            
            # Calculate conversation depth (exchanges per minute)
            conversation_depth = 0
            if duration_seconds > 0:
                exchanges = min(session_data["total_requests"], session_data["total_responses"])
                conversation_depth = exchanges / (duration_seconds / 60)
            
            # Assess conversation flow
            conversation_flow = ""
            if conversation_depth < 0.5:
                conversation_flow = "slow"
            elif conversation_depth < 2:
                conversation_flow = "moderate"
            elif conversation_depth < 5:
                conversation_flow = "good"
            else:
                conversation_flow = "rapid"
            
            # Assess response quality based on available metrics
            # We'll use response rate as a proxy for now
            response_quality = ""
            if response_rate >= 95:
                response_quality = "excellent"
            elif response_rate >= 85:
                response_quality = "good"
            elif response_rate >= 70:
                response_quality = "fair"
            else:
                response_quality = "poor"
            
            # Calculate overall quality score (0-100)
            # Weights: response quality 40%, response time 40%, conversation flow 20%
            quality_score = 0
            
            # Score for response quality
            if response_quality == "excellent":
                quality_score += 40
            elif response_quality == "good":
                quality_score += 30
            elif response_quality == "fair":
                quality_score += 20
            else:  # poor
                quality_score += 10
            
            # Score for response time
            if response_time_quality == "excellent":
                quality_score += 40
            elif response_time_quality == "good":
                quality_score += 30
            elif response_time_quality == "fair":
                quality_score += 20
            else:  # poor
                quality_score += 10
            
            # Score for conversation flow
            if conversation_flow == "good":
                quality_score += 20
            elif conversation_flow == "moderate" or conversation_flow == "rapid":
                quality_score += 15
            else:  # slow
                quality_score += 5
            
            # Store session quality insights
            results["session_insights"][session_id] = {
                "agent_id": session_data["agent_id"],
                "duration_seconds": duration_seconds,
                "total_requests": session_data["total_requests"],
                "total_responses": session_data["total_responses"],
                "response_rate": response_rate,
                "average_response_time_ms": avg_response_time,
                "response_time_quality": response_time_quality,
                "conversation_depth": conversation_depth,
                "conversation_flow": conversation_flow,
                "response_quality": response_quality,
                "overall_quality_score": quality_score
            }
        
        # Aggregate insights by agent
        agent_insights = {}
        
        for session_id, session_insight in results["session_insights"].items():
            agent_id = session_insight["agent_id"]
            
            if agent_id not in agent_insights:
                agent_insights[agent_id] = {
                    "total_sessions": 0,
                    "total_requests": 0,
                    "total_responses": 0,
                    "response_times": [],
                    "quality_scores": [],
                    "response_rates": []
                }
            
            agent_insights[agent_id]["total_sessions"] += 1
            agent_insights[agent_id]["total_requests"] += session_insight["total_requests"]
            agent_insights[agent_id]["total_responses"] += session_insight["total_responses"]
            agent_insights[agent_id]["quality_scores"].append(session_insight["overall_quality_score"])
            agent_insights[agent_id]["response_rates"].append(session_insight["response_rate"])
            
            if session_insight["average_response_time_ms"] > 0:
                agent_insights[agent_id]["response_times"].append(session_insight["average_response_time_ms"])
        
        # Process agent insights
        for agent_id, data in agent_insights.items():
            # Calculate average metrics
            avg_quality_score = statistics.mean(data["quality_scores"]) if data["quality_scores"] else 0
            avg_response_rate = statistics.mean(data["response_rates"]) if data["response_rates"] else 0
            avg_response_time = statistics.mean(data["response_times"]) if data["response_times"] else 0
            
            # Count sessions by quality score
            quality_buckets = {
                "excellent": 0,
                "good": 0,
                "fair": 0,
                "poor": 0
            }
            
            for score in data["quality_scores"]:
                if score >= 80:
                    quality_buckets["excellent"] += 1
                elif score >= 60:
                    quality_buckets["good"] += 1
                elif score >= 40:
                    quality_buckets["fair"] += 1
                else:
                    quality_buckets["poor"] += 1
            
            # Store agent quality insights
            results["agent_insights"][agent_id] = {
                "total_sessions": data["total_sessions"],
                "total_requests": data["total_requests"],
                "total_responses": data["total_responses"],
                "average_quality_score": avg_quality_score,
                "average_response_rate": avg_response_rate,
                "average_response_time_ms": avg_response_time,
                "session_quality_distribution": quality_buckets
            }
            
            # Add quality assessment
            if avg_quality_score >= 80:
                results["agent_insights"][agent_id]["quality_assessment"] = "excellent"
            elif avg_quality_score >= 60:
                results["agent_insights"][agent_id]["quality_assessment"] = "good"
            elif avg_quality_score >= 40:
                results["agent_insights"][agent_id]["quality_assessment"] = "fair"
            else:
                results["agent_insights"][agent_id]["quality_assessment"] = "poor"
        
        return results


class ConversationMetricsInsightExtractor(BaseInsightExtractor):
    """Extractor for detailed conversation metrics insights.
    
    Analyzes conversations and extracts detailed metrics about them.
    """
    
    def extract(self, db: Session, start_time: Optional[datetime] = None, 
               end_time: Optional[datetime] = None, 
               agent_id: Optional[str] = None,
               session_id: Optional[str] = None,
               **kwargs) -> Dict[str, Any]:
        """Extract conversation metrics insights.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict containing conversation metrics insights:
                - conversation_lengths: Distribution of conversation lengths
                - conversation_durations: Distribution of conversation durations
                - response_sizes: Distribution of response sizes (token counts)
                - conversation_topic_diversity: Assessment of topic diversity
                - conversation_patterns: Common conversation patterns
        """
        # Set default time range if not provided
        if not start_time:
            # Default to last week if no start time
            start_time = datetime.utcnow() - timedelta(days=7)
        
        if not end_time:
            end_time = datetime.utcnow()
        
        # Get model responses
        responses = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["model_response"],
            directions=["incoming"]
        )
        
        # Group by session
        responses_by_session = {}
        
        for response in responses:
            if not response.session_id:
                continue
                
            if response.session_id not in responses_by_session:
                responses_by_session[response.session_id] = {
                    "responses": [],
                    "start_time": response.timestamp,
                    "end_time": response.timestamp,
                    "agent_id": response.agent_id,
                    "token_counts": []
                }
            
            responses_by_session[response.session_id]["responses"].append(response)
            
            # Update session time range
            if response.timestamp < responses_by_session[response.session_id]["start_time"]:
                responses_by_session[response.session_id]["start_time"] = response.timestamp
            if response.timestamp > responses_by_session[response.session_id]["end_time"]:
                responses_by_session[response.session_id]["end_time"] = response.timestamp
            
            # Extract token count if available
            if response.data and response.data.get("llm_output", {}).get("usage", {}):
                usage = response.data.get("llm_output", {}).get("usage", {})
                output_tokens = None
                
                if "output_tokens" in usage:
                    output_tokens = int(usage["output_tokens"])
                elif "completion_tokens" in usage:
                    output_tokens = int(usage["completion_tokens"])
                
                # Alternative format in response metadata
                if output_tokens is None:
                    metadata = response.data.get("response", {}).get("message", {}).get("usage_metadata", {})
                    if metadata and "output_tokens" in metadata:
                        output_tokens = int(metadata["output_tokens"])
                
                if output_tokens is not None:
                    responses_by_session[response.session_id]["token_counts"].append(output_tokens)
        
        # Initialize results
        results = {
            "conversation_metrics": {
                "conversation_lengths": [],
                "conversation_durations": [],
                "response_sizes": []
            },
            "distributions": {
                "conversation_length": {
                    "min": 0,
                    "max": 0,
                    "average": 0,
                    "buckets": {}
                },
                "conversation_duration": {
                    "min": 0,
                    "max": 0,
                    "average": 0,
                    "buckets": {}
                },
                "response_size": {
                    "min": 0,
                    "max": 0,
                    "average": 0,
                    "buckets": {}
                }
            }
        }
        
        # Process session data
        if responses_by_session:
            # Collect metrics
            conversation_lengths = []
            conversation_durations = []
            response_sizes = []
            
            for session_id, session_data in responses_by_session.items():
                # Conversation length (number of responses)
                length = len(session_data["responses"])
                conversation_lengths.append(length)
                
                # Conversation duration (in seconds)
                duration = (session_data["end_time"] - session_data["start_time"]).total_seconds()
                conversation_durations.append(duration)
                
                # Response sizes (token counts)
                response_sizes.extend(session_data["token_counts"])
            
            # Store raw metrics
            results["conversation_metrics"]["conversation_lengths"] = conversation_lengths
            results["conversation_metrics"]["conversation_durations"] = conversation_durations
            results["conversation_metrics"]["response_sizes"] = response_sizes
            
            # Calculate statistics for conversation lengths
            if conversation_lengths:
                results["distributions"]["conversation_length"]["min"] = min(conversation_lengths)
                results["distributions"]["conversation_length"]["max"] = max(conversation_lengths)
                results["distributions"]["conversation_length"]["average"] = statistics.mean(conversation_lengths)
                
                # Create buckets for conversation lengths
                buckets = {
                    "1-2": 0,
                    "3-5": 0,
                    "6-10": 0,
                    "11-20": 0,
                    "21+": 0
                }
                
                for length in conversation_lengths:
                    if length <= 2:
                        buckets["1-2"] += 1
                    elif length <= 5:
                        buckets["3-5"] += 1
                    elif length <= 10:
                        buckets["6-10"] += 1
                    elif length <= 20:
                        buckets["11-20"] += 1
                    else:
                        buckets["21+"] += 1
                
                results["distributions"]["conversation_length"]["buckets"] = buckets
            
            # Calculate statistics for conversation durations
            if conversation_durations:
                results["distributions"]["conversation_duration"]["min"] = min(conversation_durations)
                results["distributions"]["conversation_duration"]["max"] = max(conversation_durations)
                results["distributions"]["conversation_duration"]["average"] = statistics.mean(conversation_durations)
                
                # Create buckets for conversation durations (in seconds)
                buckets = {
                    "<10s": 0,
                    "10s-1m": 0,
                    "1m-5m": 0,
                    "5m-15m": 0,
                    "15m+": 0
                }
                
                for duration in conversation_durations:
                    if duration < 10:
                        buckets["<10s"] += 1
                    elif duration < 60:
                        buckets["10s-1m"] += 1
                    elif duration < 300:
                        buckets["1m-5m"] += 1
                    elif duration < 900:
                        buckets["5m-15m"] += 1
                    else:
                        buckets["15m+"] += 1
                
                results["distributions"]["conversation_duration"]["buckets"] = buckets
            
            # Calculate statistics for response sizes
            if response_sizes:
                results["distributions"]["response_size"]["min"] = min(response_sizes)
                results["distributions"]["response_size"]["max"] = max(response_sizes)
                results["distributions"]["response_size"]["average"] = statistics.mean(response_sizes)
                
                # Create buckets for response sizes (in tokens)
                buckets = {
                    "<50": 0,
                    "50-100": 0,
                    "100-200": 0,
                    "200-500": 0,
                    "500+": 0
                }
                
                for size in response_sizes:
                    if size < 50:
                        buckets["<50"] += 1
                    elif size < 100:
                        buckets["50-100"] += 1
                    elif size < 200:
                        buckets["100-200"] += 1
                    elif size < 500:
                        buckets["200-500"] += 1
                    else:
                        buckets["500+"] += 1
                
                results["distributions"]["response_size"]["buckets"] = buckets
            
            # Add session pattern insights
            short_conversations = sum(1 for length in conversation_lengths if length <= 2)
            medium_conversations = sum(1 for length in conversation_lengths if 3 <= length <= 10)
            long_conversations = sum(1 for length in conversation_lengths if length > 10)
            
            total_conversations = len(conversation_lengths)
            conversation_pattern = ""
            
            if total_conversations > 0:
                short_pct = (short_conversations / total_conversations) * 100
                medium_pct = (medium_conversations / total_conversations) * 100
                long_pct = (long_conversations / total_conversations) * 100
                
                if short_pct >= 60:
                    conversation_pattern = "mostly short exchanges"
                elif medium_pct >= 60:
                    conversation_pattern = "balanced exchanges"
                elif long_pct >= 60:
                    conversation_pattern = "deep conversations"
                else:
                    conversation_pattern = "mixed conversation patterns"
            
            results["conversation_pattern_insights"] = {
                "short_conversations_percentage": (short_conversations / total_conversations) * 100 if total_conversations > 0 else 0,
                "medium_conversations_percentage": (medium_conversations / total_conversations) * 100 if total_conversations > 0 else 0,
                "long_conversations_percentage": (long_conversations / total_conversations) * 100 if total_conversations > 0 else 0,
                "overall_pattern": conversation_pattern,
                "total_conversations": total_conversations
            }
        
        return results


# Register the insight extractors
insight_registry.register(ConversationQualityInsightExtractor())
insight_registry.register(ConversationMetricsInsightExtractor()) 