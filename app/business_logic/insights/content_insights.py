"""
Content Insights module.

This module provides insight extractors for content analytics.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import statistics
from collections import Counter, defaultdict
from sqlalchemy.orm import Session
import json
import re

from app.business_logic.insights.base import BaseInsightExtractor, insight_registry
from app.models.event import Event


class ContentUsageInsightExtractor(BaseInsightExtractor):
    """Extractor for content usage insights.
    
    Analyzes content usage patterns across model calls.
    """
    
    def extract(self, db: Session, start_time: Optional[datetime] = None, 
               end_time: Optional[datetime] = None, 
               agent_id: Optional[str] = None,
               session_id: Optional[str] = None,
               **kwargs) -> Dict[str, Any]:
        """Extract content usage insights.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict containing content usage insights:
                - model_usage: Usage statistics by model
                - model_comparison: Comparative performance of different models
                - content_type_distribution: Distribution of content types
                - content_trends: Trends in content over time
        """
        # Set default time range if not provided
        if not start_time:
            # Default to last 7 days if no start time
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
        
        # Initialize results
        results = {
            "model_usage": {
                "total_requests": len(requests),
                "total_responses": len(responses),
                "models": {},
                "total_tokens": {
                    "input": 0,
                    "output": 0
                }
            },
            "model_comparison": {
                "response_times": {},
                "error_rates": {},
                "token_efficiency": {}
            },
            "content_type_distribution": {
                "system_messages": 0,
                "user_messages": 0,
                "tool_calls": 0,
                "function_calls": 0
            },
            "content_trends": {
                "daily": {},
                "weekly": {}
            }
        }
        
        # Process requests
        request_models = {}
        request_dates = {}
        request_content_types = {
            "system_messages": 0,
            "user_messages": 0,
            "tool_calls": 0,
            "function_calls": 0
        }
        
        for request in requests:
            # Get model information
            model = None
            if request.data and "llm_request" in request.data:
                llm_request = request.data["llm_request"]
                if "model" in llm_request:
                    model = llm_request["model"]
            
            # Alternative locations for model info
            if not model and request.data:
                if "request" in request.data and "model" in request.data["request"]:
                    model = request.data["request"]["model"]
                elif "model" in request.data:
                    model = request.data["model"]
            
            # Default if model not found
            if not model:
                model = "unknown"
            
            # Count model usage
            if model not in request_models:
                request_models[model] = {
                    "count": 0,
                    "input_tokens": 0
                }
            
            request_models[model]["count"] += 1
            
            # Extract token usage if available
            if request.data:
                input_tokens = None
                
                # Check different locations for token count
                if "llm_request" in request.data and "usage" in request.data["llm_request"]:
                    usage = request.data["llm_request"]["usage"]
                    if "input_tokens" in usage:
                        input_tokens = usage["input_tokens"]
                    elif "prompt_tokens" in usage:
                        input_tokens = usage["prompt_tokens"]
                
                # Alternative format
                if input_tokens is None and "request" in request.data:
                    if "usage_metadata" in request.data["request"]:
                        metadata = request.data["request"]["usage_metadata"]
                        if "input_tokens" in metadata:
                            input_tokens = metadata["input_tokens"]
                
                if input_tokens is not None:
                    try:
                        input_tokens = int(input_tokens)
                        request_models[model]["input_tokens"] += input_tokens
                        results["model_usage"]["total_tokens"]["input"] += input_tokens
                    except (ValueError, TypeError):
                        pass
            
            # Get date for trends
            day = request.timestamp.strftime("%Y-%m-%d")
            week = f"{request.timestamp.year}-W{request.timestamp.isocalendar()[1]:02d}"
            
            if day not in request_dates:
                request_dates[day] = {
                    "count": 0,
                    "week": week
                }
            
            request_dates[day]["count"] += 1
            
            # Analyze content types
            if request.data and "llm_request" in request.data and "messages" in request.data["llm_request"]:
                messages = request.data["llm_request"]["messages"]
                for message in messages:
                    if isinstance(message, dict) and "role" in message:
                        if message["role"] == "system":
                            request_content_types["system_messages"] += 1
                        elif message["role"] == "user":
                            request_content_types["user_messages"] += 1
                        elif message["role"] in ["assistant", "tool"]:
                            if "function_call" in message or "tool_calls" in message:
                                request_content_types["function_calls"] += 1
                            if "tool_call_id" in message:
                                request_content_types["tool_calls"] += 1
        
        # Process responses
        response_models = {}
        response_times = {}
        response_errors = {}
        
        for response in responses:
            # Get model information
            model = None
            if response.data and "llm_output" in response.data:
                llm_output = response.data["llm_output"]
                if "model" in llm_output:
                    model = llm_output["model"]
            
            # Alternative locations for model info
            if not model and response.data:
                if "response" in response.data and "model" in response.data["response"]:
                    model = response.data["response"]["model"]
                elif "model" in response.data:
                    model = response.data["model"]
            
            # Default if model not found
            if not model:
                model = "unknown"
            
            # Count model usage
            if model not in response_models:
                response_models[model] = {
                    "count": 0,
                    "output_tokens": 0,
                    "response_times": [],
                    "error_count": 0
                }
            
            response_models[model]["count"] += 1
            
            # Extract token usage if available
            if response.data:
                output_tokens = None
                
                # Check different locations for token count
                if "llm_output" in response.data and "usage" in response.data["llm_output"]:
                    usage = response.data["llm_output"]["usage"]
                    if "output_tokens" in usage:
                        output_tokens = usage["output_tokens"]
                    elif "completion_tokens" in usage:
                        output_tokens = usage["completion_tokens"]
                
                # Alternative format
                if output_tokens is None and "response" in response.data:
                    if "usage_metadata" in response.data["response"]:
                        metadata = response.data["response"]["usage_metadata"]
                        if "output_tokens" in metadata:
                            output_tokens = metadata["output_tokens"]
                
                if output_tokens is not None:
                    try:
                        output_tokens = int(output_tokens)
                        response_models[model]["output_tokens"] += output_tokens
                        results["model_usage"]["total_tokens"]["output"] += output_tokens
                    except (ValueError, TypeError):
                        pass
            
            # Extract response time if available
            if response.data and "performance" in response.data and "duration_ms" in response.data["performance"]:
                try:
                    duration_ms = float(response.data["performance"]["duration_ms"])
                    response_models[model]["response_times"].append(duration_ms)
                except (ValueError, TypeError):
                    pass
            
            # Check for errors
            has_error = False
            if response.data:
                if "error" in response.data and response.data["error"]:
                    has_error = True
                elif "llm_output" in response.data and "error" in response.data["llm_output"] and response.data["llm_output"]["error"]:
                    has_error = True
            
            if has_error:
                response_models[model]["error_count"] += 1
        
        # Combine request and response data
        for model in set(list(request_models.keys()) + list(response_models.keys())):
            request_count = request_models.get(model, {}).get("count", 0)
            response_count = response_models.get(model, {}).get("count", 0)
            
            results["model_usage"]["models"][model] = {
                "request_count": request_count,
                "response_count": response_count,
                "input_tokens": request_models.get(model, {}).get("input_tokens", 0),
                "output_tokens": response_models.get(model, {}).get("output_tokens", 0)
            }
            
            # Calculate model comparison metrics
            response_times_list = response_models.get(model, {}).get("response_times", [])
            error_count = response_models.get(model, {}).get("error_count", 0)
            
            if response_times_list:
                avg_response_time = statistics.mean(response_times_list)
                results["model_comparison"]["response_times"][model] = avg_response_time
            
            if response_count > 0:
                error_rate = (error_count / response_count) * 100
                results["model_comparison"]["error_rates"][model] = error_rate
            
            # Calculate token efficiency (output tokens per input token)
            input_tokens = request_models.get(model, {}).get("input_tokens", 0)
            output_tokens = response_models.get(model, {}).get("output_tokens", 0)
            
            if input_tokens > 0:
                token_efficiency = output_tokens / input_tokens
                results["model_comparison"]["token_efficiency"][model] = token_efficiency
        
        # Add content type distribution
        results["content_type_distribution"] = request_content_types
        
        # Generate content trends
        daily_trends = {}
        weekly_trends = {}
        
        for day, data in request_dates.items():
            daily_trends[day] = data["count"]
            
            week = data["week"]
            if week not in weekly_trends:
                weekly_trends[week] = 0
            
            weekly_trends[week] += data["count"]
        
        results["content_trends"]["daily"] = daily_trends
        results["content_trends"]["weekly"] = weekly_trends
        
        return results


class ContentAnalyticsInsightExtractor(BaseInsightExtractor):
    """Extractor for detailed content analytics insights.
    
    Analyzes content patterns and provides insights about content characteristics.
    """
    
    def extract(self, db: Session, start_time: Optional[datetime] = None, 
               end_time: Optional[datetime] = None, 
               agent_id: Optional[str] = None,
               session_id: Optional[str] = None,
               **kwargs) -> Dict[str, Any]:
        """Extract content analytics insights.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict containing content analytics insights:
                - content_complexity: Analysis of content complexity
                - tool_usage_patterns: Patterns in tool/function usage
                - content_length_analysis: Analysis of content lengths
                - model_preferences: Model preferences by content type
        """
        # Set default time range if not provided
        if not start_time:
            # Default to last 7 days if no start time
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
        
        # Initialize results
        results = {
            "content_complexity": {
                "average_message_count": 0,
                "message_structure": {},
                "context_size_distribution": {}
            },
            "tool_usage_patterns": {
                "tool_call_frequency": {},
                "common_tool_combinations": []
            },
            "content_length_analysis": {
                "prompt_length_distribution": {},
                "response_length_distribution": {}
            },
            "model_preferences": {
                "by_content_type": {},
                "by_agent": {}
            }
        }
        
        # Analyze requests for content complexity
        message_counts = []
        message_structure = {
            "system_only": 0,
            "user_only": 0,
            "mixed_simple": 0,  # system + user
            "mixed_complex": 0,  # includes assistant/tool messages
            "with_tools": 0
        }
        context_sizes = {
            "small": 0,      # < 1000 tokens
            "medium": 0,     # 1000-3000 tokens
            "large": 0,      # 3000-7000 tokens
            "very_large": 0  # > 7000 tokens
        }
        
        # Tool usage tracking
        tool_calls = Counter()
        session_tools = defaultdict(set)
        
        # Content length tracking
        prompt_lengths = {
            "very_short": 0,  # < 100 tokens
            "short": 0,       # 100-500 tokens
            "medium": 0,      # 500-1500 tokens
            "long": 0,        # 1500-4000 tokens
            "very_long": 0    # > 4000 tokens
        }
        
        # Model preference tracking
        content_type_models = defaultdict(Counter)
        agent_models = defaultdict(Counter)
        
        for request in requests:
            # Extract messages if available
            messages = []
            if request.data and "llm_request" in request.data and "messages" in request.data["llm_request"]:
                messages = request.data["llm_request"]["messages"]
            
            # Alternative location for messages
            if not messages and request.data and "request" in request.data and "messages" in request.data["request"]:
                messages = request.data["request"]["messages"]
            
            if messages:
                # Count messages
                message_counts.append(len(messages))
                
                # Analyze message structure
                has_system = False
                has_user = False
                has_assistant = False
                has_tool = False
                has_tool_calls = False
                
                for message in messages:
                    if isinstance(message, dict) and "role" in message:
                        if message["role"] == "system":
                            has_system = True
                        elif message["role"] == "user":
                            has_user = True
                        elif message["role"] == "assistant":
                            has_assistant = True
                            if "function_call" in message or "tool_calls" in message:
                                has_tool_calls = True
                        elif message["role"] == "tool":
                            has_tool = True
                
                # Categorize message structure
                if has_tool or has_tool_calls:
                    message_structure["with_tools"] += 1
                elif has_assistant or has_tool:
                    message_structure["mixed_complex"] += 1
                elif has_system and has_user:
                    message_structure["mixed_simple"] += 1
                elif has_system:
                    message_structure["system_only"] += 1
                elif has_user:
                    message_structure["user_only"] += 1
                
                # Extract tool calls
                for message in messages:
                    if isinstance(message, dict):
                        # Check for function calls in assistant messages
                        if "role" in message and message["role"] == "assistant":
                            if "function_call" in message:
                                func_call = message["function_call"]
                                if isinstance(func_call, dict) and "name" in func_call:
                                    tool_name = func_call["name"]
                                    tool_calls[tool_name] += 1
                                    
                                    if request.session_id:
                                        session_tools[request.session_id].add(tool_name)
                            
                            if "tool_calls" in message:
                                tool_call_list = message["tool_calls"]
                                if isinstance(tool_call_list, list):
                                    for tool_call in tool_call_list:
                                        if isinstance(tool_call, dict) and "function" in tool_call and "name" in tool_call["function"]:
                                            tool_name = tool_call["function"]["name"]
                                            tool_calls[tool_name] += 1
                                            
                                            if request.session_id:
                                                session_tools[request.session_id].add(tool_name)
            
            # Analyze input tokens for context size
            input_tokens = 0
            if request.data:
                # Check different locations for token count
                if "llm_request" in request.data and "usage" in request.data["llm_request"]:
                    usage = request.data["llm_request"]["usage"]
                    if "input_tokens" in usage:
                        input_tokens = usage["input_tokens"]
                    elif "prompt_tokens" in usage:
                        input_tokens = usage["prompt_tokens"]
                
                # Alternative format
                if input_tokens == 0 and "request" in request.data:
                    if "usage_metadata" in request.data["request"]:
                        metadata = request.data["request"]["usage_metadata"]
                        if "input_tokens" in metadata:
                            input_tokens = metadata["input_tokens"]
            
            try:
                input_tokens = int(input_tokens)
                # Categorize context size
                if input_tokens < 1000:
                    context_sizes["small"] += 1
                elif input_tokens < 3000:
                    context_sizes["medium"] += 1
                elif input_tokens < 7000:
                    context_sizes["large"] += 1
                else:
                    context_sizes["very_large"] += 1
                
                # Categorize prompt length
                if input_tokens < 100:
                    prompt_lengths["very_short"] += 1
                elif input_tokens < 500:
                    prompt_lengths["short"] += 1
                elif input_tokens < 1500:
                    prompt_lengths["medium"] += 1
                elif input_tokens < 4000:
                    prompt_lengths["long"] += 1
                else:
                    prompt_lengths["very_long"] += 1
            except (ValueError, TypeError):
                pass
            
            # Get model information for content type preferences
            model = None
            if request.data and "llm_request" in request.data:
                llm_request = request.data["llm_request"]
                if "model" in llm_request:
                    model = llm_request["model"]
            
            # Alternative locations for model info
            if not model and request.data:
                if "request" in request.data and "model" in request.data["request"]:
                    model = request.data["request"]["model"]
                elif "model" in request.data:
                    model = request.data["model"]
            
            if model:
                # Determine content type
                content_type = "general"
                if has_tool or has_tool_calls:
                    content_type = "tool_use"
                elif has_assistant:
                    content_type = "conversation"
                elif has_system and not has_user:
                    content_type = "system_only"
                
                content_type_models[content_type][model] += 1
                
                if request.agent_id:
                    agent_models[request.agent_id][model] += 1
        
        # Analyze responses for content length distribution
        response_lengths = {
            "very_short": 0,  # < 50 tokens
            "short": 0,       # 50-200 tokens
            "medium": 0,      # 200-500 tokens
            "long": 0,        # 500-1000 tokens
            "very_long": 0    # > 1000 tokens
        }
        
        for response in responses:
            # Extract output tokens if available
            output_tokens = 0
            if response.data:
                # Check different locations for token count
                if "llm_output" in response.data and "usage" in response.data["llm_output"]:
                    usage = response.data["llm_output"]["usage"]
                    if "output_tokens" in usage:
                        output_tokens = usage["output_tokens"]
                    elif "completion_tokens" in usage:
                        output_tokens = usage["completion_tokens"]
                
                # Alternative format
                if output_tokens == 0 and "response" in response.data:
                    if "usage_metadata" in response.data["response"]:
                        metadata = response.data["response"]["usage_metadata"]
                        if "output_tokens" in metadata:
                            output_tokens = metadata["output_tokens"]
            
            try:
                output_tokens = int(output_tokens)
                # Categorize response length
                if output_tokens < 50:
                    response_lengths["very_short"] += 1
                elif output_tokens < 200:
                    response_lengths["short"] += 1
                elif output_tokens < 500:
                    response_lengths["medium"] += 1
                elif output_tokens < 1000:
                    response_lengths["long"] += 1
                else:
                    response_lengths["very_long"] += 1
            except (ValueError, TypeError):
                pass
        
        # Calculate average message count
        results["content_complexity"]["average_message_count"] = statistics.mean(message_counts) if message_counts else 0
        results["content_complexity"]["message_structure"] = message_structure
        results["content_complexity"]["context_size_distribution"] = context_sizes
        
        # Process tool usage patterns
        results["tool_usage_patterns"]["tool_call_frequency"] = dict(tool_calls.most_common())
        
        # Find common tool combinations
        tool_combinations = Counter()
        for session_id, tools in session_tools.items():
            if len(tools) > 1:
                tool_combination = tuple(sorted(tools))
                tool_combinations[tool_combination] += 1
        
        results["tool_usage_patterns"]["common_tool_combinations"] = [
            {"tools": list(combo), "count": count}
            for combo, count in tool_combinations.most_common(5)
        ]
        
        # Content length analysis
        results["content_length_analysis"]["prompt_length_distribution"] = prompt_lengths
        results["content_length_analysis"]["response_length_distribution"] = response_lengths
        
        # Model preferences
        for content_type, models in content_type_models.items():
            results["model_preferences"]["by_content_type"][content_type] = dict(models.most_common())
        
        for agent_id, models in agent_models.items():
            results["model_preferences"]["by_agent"][agent_id] = dict(models.most_common())
        
        return results


# Register the insight extractors
insight_registry.register(ContentUsageInsightExtractor())
insight_registry.register(ContentAnalyticsInsightExtractor()) 