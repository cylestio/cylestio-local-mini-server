from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text, JSON, Float, Boolean
from sqlalchemy.orm import relationship
import datetime

from app.models.base import Base

class Event(Base):
    """Model for telemetry events from monitoring SDK."""
    
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    level = Column(String, nullable=False, index=True)
    agent_id = Column(String, ForeignKey("agents.agent_id"), nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    channel = Column(String, nullable=False, index=True)
    
    # Optional fields
    direction = Column(String, nullable=True, index=True)
    session_id = Column(String, nullable=True, index=True)
    
    # Relationship tracking
    relationship_id = Column(String, nullable=True, index=True)
    
    # Store the full event data as JSON
    data = Column(JSON, nullable=True)
    
    # Performance data
    duration_ms = Column(Float, nullable=True, index=True)
    
    # If there was a caller, store the file, line, and function
    caller_file = Column(String, nullable=True)
    caller_line = Column(Integer, nullable=True)
    caller_function = Column(String, nullable=True)
    
    # Track whether this event has been processed by the business logic layer
    is_processed = Column(Boolean, nullable=False, default=False, index=True)
    
    # Alert status for security events
    alert = Column(String, nullable=True, index=True)
    
    # Relationships
    agent = relationship("Agent", back_populates="events")
    
    # Existing relationships to normalized data models
    token_usage = relationship("TokenUsage", back_populates="event", uselist=False, cascade="all, delete-orphan")
    performance_metrics = relationship("PerformanceMetric", back_populates="event", cascade="all, delete-orphan")
    security_alerts = relationship("SecurityAlert", back_populates="event", cascade="all, delete-orphan")
    content_analysis = relationship("ContentAnalysis", back_populates="event", cascade="all, delete-orphan")
    framework_details = relationship("FrameworkDetails", back_populates="event", uselist=False, cascade="all, delete-orphan")
    
    # New relationships to enhanced data models
    model_details = relationship("ModelDetails", back_populates="event", uselist=False, cascade="all, delete-orphan")
    prompt_details = relationship("PromptDetails", back_populates="event", uselist=False, cascade="all, delete-orphan")
    response_details = relationship("ResponseDetails", back_populates="event", uselist=False, cascade="all, delete-orphan")
    call_stacks = relationship("CallStack", back_populates="event", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Event {self.event_type} at {self.timestamp}>" 