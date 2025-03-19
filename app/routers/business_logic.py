"""
Business logic API router.

This module provides API endpoints for accessing extracted data and
metrics from the business logic layer.
"""

from fastapi import APIRouter, Depends, Query, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from app.database.init_db import get_session
from app.business_logic.event_processor import EventProcessor
from app.models.event import Event
from app.models.token_usage import TokenUsage
from app.models.performance_metric import PerformanceMetric
from app.models.security_alert import SecurityAlert
from app.models.content_analysis import ContentAnalysis
from app.models.framework_details import FrameworkDetails

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/business-logic",
    tags=["Business Logic"],
    responses={404: {"description": "Not found"}},
)


@router.get("/process-events")
async def process_events(
    limit: int = Query(100, description="Maximum number of events to process"),
    db: AsyncSession = Depends(get_session)
):
    """Process unprocessed events through the business logic layer.
    
    Args:
        limit: Maximum number of events to process
        db: Database session
        
    Returns:
        Number of events processed
    """
    # Create processor
    processor = EventProcessor()
    
    # Query unprocessed events
    result = await db.execute(
        select(Event).where(Event.is_processed == False).limit(limit)
    )
    events = result.scalars().all()
    
    if not events:
        return {"message": "No unprocessed events found", "processed_count": 0}
    
    # Process events
    processed_count = 0
    for event in events:
        try:
            await processor.process_event(event, db)
            processed_count += 1
        except Exception as e:
            # Log the error but continue processing other events
            pass
    
    return {
        "message": f"Processed {processed_count} events",
        "processed_count": processed_count,
        "total_events": len(events)
    }


@router.get("/token-usage/{agent_id}")
async def get_token_usage(
    agent_id: str = Path(..., description="The agent ID to get token usage for"),
    start_time: Optional[datetime] = Query(None, description="Start time for events"),
    end_time: Optional[datetime] = Query(None, description="End time for events"),
    db: AsyncSession = Depends(get_session)
):
    """Get token usage for an agent.
    
    Args:
        agent_id: The agent ID to get token usage for
        start_time: Start time for events
        end_time: End time for events
        db: Database session
        
    Returns:
        Token usage metrics
    """
    # Build the query
    query = select(TokenUsage).join(Event).where(Event.agent_id == agent_id)
    
    if start_time:
        query = query.where(Event.timestamp >= start_time)
    
    if end_time:
        query = query.where(Event.timestamp <= end_time)
    
    # Execute query
    result = await db.execute(query)
    token_usages = result.scalars().all()
    
    if not token_usages:
        return {
            "agent_id": agent_id,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "event_count": 0
        }
    
    # Calculate metrics
    total_input_tokens = sum(usage.input_tokens for usage in token_usages)
    total_output_tokens = sum(usage.output_tokens for usage in token_usages)
    total_tokens = total_input_tokens + total_output_tokens
    
    return {
        "agent_id": agent_id,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_tokens": total_tokens,
        "event_count": len(token_usages)
    }


@router.get("/performance/{agent_id}")
async def get_performance_metrics(
    agent_id: str = Path(..., description="The agent ID to get performance metrics for"),
    start_time: Optional[datetime] = Query(None, description="Start time for events"),
    end_time: Optional[datetime] = Query(None, description="End time for events"),
    db: AsyncSession = Depends(get_session)
):
    """Get performance metrics for an agent.
    
    Args:
        agent_id: The agent ID to get performance metrics for
        start_time: Start time for events
        end_time: End time for events
        db: Database session
        
    Returns:
        Performance metrics
    """
    # Build the query
    query = select(PerformanceMetric).join(Event).where(Event.agent_id == agent_id)
    
    if start_time:
        query = query.where(Event.timestamp >= start_time)
    
    if end_time:
        query = query.where(Event.timestamp <= end_time)
    
    # Execute query
    result = await db.execute(query)
    metrics = result.scalars().all()
    
    if not metrics:
        return {
            "agent_id": agent_id,
            "event_count": 0,
            "avg_duration_ms": None,
            "min_duration_ms": None,
            "max_duration_ms": None
        }
    
    # Calculate metrics - filter out None values for duration
    durations = [m.duration_ms for m in metrics if m.duration_ms is not None]
    
    if not durations:
        return {
            "agent_id": agent_id,
            "event_count": len(metrics),
            "avg_duration_ms": None,
            "min_duration_ms": None,
            "max_duration_ms": None
        }
    
    avg_duration = sum(durations) / len(durations)
    min_duration = min(durations)
    max_duration = max(durations)
    
    return {
        "agent_id": agent_id,
        "event_count": len(metrics),
        "avg_duration_ms": avg_duration,
        "min_duration_ms": min_duration,
        "max_duration_ms": max_duration
    }


