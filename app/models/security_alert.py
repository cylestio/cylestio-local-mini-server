from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.models.base import Base

class SecurityAlert(Base):
    """Model for security alerts from events."""
    
    __tablename__ = "security_alerts"
    
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    alert_level = Column(String, nullable=False, index=True)
    field_path = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    
    # Relationships
    event = relationship("Event", back_populates="security_alerts")
    
    def __repr__(self):
        return f"<SecurityAlert event_id={self.event_id} level={self.alert_level}>" 