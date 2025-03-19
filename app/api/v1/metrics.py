from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_, case, extract
from typing import List, Optional
from datetime import datetime, timedelta

from app.database.init_db import get_session
from app.models.event import Event
from app.models.agent import Agent

router = APIRouter()

@router.get("/{agent_id}/metrics", response_model=dict)
async def get_agent_metrics(
    agent_id: str,
    metric_type: str = Query("performance", description="Type of metrics to retrieve (performance, usage, errors)"),
    start_time: Optional[str] = Query(None, description="Start time in ISO format"),
    end_time: Optional[str] = Query(None, description="End time in ISO format"),
    interval: str = Query("hour", description="Interval for time-series data (minute, hour, day)"),
    session: AsyncSession = Depends(get_session)
):
    """
    Get performance metrics for a specific agent.
    
    Provides various metrics such as response times, throughput, error rates, etc.
    """
    # Verify agent exists
    agent_result = await session.execute(
        select(Agent).where(Agent.agent_id == agent_id)
    )
    agent = agent_result.scalars().first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID '{agent_id}' not found"
        )
    
    # Determine time range if not provided
    if not end_time:
        end_datetime = datetime.now()
    else:
        end_datetime = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    
    if not start_time:
        # Default to 24 hours before end time
        start_datetime = end_datetime - timedelta(days=1)
    else:
        start_datetime = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    
    # Handle different metric types
    if metric_type == "performance":
        return await get_performance_metrics(session, agent_id, start_datetime, end_datetime, interval)
    elif metric_type == "usage":
        return await get_usage_metrics(session, agent_id, start_datetime, end_datetime, interval)
    elif metric_type == "errors":
        return await get_error_metrics(session, agent_id, start_datetime, end_datetime, interval)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid metric_type: {metric_type}"
        )

async def get_performance_metrics(
    session: AsyncSession, 
    agent_id: str, 
    start_time: datetime, 
    end_time: datetime,
    interval: str
):
    """Get performance metrics like response times and latency."""
    
    # Determine the time grouping based on interval
    if interval == "minute":
        time_extract = [
            extract('year', Event.timestamp),
            extract('month', Event.timestamp),
            extract('day', Event.timestamp),
            extract('hour', Event.timestamp),
            extract('minute', Event.timestamp)
        ]
        format_str = "%Y-%m-%d %H:%M:00"
    elif interval == "hour":
        time_extract = [
            extract('year', Event.timestamp),
            extract('month', Event.timestamp),
            extract('day', Event.timestamp),
            extract('hour', Event.timestamp)
        ]
        format_str = "%Y-%m-%d %H:00:00"
    else:  # day
        time_extract = [
            extract('year', Event.timestamp),
            extract('month', Event.timestamp),
            extract('day', Event.timestamp)
        ]
        format_str = "%Y-%m-%d 00:00:00"
    
    # Query for average response times over time
    response_time_query = select(
        *time_extract,
        func.avg(Event.duration_ms).label("avg_duration"),
        func.min(Event.duration_ms).label("min_duration"),
        func.max(Event.duration_ms).label("max_duration")
    ).where(
        Event.agent_id == agent_id,
        Event.timestamp.between(start_time, end_time),
        Event.event_type.in_(["model_response", "LLM_call_finish"]),
        Event.duration_ms.isnot(None)
    ).group_by(*time_extract).order_by(*time_extract)
    
    response_time_result = await session.execute(response_time_query)
    
    # Process the time-series data
    response_times = []
    for row in response_time_result:
        # Create a timestamp from the extracted components
        if interval == "minute":
            ts = datetime(int(row[0]), int(row[1]), int(row[2]), int(row[3]), int(row[4]))
        elif interval == "hour":
            ts = datetime(int(row[0]), int(row[1]), int(row[2]), int(row[3]))
        else:  # day
            ts = datetime(int(row[0]), int(row[1]), int(row[2]))
            
        response_times.append({
            "timestamp": ts.strftime(format_str),
            "avg_ms": round(row.avg_duration, 2),
            "min_ms": round(row.min_duration, 2),
            "max_ms": round(row.max_duration, 2)
        })
    
    # Get overall performance stats - simpler query without percentile functions which SQLite doesn't support
    overall_query = select(
        func.avg(Event.duration_ms).label("avg_duration"),
        func.min(Event.duration_ms).label("min_duration"),
        func.max(Event.duration_ms).label("max_duration"),
        func.count().label("count")
    ).where(
        Event.agent_id == agent_id,
        Event.timestamp.between(start_time, end_time),
        Event.event_type.in_(["model_response", "LLM_call_finish"]),
        Event.duration_ms.isnot(None)
    )
    
    overall_result = await session.execute(overall_query)
    overall_stats = overall_result.first()
    
    # If no data is available, provide defaults
    if not overall_stats or not overall_stats.count:
        overall_metrics = {
            "avg_response_time_ms": 0,
            "min_response_time_ms": 0,
            "max_response_time_ms": 0,
            "p95_response_time_ms": 0,
            "p99_response_time_ms": 0,
            "total_responses": 0
        }
    else:
        # For SQLite compatibility, we'll calculate a rough estimate for p95 and p99
        # by using 95% and 99% of the range between min and max
        min_val = overall_stats.min_duration or 0
        max_val = overall_stats.max_duration or 0
        p95_estimate = min_val + (max_val - min_val) * 0.95
        p99_estimate = min_val + (max_val - min_val) * 0.99
        
        overall_metrics = {
            "avg_response_time_ms": round(overall_stats.avg_duration, 2),
            "min_response_time_ms": round(overall_stats.min_duration, 2),
            "max_response_time_ms": round(overall_stats.max_duration, 2),
            "p95_response_time_ms": round(p95_estimate, 2),
            "p99_response_time_ms": round(p99_estimate, 2),
            "total_responses": overall_stats.count
        }
    
    return {
        "metrics": {
            "type": "performance",
            "overall": overall_metrics,
            "time_series": response_times
        },
        "timeframe": {
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "interval": interval
        }
    }

