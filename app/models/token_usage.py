from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Float
from sqlalchemy.orm import relationship

from app.models.base import Base

class TokenUsage(Base):
    """Model for token usage metrics from LLM calls."""
    
    __tablename__ = "token_usage"
    
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    model = Column(String, nullable=True, index=True)
    
    # Relationships
    event = relationship("Event", back_populates="token_usage")
    
    def __repr__(self):
        return f"<TokenUsage event_id={self.event_id} input={self.input_tokens} output={self.output_tokens}>" 