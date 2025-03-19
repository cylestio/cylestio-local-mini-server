from sqlalchemy import Column, String, DateTime, Integer, func
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
    
    # Relationships
    events = relationship("Event", back_populates="agent")
    
    def __repr__(self):
        return f"<Agent {self.agent_id}>" 