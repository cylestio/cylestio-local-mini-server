from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, func, JSON
from sqlalchemy.orm import relationship

from app.models.base import Base

class Session(Base):
    """Model for tracking conversation sessions."""
    
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    agent_id = Column(String, ForeignKey("agents.agent_id"), nullable=False, index=True)
    start_time = Column(DateTime, server_default=func.now(), nullable=False)
    end_time = Column(DateTime, nullable=True)
    total_events = Column(Integer, default=0, nullable=False)
    
    # Enhanced metrics
    total_tokens = Column(Integer, default=0, nullable=False)
    total_requests = Column(Integer, default=0, nullable=False)
    total_responses = Column(Integer, default=0, nullable=False)
    avg_latency_ms = Column(Integer, nullable=True)
    session_metadata = Column(JSON, nullable=True)
    
    # Relationships
    agent = relationship("Agent")
    conversations = relationship("Conversation", back_populates="session")
    
    def __repr__(self):
        return f"<Session {self.session_id}>" 