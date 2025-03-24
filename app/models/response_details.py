from sqlalchemy import Column, String, Integer, ForeignKey, Text, JSON, Boolean, Float
from sqlalchemy.orm import relationship

from app.models.base import Base

class ResponseDetails(Base):
    """Model for detailed information about responses from LLMs."""
    
    __tablename__ = "response_details"
    
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    
    # Response content
    response_text = Column(Text, nullable=True)
    text_length = Column(Integer, nullable=True)
    generated_tokens = Column(Integer, nullable=True)
    
    # Response metadata
    stop_reason = Column(String, nullable=True, index=True)  # end_turn, token_limit, function_call, etc.
    stop_sequence = Column(String, nullable=True)
    
    # Response features
    has_citations = Column(Boolean, nullable=True, default=False)
    citation_count = Column(Integer, nullable=True, default=0)
    has_function_call = Column(Boolean, nullable=True, default=False)
    
    # Function calling information
    function_calls = Column(JSON, nullable=True)
    function_name = Column(String, nullable=True, index=True)
    
    # Response quality metrics
    perplexity = Column(Float, nullable=True)
    
    # Performance data
    time_to_first_token = Column(Float, nullable=True)
    tokens_per_second = Column(Float, nullable=True)
    
    # Full response data
    full_response = Column(JSON, nullable=True)
    
    # Relationships
    event = relationship("Event", back_populates="response_details")
    
    def __repr__(self):
        return f"<ResponseDetails event_id={self.event_id} stop_reason={self.stop_reason}>" 