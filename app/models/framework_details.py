from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.models.base import Base

class FrameworkDetails(Base):
    """Model for framework details from events."""
    
    __tablename__ = "framework_details"
    
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    framework_name = Column(String, nullable=False, index=True)
    framework_version = Column(String, nullable=True)
    component_name = Column(String, nullable=True, index=True)
    component_type = Column(String, nullable=True)
    components_json = Column(JSON, nullable=True)
    
    # Relationships
    event = relationship("Event", back_populates="framework_details")
    
    def __repr__(self):
        return f"<FrameworkDetails event_id={self.event_id} framework={self.framework_name}>" 