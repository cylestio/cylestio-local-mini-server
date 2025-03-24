from sqlalchemy import Column, String, Integer, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from app.models.base import Base

class CallStack(Base):
    """Model for storing call stack information from events."""
    
    __tablename__ = "call_stacks"
    
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    
    # Call stack information
    file = Column(String, nullable=True, index=True)
    line = Column(Integer, nullable=True)
    function = Column(String, nullable=True, index=True)
    module = Column(String, nullable=True, index=True)
    
    # Stack depth and hierarchy
    depth = Column(Integer, nullable=True, default=0)
    parent_id = Column(Integer, ForeignKey("call_stacks.id"), nullable=True)
    
    # Full stack trace
    stack_trace = Column(Text, nullable=True)
    
    # Additional context
    context = Column(JSON, nullable=True)
    
    # Relationships
    event = relationship("Event", back_populates="call_stacks")
    parent = relationship("CallStack", remote_side=[id], backref="children")
    
    def __repr__(self):
        return f"<CallStack event_id={self.event_id} function={self.function}>" 