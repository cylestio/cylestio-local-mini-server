from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Float
from sqlalchemy.orm import relationship

from app.models.base import Base

class PerformanceMetric(Base):
    """Model for performance metrics from LLM calls."""
    
    __tablename__ = "performance_metrics"
    
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    duration_ms = Column(Float, nullable=True, index=True)
    timestamp = Column(DateTime, nullable=True)
    
    # Relationships
    event = relationship("Event", back_populates="performance_metrics")
    
    def __repr__(self):
        return f"<PerformanceMetric event_id={self.event_id} duration_ms={self.duration_ms}>" 