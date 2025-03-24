from sqlalchemy import Column, String, DateTime, Integer, func, JSON
from sqlalchemy.orm import relationship

from app.models.base import Base

class Agent(Base):
    """Model for agents that are being monitored."""
    
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(String, unique=True, index=True, nullable=False)
    last_seen = Column(DateTime, server_default=func.now(), nullable=False)
    first_seen = Column(DateTime, server_default=func.now(), nullable=False)
    llm_provider = Column(String, nullable=True)
    
    # New fields for enhanced schema
    agent_type = Column(String, nullable=True, index=True)  # RAG, chatbot, etc.
    description = Column(String, nullable=True)
    configuration = Column(JSON, nullable=True)
    
    # Relationships
    events = relationship("Event", back_populates="agent")
    conversations = relationship("Conversation", back_populates="agent")
    
    def __repr__(self):
        return f"<Agent {self.agent_id}>" 