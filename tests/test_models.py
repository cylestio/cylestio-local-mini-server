import pytest
import datetime
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, clear_mappers

from app.models import Base, Agent, Event, Session, TokenUsage, PerformanceMetric
from app.models import SecurityAlert, ContentAnalysis, FrameworkDetails
from app.models import ModelDetails, PromptDetails, ResponseDetails, CallStack
from app.models import Conversation, ConversationTurn

# Setup test database
@pytest.fixture(scope="function")
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(engine)
    
# Test basic model creation
def test_create_agent(db_session):
    """Test creating an Agent model."""
    agent = Agent(
        agent_id="test-agent",
        llm_provider="test-provider",
        agent_type="RAG"
    )
    
    db_session.add(agent)
    db_session.commit()
    
    saved_agent = db_session.query(Agent).filter_by(agent_id="test-agent").first()
    assert saved_agent is not None
    assert saved_agent.agent_id == "test-agent"
    assert saved_agent.llm_provider == "test-provider"
    assert saved_agent.agent_type == "RAG"

def test_create_event(db_session):
    """Test creating an Event model."""
    # First create an agent
    agent = Agent(agent_id="test-agent")
    db_session.add(agent)
    db_session.commit()
    
    # Create an event
    event = Event(
        timestamp=datetime.datetime.now(datetime.UTC),
        level="INFO",
        agent_id="test-agent",
        event_type="model_request",
        channel="LANGCHAIN",
        data={"test": "data"}
    )
    
    db_session.add(event)
    db_session.commit()
    
    saved_event = db_session.query(Event).first()
    assert saved_event is not None
    assert saved_event.agent_id == "test-agent"
    assert saved_event.event_type == "model_request"
    assert saved_event.data["test"] == "data"

def test_create_token_usage(db_session):
    """Test creating a TokenUsage model with parent Event."""
    # First create an agent and event
    agent = Agent(agent_id="test-agent")
    db_session.add(agent)
    db_session.commit()
    
    event = Event(
        timestamp=datetime.datetime.now(datetime.UTC),
        level="INFO",
        agent_id="test-agent",
        event_type="model_response",
        channel="LANGCHAIN"
    )
    db_session.add(event)
    db_session.commit()
    
    # Create token usage
    token_usage = TokenUsage(
        event_id=event.id,
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        model="claude-3-haiku"
    )
    
    db_session.add(token_usage)
    db_session.commit()
    
    saved_token_usage = db_session.query(TokenUsage).first()
    assert saved_token_usage is not None
    assert saved_token_usage.input_tokens == 100
    assert saved_token_usage.output_tokens == 50
    assert saved_token_usage.event_id == event.id
    
    # Test relationship from event to token_usage
    saved_event = db_session.query(Event).first()
    assert saved_event.token_usage is not None
    assert saved_event.token_usage.input_tokens == 100

def test_create_model_details(db_session):
    """Test creating a ModelDetails model with parent Event."""
    # First create an agent and event
    agent = Agent(agent_id="test-agent")
    db_session.add(agent)
    db_session.commit()
    
    event = Event(
        timestamp=datetime.datetime.now(datetime.UTC),
        level="INFO",
        agent_id="test-agent",
        event_type="model_request",
        channel="LANGCHAIN"
    )
    db_session.add(event)
    db_session.commit()
    
    # Create model details
    model_details = ModelDetails(
        event_id=event.id,
        model_name="claude-3-haiku",
        model_provider="Anthropic",
        model_type="chat",
        model_version="20240307",
        context_window_size=200000,
        max_tokens=4096,
        temperature=0.7,
        supports_function_calling=True,
        supports_vision=True,
        supports_streaming=True
    )
    
    db_session.add(model_details)
    db_session.commit()
    
    saved_model_details = db_session.query(ModelDetails).first()
    assert saved_model_details is not None
    assert saved_model_details.model_name == "claude-3-haiku"
    assert saved_model_details.model_provider == "Anthropic"
    assert saved_model_details.supports_function_calling is True
    
    # Test relationship from event to model_details
    saved_event = db_session.query(Event).first()
    assert saved_event.model_details is not None
    assert saved_event.model_details.model_name == "claude-3-haiku"

def test_create_prompt_details(db_session):
    """Test creating a PromptDetails model with parent Event."""
    # First create an agent and event
    agent = Agent(agent_id="test-agent")
    db_session.add(agent)
    db_session.commit()
    
    event = Event(
        timestamp=datetime.datetime.now(datetime.UTC),
        level="INFO",
        agent_id="test-agent",
        event_type="model_request",
        channel="LANGCHAIN"
    )
    db_session.add(event)
    db_session.commit()
    
    # Create prompt details
    prompt_details = PromptDetails(
        event_id=event.id,
        prompt_text="Hello, how are you?",
        prompt_type="user",
        prompt_count=1,
        has_system_message=True,
        system_message="You are a helpful assistant",
        prompts=json.dumps([
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello, how are you?"}
        ]),
        context_included=False
    )
    
    db_session.add(prompt_details)
    db_session.commit()
    
    saved_prompt_details = db_session.query(PromptDetails).first()
    assert saved_prompt_details is not None
    assert saved_prompt_details.prompt_text == "Hello, how are you?"
    assert saved_prompt_details.prompt_type == "user"
    assert saved_prompt_details.has_system_message is True
    
    # Test relationship from event to prompt_details
    saved_event = db_session.query(Event).first()
    assert saved_event.prompt_details is not None
    assert saved_event.prompt_details.prompt_text == "Hello, how are you?"

