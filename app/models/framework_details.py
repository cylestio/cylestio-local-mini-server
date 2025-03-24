from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship

from app.models.base import Base

class FrameworkDetails(Base):
    """Model for framework and model details from events."""
    
    __tablename__ = "framework_details"
    
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    name = Column(String, nullable=True, index=True)
    version = Column(String, nullable=True, index=True)
    component = Column(String, nullable=True, index=True)
    
    # Framework component information
    chain_type = Column(String, nullable=True)
    llm_type = Column(String, nullable=True, index=True)
    tool_type = Column(String, nullable=True)
    
    # Model information
    model_name = Column(String, nullable=True, index=True)
    
    # Relationships
    event = relationship("Event", back_populates="framework_details")
    
    def __repr__(self):
        return f"<FrameworkDetails {self.name} {self.version} model={self.model_name}>" 