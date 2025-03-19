from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
from typing import List, Optional
from datetime import datetime, timedelta

from app.database.init_db import get_session
from app.models.event import Event

router = APIRouter()

@router.get("/", response_model=dict)
async def get_alerts(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    severity: Optional[str] = Query(None, description="Filter by severity (high, medium, low)"),
    status: Optional[str] = Query(None, description="Filter by status (active, resolved)"),
    start_time: Optional[str] = Query(None, description="Start time in ISO format"),
    end_time: Optional[str] = Query(None, description="End time in ISO format"),
    limit: int = Query(20, ge=1, le=100, description="Number of alerts to return"),
    offset: int = Query(0, ge=0, description="Number of alerts to skip"),
    session: AsyncSession = Depends(get_session)
):
    """
    Get security alerts with filtering options.
    
    Returns a paginated list of security alerts.
    """
    # Base query for error events
    query = select(Event).where(
        Event.level.in_(["ERROR", "CRITICAL"]),
        # Include other conditions to identify security-related events
        or_(
            Event.event_type.ilike("%security%"),
            Event.event_type.ilike("%auth%"),
            Event.event_type.ilike("%access%"),
            Event.event_type.ilike("%permission%"),
            Event.event_type.ilike("%error%"),
            Event.channel.ilike("%security%")
        )
    )
    
    # Apply filters
    filters = []
    
    if agent_id:
        filters.append(Event.agent_id == agent_id)
    
    if severity:
        if severity.lower() == "high":
            filters.append(Event.level == "CRITICAL")
        elif severity.lower() == "medium":
            filters.append(Event.level == "ERROR")
        # Low severity would include warnings, but we're already filtering for ERROR/CRITICAL
    
    if start_time:
        start_datetime = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        filters.append(Event.timestamp >= start_datetime)
    
    if end_time:
        end_datetime = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        filters.append(Event.timestamp <= end_datetime)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Apply sorting (most recent first)
    query = query.order_by(desc(Event.timestamp))
    
    # Get total count for pagination
    count_query = select(func.count()).select_from(query.alias())
    count_result = await session.execute(count_query)
    total_count = count_result.scalar()
    
    # Apply pagination
    query = query.offset(offset).limit(limit)
    
    # Execute the query
    result = await session.execute(query)
    events = result.scalars().all()
    
    # Convert to alerts format
    alerts = []
    for event in events:
        # Generate a severity
        if event.level == "CRITICAL":
            severity = "high"
        elif event.level == "ERROR":
            severity = "medium"
        else:
            severity = "low"
        
        # Generate a status (for demonstration - in a real system this would be tracked in a separate table)
        # For this example, we'll consider alerts in the last 24 hours as active
        alert_status = "active" if (datetime.utcnow() - event.timestamp) < timedelta(days=1) else "resolved"
        
        # Skip if we're filtering by status and it doesn't match
        if status and status.lower() != alert_status:
            continue
        
        # Create alert object
        alert = {
            "id": event.id,
            "timestamp": event.timestamp.isoformat(),
            "agent_id": event.agent_id,
            "event_type": event.event_type,
            "channel": event.channel,
            "severity": severity,
            "status": alert_status,
            "message": f"Security alert: {event.event_type}",
            "details": event.data or {}
        }
        
        alerts.append(alert)
    
    # Adjust the total count if we filtered by status
    if status:
        total_count = len(alerts)
    
    # Construct response with pagination metadata
    return {
        "results": alerts,
        "pagination": {
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count
        }
    }

@router.get("/{alert_id}", response_model=dict)
async def get_alert(
    alert_id: int,
    session: AsyncSession = Depends(get_session)
):
    """
    Get detailed information about a specific alert.
    """
    # Alert ID corresponds to event ID
    result = await session.execute(
        select(Event).where(Event.id == alert_id)
    )
    event = result.scalars().first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID {alert_id} not found"
        )
    
    # Verify this is an error event
    if event.level not in ["ERROR", "CRITICAL"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {alert_id} is not an alert"
        )
    
    # Generate a severity
    if event.level == "CRITICAL":
        severity = "high"
    elif event.level == "ERROR":
        severity = "medium"
    else:
        severity = "low"
    
    # Generate a status
    alert_status = "active" if (datetime.utcnow() - event.timestamp) < timedelta(days=1) else "resolved"
    
    # Get related events (context around this alert)
    context_result = await session.execute(
        select(Event)
        .where(Event.agent_id == event.agent_id)
        .where(Event.timestamp.between(
            event.timestamp - timedelta(minutes=5),
            event.timestamp + timedelta(minutes=5)
        ))
        .where(Event.id != event.id)
        .order_by(Event.timestamp)
        .limit(10)
    )
    context_events = context_result.scalars().all()
    
    # Construct the response
    return {
        "id": event.id,
        "timestamp": event.timestamp.isoformat(),
        "agent_id": event.agent_id,
        "event_type": event.event_type,
        "channel": event.channel,
        "severity": severity,
        "status": alert_status,
        "message": f"Security alert: {event.event_type}",
        "details": event.data or {},
        "context": [
            {
                "id": e.id,
                "timestamp": e.timestamp.isoformat(),
                "event_type": e.event_type,
                "level": e.level
            }
            for e in context_events
        ]
    } 