def test_create_response_details(db_session):
    """Test creating a ResponseDetails model with parent Event."""
    # First create an agent and event
    agent = Agent(agent_id="test-agent")
    db_session.add(agent)
    db_session.commit()
    
    event = Event(
        timestamp=datetime.datetime.now(datetime.UTC),
        level="INFO",
        agent_id="test-agent",
        event_type="model_response",
        channel="LANGCHAIN"
    )
    db_session.add(event)
    db_session.commit()
    
    # Create response details
    response_details = ResponseDetails(
        event_id=event.id,
        response_text="I'm doing well, thank you for asking!",
        text_length=43,
        generated_tokens=12,
        stop_reason="end_turn",
        stop_sequence=None,
        has_citations=False,
        has_function_call=False,
        tokens_per_second=20.5
    )
    
    db_session.add(response_details)
    db_session.commit()
    
    saved_response_details = db_session.query(ResponseDetails).first()
    assert saved_response_details is not None
    assert saved_response_details.response_text == "I'm doing well, thank you for asking!"
    assert saved_response_details.stop_reason == "end_turn"
    assert saved_response_details.tokens_per_second == 20.5
    
    # Test relationship from event to response_details
    saved_event = db_session.query(Event).first()
    assert saved_event.response_details is not None
    assert saved_event.response_details.response_text == "I'm doing well, thank you for asking!"

def test_create_call_stack(db_session):
    """Test creating a CallStack model with parent Event."""
    # First create an agent and event
    agent = Agent(agent_id="test-agent")
    db_session.add(agent)
    db_session.commit()
    
    event = Event(
        timestamp=datetime.datetime.now(datetime.UTC),
        level="INFO",
        agent_id="test-agent",
        event_type="model_request",
        channel="LANGCHAIN"
    )
    db_session.add(event)
    db_session.commit()
    
    # Create call stack
    call_stack = CallStack(
        event_id=event.id,
        file="test_file.py",
        line=42,
        function="test_function",
        module="test_module",
        depth=0,
        stack_trace="File test_file.py, line 42, in test_function"
    )
    
    db_session.add(call_stack)
    db_session.commit()
    
    saved_call_stack = db_session.query(CallStack).first()
    assert saved_call_stack is not None
    assert saved_call_stack.file == "test_file.py"
    assert saved_call_stack.line == 42
    assert saved_call_stack.function == "test_function"
    
    # Test relationship from event to call_stack
    saved_event = db_session.query(Event).first()
    assert saved_event.call_stacks is not None
    assert len(saved_event.call_stacks) == 1
    assert saved_event.call_stacks[0].file == "test_file.py"

def test_create_conversation_with_turns(db_session):
    """Test creating a Conversation with ConversationTurns."""
    # First create an agent and session
    agent = Agent(agent_id="test-agent")
    db_session.add(agent)
    db_session.commit()
    
    session = Session(
        session_id="test-session",
        agent_id="test-agent"
    )
    db_session.add(session)
    db_session.commit()
    
    # Create conversation
    conversation = Conversation(
        conversation_id="test-conversation",
        agent_id="test-agent",
        session_id="test-session",
        start_time=datetime.datetime.now(datetime.UTC),
        turn_count=2,
        total_tokens_used=150
    )
    db_session.add(conversation)
    db_session.commit()
    
    # Add request and response events
    request_event = Event(
        timestamp=datetime.datetime.now(datetime.UTC),
        level="INFO",
        agent_id="test-agent",
        event_type="model_request",
        channel="LANGCHAIN"
    )
    db_session.add(request_event)
    
    response_event = Event(
        timestamp=datetime.datetime.now(datetime.UTC),
        level="INFO",
        agent_id="test-agent",
        event_type="model_response",
        channel="LANGCHAIN"
    )
    db_session.add(response_event)
    db_session.commit()
    
    # Create conversation turns
    turn1 = ConversationTurn(
        conversation_id="test-conversation",
        turn_number=1,
        turn_type="user",
        content="Hello, how are you?",
        content_type="text",
        request_event_id=request_event.id
    )
    db_session.add(turn1)
    
    turn2 = ConversationTurn(
        conversation_id="test-conversation",
        turn_number=2,
        turn_type="assistant",
        content="I'm doing well, thank you!",
        content_type="text",
        response_event_id=response_event.id,
        tokens_used=25,
        latency_ms=250
    )
    db_session.add(turn2)
    db_session.commit()
    
    # Test conversation
    saved_conversation = db_session.query(Conversation).first()
    assert saved_conversation is not None
    assert saved_conversation.conversation_id == "test-conversation"
    assert saved_conversation.turn_count == 2
    
    # Test relationship from conversation to turns
    assert len(saved_conversation.turns) == 2
    assert saved_conversation.turns[0].turn_number == 1
    assert saved_conversation.turns[0].turn_type == "user"
    assert saved_conversation.turns[1].turn_number == 2
    assert saved_conversation.turns[1].turn_type == "assistant"
    
    # Test relationship from agent to conversation
    saved_agent = db_session.query(Agent).first()
    assert len(saved_agent.conversations) == 1
    assert saved_agent.conversations[0].conversation_id == "test-conversation" 