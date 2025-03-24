from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship
import datetime

from app.models.base import Base

class Conversation(Base):
    """Model for tracking conversations and turn-taking between users and AI models."""
    
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(String, nullable=False, unique=True, index=True)
    agent_id = Column(String, ForeignKey("agents.agent_id"), nullable=False, index=True)
    session_id = Column(String, ForeignKey("sessions.session_id"), nullable=False, index=True)
    
    # Conversation metadata
    start_time = Column(DateTime, nullable=False, default=lambda: datetime.datetime.now(datetime.UTC))
    end_time = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    
    # Conversation attributes
    turn_count = Column(Integer, nullable=False, default=0)
    topic = Column(String, nullable=True)
    
    # Metrics
    total_tokens_used = Column(Integer, nullable=False, default=0)
    average_latency_ms = Column(Integer, nullable=True)
    
    # Additional metadata
    conversation_metadata = Column(JSON, nullable=True)
    
    # Relationships
    agent = relationship("Agent", back_populates="conversations")
    session = relationship("Session", back_populates="conversations")
    turns = relationship("ConversationTurn", back_populates="conversation", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Conversation id={self.conversation_id} turns={self.turn_count}>"
    
class ConversationTurn(Base):
    """Model for individual turns in a conversation."""
    
    __tablename__ = "conversation_turns"
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id"), nullable=False, index=True)
    
    # Turn details
    turn_number = Column(Integer, nullable=False, index=True)
    turn_type = Column(String, nullable=False, index=True)  # user, assistant
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.datetime.now(datetime.UTC))
    
    # Content
    content = Column(Text, nullable=True)
    content_type = Column(String, nullable=True)  # text, image, etc.
    
    # Related events
    request_event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    response_event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    
    # Metrics for this turn
    tokens_used = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="turns")
    request_event = relationship("Event", foreign_keys=[request_event_id])
    response_event = relationship("Event", foreign_keys=[response_event_id])
    
    def __repr__(self):
        return f"<ConversationTurn conversation={self.conversation_id} turn={self.turn_number} type={self.turn_type}>" 