async def get_usage_metrics(
    session: AsyncSession, 
    agent_id: str, 
    start_time: datetime, 
    end_time: datetime,
    interval: str
):
    """Get usage metrics like request counts and throughput."""
    
    # Determine the time grouping based on interval
    if interval == "minute":
        time_extract = [
            extract('year', Event.timestamp),
            extract('month', Event.timestamp),
            extract('day', Event.timestamp),
            extract('hour', Event.timestamp),
            extract('minute', Event.timestamp)
        ]
        format_str = "%Y-%m-%d %H:%M:00"
    elif interval == "hour":
        time_extract = [
            extract('year', Event.timestamp),
            extract('month', Event.timestamp),
            extract('day', Event.timestamp),
            extract('hour', Event.timestamp)
        ]
        format_str = "%Y-%m-%d %H:00:00"
    else:  # day
        time_extract = [
            extract('year', Event.timestamp),
            extract('month', Event.timestamp),
            extract('day', Event.timestamp)
        ]
        format_str = "%Y-%m-%d 00:00:00"
    
    # Query for event counts by type over time
    usage_query = select(
        *time_extract,
        Event.event_type,
        func.count().label("count")
    ).where(
        Event.agent_id == agent_id,
        Event.timestamp.between(start_time, end_time)
    ).group_by(*time_extract, Event.event_type).order_by(*time_extract)
    
    usage_result = await session.execute(usage_query)
    
    # Process the time-series data
    # First, create a map of timestamp -> {event_type: count}
    timeseries_map = {}
    event_types = set()
    
    for row in usage_result:
        # Create a timestamp from the extracted components
        if interval == "minute":
            ts = datetime(int(row[0]), int(row[1]), int(row[2]), int(row[3]), int(row[4]))
        elif interval == "hour":
            ts = datetime(int(row[0]), int(row[1]), int(row[2]), int(row[3]))
        else:  # day
            ts = datetime(int(row[0]), int(row[1]), int(row[2]))
            
        ts_str = ts.strftime(format_str)
        event_type = row.event_type
        count = row.count
        
        event_types.add(event_type)
        
        if ts_str not in timeseries_map:
            timeseries_map[ts_str] = {"timestamp": ts_str}
        
        timeseries_map[ts_str][event_type] = count
    
    # Convert the map to a list
    usage_timeseries = list(timeseries_map.values())
    
    # Ensure each entry has all event types (with 0 as default)
    for entry in usage_timeseries:
        for event_type in event_types:
            if event_type not in entry:
                entry[event_type] = 0
    
    # Sort by timestamp
    usage_timeseries.sort(key=lambda x: x["timestamp"])
    
    # Get overall usage stats
    overall_query = select(
        Event.event_type,
        func.count().label("count")
    ).where(
        Event.agent_id == agent_id,
        Event.timestamp.between(start_time, end_time)
    ).group_by(Event.event_type)
    
    overall_result = await session.execute(overall_query)
    event_counts = {row.event_type: row.count for row in overall_result}
    
    # Calculate total events
    total_events = sum(event_counts.values())
    
    # Calculate events per hour
    hours = (end_time - start_time).total_seconds() / 3600
    if hours < 0.1:  # Avoid division by very small numbers
        hours = 0.1
    
    events_per_hour = round(total_events / hours, 2)
    
    return {
        "metrics": {
            "type": "usage",
            "overall": {
                "total_events": total_events,
                "events_per_hour": events_per_hour,
                "by_event_type": event_counts
            },
            "time_series": usage_timeseries
        },
        "timeframe": {
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "interval": interval
        }
    }