@router.get("/security-alerts/{agent_id}")
async def get_security_alerts(
    agent_id: str = Path(..., description="The agent ID to get security alerts for"),
    start_time: Optional[datetime] = Query(None, description="Start time for events"),
    end_time: Optional[datetime] = Query(None, description="End time for events"),
    db: AsyncSession = Depends(get_session)
):
    """Get security alerts for an agent.
    
    Args:
        agent_id: The agent ID to get security alerts for
        start_time: Start time for events
        end_time: End time for events
        db: Database session
        
    Returns:
        Security alerts
    """
    # Build the query
    query = select(SecurityAlert).join(Event).where(Event.agent_id == agent_id)
    
    if start_time:
        query = query.where(Event.timestamp >= start_time)
    
    if end_time:
        query = query.where(Event.timestamp <= end_time)
    
    # Execute query
    result = await db.execute(query)
    alerts = result.scalars().all()
    
    # Count alerts by level
    alert_counts = {}
    for alert in alerts:
        level = alert.alert_level
        if level not in alert_counts:
            alert_counts[level] = 0
        alert_counts[level] += 1
    
    return {
        "agent_id": agent_id,
        "alert_count": len(alerts),
        "alert_levels": alert_counts,
        "alerts": [
            {
                "id": alert.id,
                "event_id": alert.event_id, 
                "alert_level": alert.alert_level,
                "field_path": alert.field_path,
                "description": alert.description
            }
            for alert in alerts[:100]  # Limit to 100 alerts in response
        ]
    }


