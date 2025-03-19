from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Float, Text
from sqlalchemy.orm import relationship

from app.models.base import Base

class ContentAnalysis(Base):
    """Model for analyzed content from responses."""
    
    __tablename__ = "content_analysis"
    
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    content_type = Column(String, nullable=False, index=True)
    content_text = Column(Text, nullable=True)
    sentiment_score = Column(Float, nullable=True)
    toxicity_score = Column(Float, nullable=True)
    word_count = Column(Integer, nullable=True)
    
    # Relationships
    event = relationship("Event", back_populates="content_analysis")
    
    def __repr__(self):
        return f"<ContentAnalysis event_id={self.event_id} type={self.content_type}>" 