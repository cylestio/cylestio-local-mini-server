from sqlalchemy import Column, String, Integer, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship

from app.models.base import Base

class PromptDetails(Base):
    """Model for storing details about prompts used in LLM requests."""
    
    __tablename__ = "prompt_details"
    
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    
    # Basic prompt information
    prompt_text = Column(Text, nullable=True)  # First prompt text if multiple
    prompt_type = Column(String, nullable=True, index=True)  # system, user, assistant, etc.
    prompt_count = Column(Integer, nullable=True, default=1)  # Number of prompt messages
    
    # Prompt structure (for chat models)
    has_system_message = Column(Boolean, nullable=True, default=False)  
    system_message = Column(Text, nullable=True)
    
    # Raw prompts array
    prompts = Column(JSON, nullable=True)  # Store all prompts if needed
    
    # Context information
    context_included = Column(Boolean, nullable=True, default=False)
    context_source = Column(String, nullable=True)  # RAG, history, etc.
    context_tokens = Column(Integer, nullable=True)  # Estimated tokens for context
    
    # Relationships
    event = relationship("Event", back_populates="prompt_details")
    
    def __repr__(self):
        return f"<PromptDetails event_id={self.event_id} type={self.prompt_type}>" 