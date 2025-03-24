import pytest
import json
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, Agent, Event
from app.models import ModelDetails, PromptDetails, ResponseDetails, TokenUsage
from app.business_logic.extractors.model_info_extractor import ModelInfoExtractor
from app.business_logic.extractors.token_usage_extractor import TokenUsageExtractor

# Setup test database
@pytest.fixture(scope="function")
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create a test agent
    agent = Agent(agent_id="test-agent", llm_provider="Anthropic")
    session.add(agent)
    session.commit()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(engine)

# Test ModelInfoExtractor with model_request event
@pytest.mark.asyncio
async def test_model_info_extractor_with_request(db_session):
    """Test that ModelInfoExtractor correctly extracts model info from a request event."""
    # Create a model_request event with sample data
    event_data = {
        "llm_type": "ChatAnthropic",
        "model": {
            "name": "ChatAnthropic",
            "type": "completion",
            "provider": "Anthropic",
            "metadata": {}
        },
        "prompts": ["You are a helpful AI assistant", "What is the weather?"],
        "metadata": {},
        "run_id": "12345",
        "framework_version": "0.3.44",
        "components": {
            "chain_type": "None",
            "llm_type": "ChatAnthropic",
            "tool_type": "None"
        }
    }
    
    event = Event(
        timestamp=datetime.datetime.now(datetime.UTC),
        level="INFO",
        agent_id="test-agent",
        event_type="model_request",
        channel="LANGCHAIN",
        data=event_data
    )
    db_session.add(event)
    db_session.commit()
    
    # Create and run the extractor
    extractor = ModelInfoExtractor()
    assert extractor.can_process(event) is True
    
    # Process the event
    await extractor.process(event, db_session)
    db_session.commit()
    
    # Verify the extracted data
    framework_details = db_session.query(ModelDetails).filter_by(event_id=event.id).first()
    assert framework_details is not None
    assert framework_details.model_name == "ChatAnthropic"
    assert framework_details.model_provider == "Anthropic"
    assert framework_details.model_type == "completion"

# Test TokenUsageExtractor with model_response event
@pytest.mark.asyncio
async def test_token_usage_extractor_with_response(db_session):
    """Test that TokenUsageExtractor correctly extracts token usage from a response event."""
    # Create a model_response event with sample data
    event_data = {
        "response": {
            "text": "('text', 'The weather is sunny.')",
            "llm_output": {
                "id": "msg_01ABCDEF",
                "model": "claude-3-haiku-20240307",
                "stop_reason": "end_turn",
                "stop_sequence": "None",
                "usage": {
                    "cache_creation_input_tokens": "0",
                    "cache_read_input_tokens": "0",
                    "input_tokens": "200",
                    "output_tokens": "158"
                },
                "model_name": "claude-3-haiku-20240307"
            }
        },
        "performance": {
            "duration_ms": "1500.123"
        }
    }
    
    event = Event(
        timestamp=datetime.datetime.now(datetime.UTC),
        level="INFO",
        agent_id="test-agent",
        event_type="model_response",
        channel="LANGCHAIN",
        data=event_data
    )
    db_session.add(event)
    db_session.commit()
    
    # Create and run the extractor
    extractor = TokenUsageExtractor()
    assert extractor.can_process(event) is True
    
    # Process the event
    await extractor.process(event, db_session)
    db_session.commit()
    
    # Verify the extracted data
    token_usage = db_session.query(TokenUsage).filter_by(event_id=event.id).first()
    assert token_usage is not None
    assert token_usage.input_tokens == 200
    assert token_usage.output_tokens == 158
    assert token_usage.total_tokens == 358
    assert token_usage.model == "claude-3-haiku-20240307" 