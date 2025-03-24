from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship

from app.models.base import Base

class SecurityAlert(Base):
    """Model for security alerts detected in events."""
    
    __tablename__ = "security_alerts"
    
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    alert_type = Column(String, nullable=False, index=True)
    severity = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Relationships
    event = relationship("Event", back_populates="security_alerts")
    
    def __repr__(self):
        return f"<SecurityAlert {self.alert_type} (severity={self.severity})>" 