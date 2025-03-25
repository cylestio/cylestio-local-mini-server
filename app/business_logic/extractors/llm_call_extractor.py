"""
LLMCallExtractor module.

This module extracts information from LLM_call_start and LLM_call_finish events.
"""

import logging
from typing import Dict, Any, Optional, List

from app.models.model_details import ModelDetails
from app.models.token_usage import TokenUsage
from app.models.performance_metric import PerformanceMetric
from app.models.security_alert import SecurityAlert
from app.business_logic.extractors.base import BaseExtractor, extractor_registry
from sqlalchemy import select

# Set up logging
logger = logging.getLogger(__name__)


class LLMCallExtractor(BaseExtractor):
    """Extractor for LLM call events.
    
    Extracts information from LLM_call_start and LLM_call_finish events
    including performance metrics, token usage, and model details.
    """
    
    def can_process(self, event) -> bool:
        """Determine if this extractor can process the given event.
        
        Args:
            event: The event to check
            
        Returns:
            True if this is an LLM call event, False otherwise
        """
        return event.event_type in ["LLM_call_start", "LLM_call_finish", "LLM_call_blocked"]
    
    async def process(self, event, db_session) -> None:
        """Process the event and extract data.
        
        Args:
            event: The event to process
            db_session: Database session for persistence
        """
        if not event.data:
            logger.warning(f"No data in LLM call event {event.id}")
            return
        
        # Different processing based on event type
        if event.event_type == "LLM_call_start":
            # Extract model details for start events
            await self._extract_model_details(event, db_session)
            
            # Extract security alerts from start events
            await self._extract_security_alert(event, db_session)
        
        elif event.event_type == "LLM_call_finish":
            # Extract token usage from finish events
            await self._extract_token_usage(event, db_session)
            
            # Extract performance metrics from finish events
            await self._extract_performance_metrics(event, db_session)
            
            # Extract model details from finish events
            await self._extract_model_details(event, db_session)
            
        elif event.event_type == "LLM_call_blocked":
            # Extract security alerts from blocked events
            await self._extract_security_alert(event, db_session)
            
            # Extract model details if available
            await self._extract_model_details(event, db_session)
    
    async def _extract_model_details(self, event, db_session) -> Optional[ModelDetails]:
        """Extract model details from the event.
        
        Args:
            event: The event to extract from
            db_session: Database session for persistence
            
        Returns:
            The created ModelDetails object or None if no data
        """
        try:
            # Check if model details already exist for this event
            result = await db_session.execute(
                select(ModelDetails).where(ModelDetails.event_id == event.id)
            )
            existing_model_details = result.scalars().first()
            
            if existing_model_details:
                logger.info(f"Model details already exist for event {event.id}, skipping extraction")
                return existing_model_details
                
            # Base model data
            model_name = None
            model_provider = None
            model_version = None
            model_type = "chat"  # Default to chat model
            
            # For start events, check in method and prompt
            if event.event_type == "LLM_call_start":
                # Method may indicate provider (e.g., openai.chat.completions)
                if "method" in event.data:
                    method = event.data.get("method", "")
                    if "openai" in method.lower():
                        model_provider = "OpenAI"
                    elif "anthropic" in method.lower():
                        model_provider = "Anthropic"
                    elif "cohere" in method.lower():
                        model_provider = "Cohere"
                    
                # Prompt may contain model information
                if "prompt" in event.data and isinstance(event.data["prompt"], list):
                    # Check if model is specified in the first message
                    prompt_data = event.data["prompt"]
                    if prompt_data and isinstance(prompt_data[-1], dict) and "model" in prompt_data[-1]:
                        model_name = prompt_data[-1]["model"]
            
            # For finish events, check in response
            elif event.event_type == "LLM_call_finish":
                if "response" in event.data:
                    response = event.data["response"]
                    
                    # Extract model name
                    model_name = response.get("model")
                    
                    # Extract model type from response structure
                    if "content" in response and isinstance(response["content"], list):
                        model_type = "chat"
                    elif "text" in response:
                        model_type = "completion"
                    
                    # Try to determine provider from model name
                    if model_name:
                        if "gpt" in model_name.lower():
                            model_provider = "OpenAI"
                        elif "claude" in model_name.lower():
                            model_provider = "Anthropic"
                        elif "command" in model_name.lower():
                            model_provider = "Cohere"
            
            # If we have model information, create the object
            if model_name or model_provider:
                model_details = ModelDetails(
                    event_id=event.id,
                    model_name=model_name,
                    model_provider=model_provider,
                    model_version=model_version,
                    model_type=model_type
                )
                
                # Add to session
                db_session.add(model_details)
                logger.info(f"Extracted model details for event {event.id}: {model_name} ({model_provider})")
                
                return model_details
            
            return None
        except Exception as e:
            logger.error(f"Error extracting model details for event {event.id}: {str(e)}")
            return None
    
    async def _extract_token_usage(self, event, db_session) -> Optional[TokenUsage]:
        """Extract token usage data from LLM_call_finish events.
        
        Args:
            event: The event to extract from
            db_session: Database session for persistence
            
        Returns:
            The created TokenUsage object or None if no data
        """
        try:
            # Only process finish events
            if event.event_type != "LLM_call_finish":
                return None
                
            # Check if token usage already exists for this event
            result = await db_session.execute(
                select(TokenUsage).where(TokenUsage.event_id == event.id)
            )
            existing_token_usage = result.scalars().first()
            
            if existing_token_usage:
                logger.info(f"Token usage already exists for event {event.id}, skipping extraction")
                return existing_token_usage
                
            data = event.data
            input_tokens = 0
            output_tokens = 0
            total_tokens = 0
            cache_read_tokens = 0
            cache_creation_tokens = 0
            model = None
            
            # Extract model information from multiple possible locations
            if "model" in data:
                if isinstance(data["model"], dict) and "name" in data["model"]:
                    model = data["model"]["name"]
                else:
                    model = data["model"]
            elif "response" in data and "model" in data["response"]:
                model = data["response"]["model"]
            elif "response" in data and "model_name" in data["response"]:
                model = data["response"]["model_name"]
            
            # Extract token data from response
            if "response" in data and "usage" in data["response"]:
                usage_data = data["response"]["usage"]
                
                # Handle different field naming patterns
                input_tokens = int(usage_data.get("input_tokens", 
                    usage_data.get("prompt_tokens", 0)))
                    
                output_tokens = int(usage_data.get("output_tokens", 
                    usage_data.get("completion_tokens", 0)))
                    
                total_tokens = int(usage_data.get("total_tokens", 0))
                
                # Some providers provide cache information
                cache_read_tokens = int(usage_data.get("cache_read_input_tokens", 0))
                cache_creation_tokens = int(usage_data.get("cache_creation_input_tokens", 0))
            
            # Try direct token_usage in the data
            elif "token_usage" in data:
                usage_data = data["token_usage"]
                input_tokens = int(usage_data.get("input_tokens", 0))
                output_tokens = int(usage_data.get("output_tokens", 0))
                total_tokens = int(usage_data.get("total_tokens", 0))
            
            # Look for usage data in llm_output
            elif "llm_output" in data and "usage" in data["llm_output"]:
                usage_data = data["llm_output"]["usage"]
                input_tokens = int(usage_data.get("input_tokens", 0))
                output_tokens = int(usage_data.get("output_tokens", 0))
                total_tokens = int(usage_data.get("total_tokens", 0))
                
                if not model and "model" in data["llm_output"]:
                    model = data["llm_output"]["model"]
            
            # If we found token data, create the object
            if input_tokens > 0 or output_tokens > 0:
                # Calculate total tokens if not provided
                if total_tokens == 0:
                    total_tokens = input_tokens + output_tokens
                
                # Create and store token usage object
                token_usage = TokenUsage(
                    event_id=event.id,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    cache_read_tokens=cache_read_tokens,
                    cache_creation_tokens=cache_creation_tokens,
                    model=model
                )
                
                db_session.add(token_usage)
                logger.info(f"Extracted token usage for event {event.id}: {total_tokens} tokens")
                
                return token_usage
                
            return None
                
        except Exception as e:
            logger.error(f"Error extracting token usage for event {event.id}: {str(e)}")
            return None
    
    async def _extract_performance_metrics(self, event, db_session) -> Optional[PerformanceMetric]:
        """Extract performance metrics from LLM_call_finish events.
        
        Args:
            event: The event to extract from
            db_session: Database session for persistence
            
        Returns:
            The created PerformanceMetric object or None if no data
        """
        try:
            # Only process finish events
            if event.event_type != "LLM_call_finish":
                return None
                
            # Check if performance metrics already exist for this event
            result = await db_session.execute(
                select(PerformanceMetric).where(PerformanceMetric.event_id == event.id)
            )
            existing_performance_metric = result.scalars().first()
            
            if existing_performance_metric:
                logger.info(f"Performance metrics already exist for event {event.id}, skipping extraction")
                return existing_performance_metric
                
            data = event.data
            duration_ms = None
            
            # Check if duration is in the data
            if "duration" in data:
                duration_ms = float(data.get("duration", 0)) * 1000  # Convert to ms
                
            # Check for dedicated performance field
            elif "performance" in data:
                perf_data = data["performance"]
                if isinstance(perf_data, dict) and "duration_ms" in perf_data:
                    duration_str = perf_data["duration_ms"]
                    # Handle both string and float formats
                    duration_ms = float(duration_str) if isinstance(duration_str, str) else duration_str
            
            # If we found duration data, create the object
            if duration_ms is not None and duration_ms > 0:
                performance_metric = PerformanceMetric(
                    event_id=event.id,
                    duration_ms=duration_ms,
                    timestamp=event.timestamp
                )
                
                db_session.add(performance_metric)
                logger.info(f"Extracted performance metrics for event {event.id}: {duration_ms}ms")
                
                return performance_metric
                
            return None
        except Exception as e:
            logger.error(f"Error extracting performance metrics from event {event.id}: {str(e)}")
            return None
    
    async def _extract_security_alert(self, event, db_session) -> Optional[SecurityAlert]:
        """Extract security alert data from LLM_call_start events.
        
        Args:
            event: The event to extract from
            db_session: Database session for persistence
            
        Returns:
            The created SecurityAlert object or None if no data
        """
        try:
            # Skip if alert is explicitly "none"
            if hasattr(event, 'alert') and event.alert and event.alert.lower() == "none":
                return None
                
            data = event.data
            
            # Skip if data contains alert="none"
            if data and "alert" in data and data["alert"].lower() == "none":
                return None
                
            # Check if security alert already exists for this event
            result = await db_session.execute(
                select(SecurityAlert).where(SecurityAlert.event_id == event.id)
            )
            existing_security_alert = result.scalars().first()
            
            if existing_security_alert:
                logger.info(f"Security alert already exists for event {event.id}, skipping extraction")
                return existing_security_alert
            
            alert_type = None
            severity = "low"
            description = None
            
            # Check for alert in event data
            if "alert" in data:
                alert_type = data["alert"]
                
                # Determine severity based on alert type
                if alert_type.lower() == "dangerous":
                    severity = "high"
                    description = "Potentially harmful content detected"
                elif alert_type.lower() == "suspicious":
                    severity = "medium"
                    description = "Suspicious pattern detected"
                else:
                    description = f"Alert: {alert_type}"
            
            # If we have an alert, create the object
            if alert_type:
                security_alert = SecurityAlert(
                    event_id=event.id,
                    alert_type=alert_type,
                    severity=severity,
                    description=description,
                    timestamp=event.timestamp
                )
                
                db_session.add(security_alert)
                logger.info(f"Extracted security alert for event {event.id}: {alert_type} ({severity})")
                
                return security_alert
                
            return None
        except Exception as e:
            logger.error(f"Error extracting security alert from event {event.id}: {str(e)}")
            return None


# Register the extractor
extractor_registry.register(LLMCallExtractor()) 