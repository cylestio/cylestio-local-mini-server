from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text, JSON, Float
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
    
    # Relationships
    agent = relationship("Agent", back_populates="events")
    
    def __repr__(self):
        return f"<Event {self.event_type} at {self.timestamp}>" 