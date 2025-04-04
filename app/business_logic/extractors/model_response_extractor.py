"""
ModelResponseExtractor module.

This module provides an extractor for model_response events,
which extracts token usage, performance, and content data.
"""

from typing import Dict, Any, Optional
import logging
from datetime import datetime

from app.business_logic.extractors.base import BaseExtractor, extractor_registry
from app.models.token_usage import TokenUsage
from app.models.performance_metric import PerformanceMetric
from app.models.content_analysis import ContentAnalysis
from sqlalchemy import select

# Set up logging
logger = logging.getLogger(__name__)


class ModelResponseExtractor(BaseExtractor):
    """Extractor for model_response events.
    
    Extracts token usage, performance metrics, and content data
    from model_response events.
    """
    
    def can_process(self, event) -> bool:
        """Determine if this extractor can process the given event.
        
        Args:
            event: The event to check
            
        Returns:
            True if this is a model_response event, False otherwise
        """
        return event.event_type == "model_response"
    
    async def process(self, event, db_session) -> None:
        """Process the event and extract data.
        
        Args:
            event: The event to process
            db_session: Database session for persistence
        """
        if not event.data:
            logger.warning(f"No data in model_response event {event.id}")
            return
        
        # Extract token usage
        await self._extract_token_usage(event, db_session)
        
        # Extract performance metrics
        await self._extract_performance_metrics(event, db_session)
        
        # Extract content for analysis
        await self._extract_content(event, db_session)
    
    async def _extract_token_usage(self, event, db_session) -> Optional[TokenUsage]:
        """Extract token usage data from the event.
        
        Args:
            event: The event to extract from
            db_session: Database session for persistence
            
        Returns:
            The created TokenUsage object, or None if no token usage data
        """
        try:
            # No need to check for existing token usage - event processor guarantees
            # this extractor runs exactly once per event
            
            data = event.data
            
            # Try multiple paths to handle different formats
            usage = None
            model_name = None
            
            # Check in llm_output
            if "llm_output" in data and "usage" in data["llm_output"]:
                usage = data["llm_output"]["usage"]
                model_name = data["llm_output"].get("model") or data["llm_output"].get("model_name")
            
            # Check in verbose format with message
            elif "response" in data:
                response = data["response"]
                
                # Check in llm_output within response
                if "llm_output" in response and "usage" in response["llm_output"]:
                    usage = response["llm_output"]["usage"]
                    model_name = response["llm_output"].get("model") or response["llm_output"].get("model_name")
                
                # Check in message's usage_metadata
                elif "message" in response and isinstance(response["message"], dict):
                    message = response["message"]
                    if "usage_metadata" in message:
                        usage = message["usage_metadata"]
                        if "input_token_details" in usage:
                            # Add cache details from input_token_details
                            details = usage["input_token_details"]
                            usage["cache_read_input_tokens"] = details.get("cache_read", 0)
                            usage["cache_creation_input_tokens"] = details.get("cache_creation", 0)
                
                # Check directly in response
                elif "usage" in response:
                    usage = response["usage"]
                
                # Try to extract model name
                if not model_name:
                    model_name = response.get("model") or response.get("model_name")
            
            # Look directly in data for model info
            if not model_name and "model" in data:
                if isinstance(data["model"], dict):
                    model_name = data["model"].get("name")
                else:
                    model_name = data["model"]
            
            # If we have usage data, create the token usage object
            if usage:
                input_tokens = int(usage.get("input_tokens", 0))
                output_tokens = int(usage.get("output_tokens", 0))
                total_tokens = int(usage.get("total_tokens", 0))
                
                # If total tokens not provided, calculate it
                if total_tokens == 0:
                    total_tokens = input_tokens + output_tokens
                
                # Extract cache token information
                cache_read_tokens = int(usage.get("cache_read_input_tokens", 0))
                cache_creation_tokens = int(usage.get("cache_creation_input_tokens", 0))
                
                # Create token usage object
                token_usage = TokenUsage(
                    event_id=event.id,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    cache_read_tokens=cache_read_tokens,
                    cache_creation_tokens=cache_creation_tokens,
                    model=model_name
                )
                
                # Add to session
                db_session.add(token_usage)
                logger.info(f"Extracted token usage for event {event.id}: {input_tokens} input, {output_tokens} output")
                
                return token_usage
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting token usage for event {event.id}: {str(e)}")
            return None
    
    async def _extract_performance_metrics(self, event, db_session) -> Optional[PerformanceMetric]:
        """Extract performance metrics from the event.
        
        Args:
            event: The event to extract from
            db_session: Database session for persistence
            
        Returns:
            The created PerformanceMetric object, or None if no performance data
        """
        try:
            # No need to check for existing performance metrics - event processor guarantees
            # this extractor runs exactly once per event
            
            data = event.data
            
            # Try to get performance data
            performance = data.get("performance", {})
            if not performance:
                logger.info(f"No performance data found in event {event.id}")
                return None
            
            # Extract duration
            duration_ms = performance.get("duration_ms")
            if duration_ms is not None:
                duration_ms = float(duration_ms)
            
            # Extract timestamp
            timestamp_str = performance.get("timestamp")
            timestamp = None
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except Exception as e:
                    logger.warning(f"Invalid timestamp format in event {event.id}: {timestamp_str}")
            
            # Create PerformanceMetric object
            perf_metric = PerformanceMetric(
                event_id=event.id,
                duration_ms=duration_ms,
                timestamp=timestamp
            )
            
            # Add to session
            db_session.add(perf_metric)
            logger.info(f"Extracted performance metrics for event {event.id}: duration={duration_ms}ms")
            
            return perf_metric
        except Exception as e:
            logger.error(f"Error extracting performance metrics for event {event.id}: {str(e)}")
            return None
    
    async def _extract_content(self, event, db_session) -> Optional[ContentAnalysis]:
        """Extract and analyze content from the event.
        
        Args:
            event: The event to extract from
            db_session: Database session for persistence
            
        Returns:
            The created ContentAnalysis object, or None if no content
        """
        try:
            # No need to check for existing content - event processor guarantees
            # this extractor runs exactly once per event
            
            data = event.data
            
            # Try to get response content
            response = data.get("response", {})
            if not response:
                logger.info(f"No response content found in event {event.id}")
                return None
            
            # Extract text content - handle different formats
            content_text = None
            
            # Format 1: response.text with tuple format - very common format
            if "text" in response:
                text = response["text"]
                if isinstance(text, str):
                    if text.startswith("('text', "):
                        # Parse the tuple-like string: ('text', "actual content")
                        try:
                            import re
                            # Use regex to extract content between first set of quotes after ('text',
                            match = re.search(r"\('text', [\"'](.*)[\"']\)", text, re.DOTALL)
                            if match:
                                content_text = match.group(1)
                            else:
                                # Try another approach - find first quote after ('text',
                                quote_start = text.find('"', text.find("('text',"))
                                if quote_start > 0:
                                    quote_end = text.rfind('")')
                                    if quote_end > quote_start:
                                        content_text = text[quote_start+1:quote_end]
                                    else:
                                        content_text = text[quote_start+1:]
                        except Exception as e:
                            logger.warning(f"Failed to parse tuple format: {e}")
                            content_text = text  # Fallback to using the raw text
                    else:
                        content_text = text
            
            # Format 2: response.message.content
            if not content_text and "message" in response:
                message = response["message"]
                if isinstance(message, dict) and "content" in message:
                    content_text = message["content"]
                elif isinstance(message, str) and "content" in message:
                    # Try to extract content from string representation of a message
                    try:
                        import re
                        match = re.search(r"content=[\"']([^\"']+)[\"']", message)
                        if match:
                            content_text = match.group(1)
                    except Exception:
                        pass
            
            if not content_text:
                logger.info(f"No content text found in event {event.id}")
                return None
            
            # Basic content analysis - word count
            word_count = len(content_text.split())
            
            # Create ContentAnalysis object
            content_analysis = ContentAnalysis(
                event_id=event.id,
                content_type="text",
                content_text=content_text[:1000],  # Limit to 1000 chars
                word_count=word_count,
                sentiment_score=None,  # Could add sentiment analysis in future
                toxicity_score=None    # Could add toxicity analysis in future
            )
            
            # Add to session
            db_session.add(content_analysis)
            logger.info(f"Extracted content for event {event.id}: {word_count} words")
            
            return content_analysis
        except Exception as e:
            logger.error(f"Error extracting content for event {event.id}: {str(e)}")
            return None


# Register the extractor
extractor_registry.register(ModelResponseExtractor()) 