async def get_error_metrics(
    session: AsyncSession, 
    agent_id: str, 
    start_time: datetime, 
    end_time: datetime,
    interval: str
):
    """Get error metrics and statistics."""
    
    # Determine the time grouping based on interval
    if interval == "minute":
        time_extract = [
            extract('year', Event.timestamp),
            extract('month', Event.timestamp),
            extract('day', Event.timestamp),
            extract('hour', Event.timestamp),
            extract('minute', Event.timestamp)
        ]
        format_str = "%Y-%m-%d %H:%M:00"
    elif interval == "hour":
        time_extract = [
            extract('year', Event.timestamp),
            extract('month', Event.timestamp),
            extract('day', Event.timestamp),
            extract('hour', Event.timestamp)
        ]
        format_str = "%Y-%m-%d %H:00:00"
    else:  # day
        time_extract = [
            extract('year', Event.timestamp),
            extract('month', Event.timestamp),
            extract('day', Event.timestamp)
        ]
        format_str = "%Y-%m-%d 00:00:00"
    
    # Query for error counts over time
    error_query = select(
        *time_extract,
        func.count().label("error_count")
    ).where(
        Event.agent_id == agent_id,
        Event.timestamp.between(start_time, end_time),
        Event.level.in_(["ERROR", "CRITICAL"])
    ).group_by(*time_extract).order_by(*time_extract)
    
    error_result = await session.execute(error_query)
    
    # Process the time-series data
    error_timeseries = []
    for row in error_result:
        # Create a timestamp from the extracted components
        if interval == "minute":
            ts = datetime(int(row[0]), int(row[1]), int(row[2]), int(row[3]), int(row[4]))
        elif interval == "hour":
            ts = datetime(int(row[0]), int(row[1]), int(row[2]), int(row[3]))
        else:  # day
            ts = datetime(int(row[0]), int(row[1]), int(row[2]))
            
        error_timeseries.append({
            "timestamp": ts.strftime(format_str),
            "error_count": row.error_count
        })
    
    # Get overall error stats
    error_types_query = select(
        Event.event_type,
        func.count().label("count")
    ).where(
        Event.agent_id == agent_id,
        Event.timestamp.between(start_time, end_time),
        Event.level.in_(["ERROR", "CRITICAL"])
    ).group_by(Event.event_type)
    
    error_types_result = await session.execute(error_types_query)
    error_types = {row.event_type: row.count for row in error_types_result}
    
    # Get total event count for error rate calculation
    total_events_query = select(func.count()).where(
        Event.agent_id == agent_id,
        Event.timestamp.between(start_time, end_time)
    )
    
    total_result = await session.execute(total_events_query)
    total_events = total_result.scalar() or 0
    
    # Calculate error rate
    error_count = sum(error_types.values())
    error_rate = (error_count / total_events * 100) if total_events > 0 else 0
    
    return {
        "metrics": {
            "type": "errors",
            "overall": {
                "total_errors": error_count,
                "error_rate": round(error_rate, 2),
                "by_error_type": error_types
            },
            "time_series": error_timeseries
        },
        "timeframe": {
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "interval": interval
        }
    } 