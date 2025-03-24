from sqlalchemy import Column, String, Integer, ForeignKey, Float, JSON, Boolean
from sqlalchemy.orm import relationship

from app.models.base import Base

class ModelDetails(Base):
    """Model for detailed information about language models used in events."""
    
    __tablename__ = "model_details"
    
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    
    # Basic model information
    model_name = Column(String, nullable=False, index=True)
    model_provider = Column(String, nullable=True, index=True)
    model_type = Column(String, nullable=True, index=True)  # completion, chat, embedding, etc.
    model_version = Column(String, nullable=True, index=True)
    
    # Model capabilities and configuration
    context_window_size = Column(Integer, nullable=True)
    max_tokens = Column(Integer, nullable=True)
    temperature = Column(Float, nullable=True)
    top_p = Column(Float, nullable=True)
    frequency_penalty = Column(Float, nullable=True)
    presence_penalty = Column(Float, nullable=True)
    stop_sequences = Column(JSON, nullable=True)
    
    # Model behavior details
    supports_function_calling = Column(Boolean, nullable=True, default=False)
    supports_vision = Column(Boolean, nullable=True, default=False)
    supports_streaming = Column(Boolean, nullable=True, default=False)
    
    # Model metadata
    model_metadata = Column(JSON, nullable=True)
    
    # Relationships
    event = relationship("Event", back_populates="model_details")
    
    def __repr__(self):
        return f"<ModelDetails model={self.model_name} provider={self.model_provider}>" 