@router.get("/content-analysis/{agent_id}")
async def get_content_analysis(
    agent_id: str = Path(..., description="The agent ID to get content analysis for"),
    start_time: Optional[datetime] = Query(None, description="Start time for events"),
    end_time: Optional[datetime] = Query(None, description="End time for events"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    db: AsyncSession = Depends(get_session)
):
    """Get content analysis for an agent.
    
    Args:
        agent_id: The agent ID to get content analysis for
        start_time: Start time for events
        end_time: End time for events
        content_type: Filter by content type
        db: Database session
        
    Returns:
        Content analysis results
    """
    # Build the query
    query = select(ContentAnalysis).join(Event).where(Event.agent_id == agent_id)
    
    if start_time:
        query = query.where(Event.timestamp >= start_time)
    
    if end_time:
        query = query.where(Event.timestamp <= end_time)
    
    if content_type:
        query = query.where(ContentAnalysis.content_type == content_type)
    
    # Execute query
    result = await db.execute(query)
    analyses = result.scalars().all()
    
    if not analyses:
        return {
            "agent_id": agent_id,
            "content_count": 0,
            "avg_word_count": None,
            "content_types": {}
        }
    
    # Calculate metrics
    word_counts = [a.word_count for a in analyses if a.word_count is not None]
    avg_word_count = sum(word_counts) / len(word_counts) if word_counts else None
    
    # Count by content type
    content_types = {}
    for analysis in analyses:
        c_type = analysis.content_type
        if c_type not in content_types:
            content_types[c_type] = 0
        content_types[c_type] += 1
    
    return {
        "agent_id": agent_id,
        "content_count": len(analyses),
        "avg_word_count": avg_word_count,
        "content_types": content_types,
        "sample_content": [
            {
                "id": analysis.id,
                "event_id": analysis.event_id,
                "content_type": analysis.content_type,
                "word_count": analysis.word_count,
                "preview": analysis.content_text[:100] + "..." if analysis.content_text and len(analysis.content_text) > 100 else analysis.content_text
            }
            for analysis in analyses[:10]  # Limit to 10 content samples
        ]
    }


@router.get("/frameworks/{agent_id}")
async def get_framework_details(
    agent_id: str = Path(..., description="The agent ID to get framework details for"),
    start_time: Optional[datetime] = Query(None, description="Start time for events"),
    end_time: Optional[datetime] = Query(None, description="End time for events"),
    framework_name: Optional[str] = Query(None, description="Filter by framework name"),
    db: AsyncSession = Depends(get_session)
):
    """Get framework details for an agent.
    
    Args:
        agent_id: The agent ID to get framework details for
        start_time: Start time for events
        end_time: End time for events
        framework_name: Filter by framework name
        db: Database session
        
    Returns:
        Framework details and usage statistics
    """
    # Build the query
    query = select(FrameworkDetails).join(Event).where(Event.agent_id == agent_id)
    
    if start_time:
        query = query.where(Event.timestamp >= start_time)
    
    if end_time:
        query = query.where(Event.timestamp <= end_time)
    
    if framework_name:
        query = query.where(FrameworkDetails.framework_name == framework_name)
    
    # Execute query
    result = await db.execute(query)
    frameworks = result.scalars().all()
    
    if not frameworks:
        return {
            "agent_id": agent_id,
            "framework_count": 0,
            "frameworks": {}
        }
    
    # Count by framework name and version
    framework_counts = {}
    component_counts = {}
    
    for fw in frameworks:
        # Count frameworks
        name = fw.framework_name
        version = fw.framework_version or "unknown"
        
        if name not in framework_counts:
            framework_counts[name] = {}
        
        if version not in framework_counts[name]:
            framework_counts[name][version] = 0
        
        framework_counts[name][version] += 1
        
        # Count components
        if fw.component_name:
            component = fw.component_name
            if component not in component_counts:
                component_counts[component] = 0
            component_counts[component] += 1
    
    return {
        "agent_id": agent_id,
        "framework_count": len(frameworks),
        "frameworks": framework_counts,
        "components": component_counts,
        "details": [
            {
                "id": fw.id,
                "event_id": fw.event_id,
                "framework_name": fw.framework_name,
                "framework_version": fw.framework_version,
                "component_name": fw.component_name,
                "component_type": fw.component_type
            }
            for fw in frameworks[:10]  # Limit to 10 framework details
        ]
    }


@router.get("/dashboard-metrics/{agent_id}")
async def get_dashboard_metrics(
    agent_id: str = Path(..., description="The agent ID to get metrics for"),
    start_time: Optional[datetime] = Query(None, description="Start time for events"),
    end_time: Optional[datetime] = Query(None, description="End time for events"),
    db: AsyncSession = Depends(get_session)
):
    """Get all metrics needed for the dashboard for an agent.
    
    This endpoint provides a consolidated view of all metrics for the dashboard.
    
    Args:
        agent_id: The agent ID to get metrics for
        start_time: Start time for events
        end_time: End time for events
        db: Database session
        
    Returns:
        Combined metrics for dashboard visualization
    """
    # Get token usage
    token_query = select(TokenUsage).join(Event).where(Event.agent_id == agent_id)
    
    if start_time:
        token_query = token_query.where(Event.timestamp >= start_time)
    
    if end_time:
        token_query = token_query.where(Event.timestamp <= end_time)
    
    token_result = await db.execute(token_query)
    token_usages = token_result.scalars().all()
    
    # Get performance metrics
    perf_query = select(PerformanceMetric).join(Event).where(Event.agent_id == agent_id)
    
    if start_time:
        perf_query = perf_query.where(Event.timestamp >= start_time)
    
    if end_time:
        perf_query = perf_query.where(Event.timestamp <= end_time)
    
    perf_result = await db.execute(perf_query)
    performance_metrics = perf_result.scalars().all()
    
    # Get security alerts
    alert_query = select(SecurityAlert).join(Event).where(Event.agent_id == agent_id)
    
    if start_time:
        alert_query = alert_query.where(Event.timestamp >= start_time)
    
    if end_time:
        alert_query = alert_query.where(Event.timestamp <= end_time)
    
    alert_result = await db.execute(alert_query)
    alerts = alert_result.scalars().all()
    
    # Calculate token metrics
    total_input_tokens = sum(usage.input_tokens for usage in token_usages)
    total_output_tokens = sum(usage.output_tokens for usage in token_usages)
    total_tokens = total_input_tokens + total_output_tokens
    
    # Calculate performance metrics
    durations = [m.duration_ms for m in performance_metrics if m.duration_ms is not None]
    avg_duration = sum(durations) / len(durations) if durations else None
    min_duration = min(durations) if durations else None
    max_duration = max(durations) if durations else None
    
    # Count security alerts by level
    alert_counts = {}
    for alert in alerts:
        level = alert.alert_level
        if level not in alert_counts:
            alert_counts[level] = 0
        alert_counts[level] += 1
    
    return {
        "agent_id": agent_id,
        "token_usage": {
            "total_tokens": total_tokens,
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "count": len(token_usages)
        },
        "performance": {
            "avg_duration_ms": avg_duration,
            "min_duration_ms": min_duration,
            "max_duration_ms": max_duration,
            "count": len(performance_metrics)
        },
        "security": {
            "alert_count": len(alerts),
            "alert_levels": alert_counts
        }
    }


@router.post("/process-all-events")
async def process_all_events(
    batch_size: int = Query(100, description="Number of events to process in each batch"),
    db: AsyncSession = Depends(get_session)
):
    """Process all historical events that haven't been processed yet.
    
    This is useful for processing events that were ingested before the business logic
    layer was added or if the business logic processing failed previously.
    
    Args:
        batch_size: Number of events to process in each batch
        db: Database session
        
    Returns:
        Number of events processed
    """
    # Create processor
    processor = EventProcessor()
    
    total_processed = 0
    continue_processing = True
    
    while continue_processing:
        # Query a batch of unprocessed events
        result = await db.execute(
            select(Event)
            .where(Event.is_processed == False)
            .limit(batch_size)
        )
        events = result.scalars().all()
        
        if not events:
            # No more events to process
            continue_processing = False
            break
        
        # Process events
        processed_count = 0
        for event in events:
            try:
                await processor.process_event(event, db)
                processed_count += 1
            except Exception as e:
                # Log the error but continue processing other events
                logger.error(f"Error processing event {event.id}: {str(e)}")
        
        total_processed += processed_count
        
        # If we processed fewer events than the batch size, we're done
        if processed_count < batch_size:
            continue_processing = False
    
    return {
        "message": f"Processed {total_processed} historical events",
        "processed_count": total_processed
    } 