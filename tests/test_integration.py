import pytest
import datetime
import json
from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker

from app.models import Base, Agent, Event, Session, TokenUsage, PerformanceMetric
from app.models import SecurityAlert, ContentAnalysis, FrameworkDetails
from app.models import ModelDetails, PromptDetails, ResponseDetails, CallStack
from app.models import Conversation, ConversationTurn

# Setup test database with sample data
@pytest.fixture(scope="function")
def db_session_with_data():
    """Create an in-memory SQLite database with sample data for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    
    # Create agents
    agents = [
        Agent(agent_id="rag-agent", llm_provider="Anthropic", agent_type="RAG"),
        Agent(agent_id="chatbot-agent", llm_provider="Anthropic", agent_type="Chatbot"),
        Agent(agent_id="weather-agent", llm_provider="Anthropic", agent_type="Tool")
    ]
    session.add_all(agents)
    session.commit()
    
    # Create sessions
    sessions = [
        Session(session_id="session-1", agent_id="rag-agent"),
        Session(session_id="session-2", agent_id="chatbot-agent"),
        Session(session_id="session-3", agent_id="weather-agent")
    ]
    session.add_all(sessions)
    session.commit()
    
    # Create events with various types
    start_time = datetime.datetime(2025, 3, 20, 22, 0, 0)
    events = []
    
    # RAG agent events
    for i in range(10):
        # Create a request event
        req_event = Event(
            timestamp=start_time + datetime.timedelta(minutes=i*5),
            level="INFO",
            agent_id="rag-agent",
            event_type="model_request",
            channel="LANGCHAIN",
            session_id="session-1",
            data={"test": f"request-{i}"}
        )
        events.append(req_event)
        
        # Create a response event
        resp_event = Event(
            timestamp=start_time + datetime.timedelta(minutes=i*5, seconds=30),
            level="INFO",
            agent_id="rag-agent",
            event_type="model_response",
            channel="LANGCHAIN",
            session_id="session-1",
            data={"test": f"response-{i}"},
            duration_ms=2000 + (i * 100)  # Varying duration
        )
        events.append(resp_event)
    
    # Chatbot agent events
    for i in range(5):
        # Create a request event
        req_event = Event(
            timestamp=start_time + datetime.timedelta(minutes=i*3),
            level="INFO",
            agent_id="chatbot-agent",
            event_type="model_request",
            channel="LANGCHAIN",
            session_id="session-2",
            data={"test": f"chat-request-{i}"}
        )
        events.append(req_event)
        
        # Create a response event
        resp_event = Event(
            timestamp=start_time + datetime.timedelta(minutes=i*3, seconds=20),
            level="INFO",
            agent_id="chatbot-agent",
            event_type="model_response",
            channel="LANGCHAIN",
            session_id="session-2",
            data={"test": f"chat-response-{i}"},
            duration_ms=1500 + (i * 150)  # Varying duration
        )
        events.append(resp_event)
    
    # Weather agent events with security alerts
    for i in range(3):
        # Create a request event
        req_event = Event(
            timestamp=start_time + datetime.timedelta(hours=1, minutes=i*10),
            level="INFO",
            agent_id="weather-agent",
            event_type="LLM_call_start",
            channel="LLM",
            session_id="session-3",
            data={"test": f"weather-request-{i}"}
        )
        events.append(req_event)
        
        # Create a response event
        resp_event = Event(
            timestamp=start_time + datetime.timedelta(hours=1, minutes=i*10, seconds=15),
            level="INFO",
            agent_id="weather-agent",
            event_type="LLM_call_finish",
            channel="LLM",
            session_id="session-3",
            data={"test": f"weather-response-{i}"},
            duration_ms=1000 + (i * 200)  # Varying duration
        )
        events.append(resp_event)
        
        # Create a security alert event for one of the requests
        if i == 1:
            alert_event = Event(
                timestamp=start_time + datetime.timedelta(hours=1, minutes=i*10, seconds=5),
                level="WARNING",
                agent_id="weather-agent",
                event_type="LLM_call_start",
                channel="LLM",
                session_id="session-3",
                data={"prompt": "suspicious content", "alert": "suspicious"},
                alert="suspicious"
            )
            events.append(alert_event)
    
    session.add_all(events)
    session.commit()
    
    # Add token usage for each response event
    for event in session.query(Event).filter(Event.event_type.in_(["model_response", "LLM_call_finish"])).all():
        # Different token usage for different agents
        if event.agent_id == "rag-agent":
            input_tokens = 200
            output_tokens = 150
            model = "claude-3-haiku-20240307"
        elif event.agent_id == "chatbot-agent":
            input_tokens = 30 + (int(event.data["test"].split("-")[-1]) * 20)  # Increasing with turn number
            output_tokens = 300 - (int(event.data["test"].split("-")[-1]) * 20)  # Decreasing with turn number
            model = "claude-3-haiku-20240307"
        else:  # weather-agent
            input_tokens = 500
            output_tokens = 60
            model = "claude-3-haiku-20240307"
        
        token_usage = TokenUsage(
            event_id=event.id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            model=model
        )
        session.add(token_usage)
    
    # Add model details for each request event
    for event in session.query(Event).filter(Event.event_type.in_(["model_request", "LLM_call_start"])).all():
        if event.agent_id == "rag-agent" or event.agent_id == "chatbot-agent":
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
        else:  # weather-agent
            model_details = ModelDetails(
                event_id=event.id,
                model_name="claude-3-haiku",
                model_provider="Anthropic",
                model_type="chat",
                model_version="20240307",
                context_window_size=200000,
                max_tokens=4096,
                temperature=0.5,
                supports_function_calling=True,
                supports_vision=False,
                supports_streaming=False
            )
        session.add(model_details)
    
    # Add security alerts
    alert_event = session.query(Event).filter_by(alert="suspicious").first()
    if alert_event:
        security_alert = SecurityAlert(
            event_id=alert_event.id,
            severity="medium",
            alert_type="prompt_injection",
            description="Potentially suspicious prompt detected",
            timestamp=alert_event.timestamp
        )
        session.add(security_alert)
    
    # Create conversations for RAG and chatbot agents
    rag_conversation = Conversation(
        conversation_id="rag-conv-1",
        agent_id="rag-agent",
        session_id="session-1",
        start_time=start_time,
        turn_count=5,
        total_tokens_used=1750,
        average_latency_ms=2250
    )
    session.add(rag_conversation)
    
    chat_conversation = Conversation(
        conversation_id="chat-conv-1",
        agent_id="chatbot-agent",
        session_id="session-2",
        start_time=start_time,
        turn_count=5,
        total_tokens_used=1650,
        average_latency_ms=1750
    )
    session.add(chat_conversation)
    
    session.commit()
    
    # Add conversation turns for the conversations
    # RAG conversation turns
    rag_events = session.query(Event).filter_by(agent_id="rag-agent").order_by(Event.timestamp).all()
    for i in range(5):
        req_idx = i * 2
        resp_idx = i * 2 + 1
        
        if req_idx < len(rag_events) and resp_idx < len(rag_events):
            turn1 = ConversationTurn(
                conversation_id="rag-conv-1",
                turn_number=i*2 + 1,
                turn_type="user",
                content=f"Question {i+1}",
                content_type="text",
                request_event_id=rag_events[req_idx].id,
                tokens_used=200
            )
            session.add(turn1)
            
            turn2 = ConversationTurn(
                conversation_id="rag-conv-1",
                turn_number=i*2 + 2,
                turn_type="assistant",
                content=f"Answer {i+1}",
                content_type="text",
                response_event_id=rag_events[resp_idx].id,
                tokens_used=150,
                latency_ms=2000 + (i * 100)
            )
            session.add(turn2)
    
    # Chatbot conversation turns
    chat_events = session.query(Event).filter_by(agent_id="chatbot-agent").order_by(Event.timestamp).all()
    for i in range(5):
        req_idx = i * 2
        resp_idx = i * 2 + 1
        
        if req_idx < len(chat_events) and resp_idx < len(chat_events):
            turn1 = ConversationTurn(
                conversation_id="chat-conv-1",
                turn_number=i*2 + 1,
                turn_type="user",
                content=f"Hi {i+1}",
                content_type="text",
                request_event_id=chat_events[req_idx].id,
                tokens_used=30 + (i * 20)
            )
            session.add(turn1)
            
            turn2 = ConversationTurn(
                conversation_id="chat-conv-1",
                turn_number=i*2 + 2,
                turn_type="assistant",
                content=f"Hello {i+1}",
                content_type="text",
                response_event_id=chat_events[resp_idx].id,
                tokens_used=300 - (i * 20),
                latency_ms=1500 + (i * 150)
            )
            session.add(turn2)
    
    session.commit()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(engine)

# Test query: Token usage by agent over time
def test_token_usage_by_agent(db_session_with_data):
    """Test querying token usage by agent over time."""
    query = db_session_with_data.query(
        Event.agent_id,
        func.strftime('%Y-%m-%d %H:00:00', Event.timestamp).label('hour'),
        func.sum(TokenUsage.input_tokens).label('total_input_tokens'),
        func.sum(TokenUsage.output_tokens).label('total_output_tokens')
    ).join(
        TokenUsage, TokenUsage.event_id == Event.id
    ).group_by(
        Event.agent_id, 'hour'
    ).order_by(
        Event.agent_id, 'hour'
    )
    
    results = query.all()
    
    # Should have at least one row per agent
    assert len(results) >= 3
    
    # Check that we have results for each agent
    agent_ids = set([result[0] for result in results])
    assert "rag-agent" in agent_ids
    assert "chatbot-agent" in agent_ids
    assert "weather-agent" in agent_ids
    
    # Check that token counts are positive
    for result in results:
        assert result[2] > 0  # input tokens
        assert result[3] > 0  # output tokens

# Test query: Average response latency by model
def test_response_latency_by_model(db_session_with_data):
    """Test querying average response latency by model."""
    # First, get the model details for request events
    request_events = db_session_with_data.query(Event).filter(
        Event.event_type.in_(["model_request", "LLM_call_start"])
    ).all()
    
    # Get the corresponding response events
    response_latencies = []
    for req_event in request_events:
        # For each request, get the corresponding response event
        resp_event = db_session_with_data.query(Event).filter(
            Event.agent_id == req_event.agent_id,
            Event.session_id == req_event.session_id,
            Event.event_type.in_(["model_response", "LLM_call_finish"]),
            Event.timestamp > req_event.timestamp
        ).order_by(Event.timestamp).first()
        
        # Get model details for this request
        model_details = db_session_with_data.query(ModelDetails).filter(
            ModelDetails.event_id == req_event.id
        ).first()
        
        if resp_event and model_details:
            response_latencies.append((
                model_details.model_name,
                resp_event.duration_ms
            ))
    
    # Group by model name and calculate average latency
    model_latencies = {}
    for model_name, latency in response_latencies:
        if model_name not in model_latencies:
            model_latencies[model_name] = {"total": 0, "count": 0}
        model_latencies[model_name]["total"] += latency
        model_latencies[model_name]["count"] += 1
    
    results = [(model, data["total"] / data["count"], data["count"]) 
               for model, data in model_latencies.items()]
    results.sort(key=lambda x: x[1], reverse=True)  # Sort by avg latency
    
    # Should have at least one row
    assert len(results) > 0
    
    # First result should be the model with highest latency
    assert results[0][0] is not None  # model name
    assert results[0][1] > 0  # avg latency
    assert results[0][2] > 0  # call count

# Test query: Security alerts by severity
def test_security_alerts_by_severity(db_session_with_data):
    """Test querying security alerts by severity."""
    query = db_session_with_data.query(
        SecurityAlert.severity,
        func.count().label('alert_count')
    ).group_by(
        SecurityAlert.severity
    )
    
    results = query.all()
    
    # Should have at least one row
    assert len(results) > 0
    
    # Check that we have a medium severity alert
    medium_alerts = [r for r in results if r[0] == "medium"]
    assert len(medium_alerts) == 1
    assert medium_alerts[0][1] > 0  # at least one alert

# Test query: Most active conversations
def test_most_active_conversations(db_session_with_data):
    """Test querying most active conversations by turn count."""
    query = db_session_with_data.query(
        Conversation.conversation_id,
        Conversation.agent_id,
        Conversation.turn_count,
        Conversation.total_tokens_used
    ).order_by(
        Conversation.turn_count.desc()
    ).limit(10)
    
    results = query.all()
    
    # Should have at least one row
    assert len(results) > 0
    
    # First result should be the conversation with most turns
    assert results[0][0] is not None  # conversation_id
    assert results[0][1] is not None  # agent_id
    assert results[0][2] > 0  # turn_count
    assert results[0][3] > 0  # total_tokens_used

# Test query: Agent performance comparison
def test_agent_performance_comparison(db_session_with_data):
    """Test querying performance metrics to compare agents."""
    query = db_session_with_data.query(
        Event.agent_id,
        func.avg(Event.duration_ms).label('avg_response_time'),
        func.avg(TokenUsage.total_tokens).label('avg_tokens_per_call'),
        func.count().label('call_count')
    ).join(
        TokenUsage, TokenUsage.event_id == Event.id
    ).filter(
        Event.event_type.in_(["model_response", "LLM_call_finish"])
    ).group_by(
        Event.agent_id
    )
    
    results = query.all()
    
    # Should have results for each agent
    assert len(results) == 3
    
    # Check that metrics are reasonable
    for result in results:
        assert result[0] is not None  # agent_id
        assert result[1] > 0  # avg_response_time
        assert result[2] > 0  # avg_tokens_per_call
        assert result[3] > 0  # call_count

# Test query: Conversation turns with related events
def test_conversation_turns_with_events(db_session_with_data):
    """Test querying conversation turns with their related events."""
    query = db_session_with_data.query(
        ConversationTurn.conversation_id,
        ConversationTurn.turn_number,
        ConversationTurn.turn_type,
        ConversationTurn.content,
        Event.timestamp,
        Event.event_type
    ).join(
        Event, 
        (Event.id == ConversationTurn.request_event_id) | 
        (Event.id == ConversationTurn.response_event_id)
    ).filter(
        ConversationTurn.conversation_id == "rag-conv-1"
    ).order_by(
        ConversationTurn.turn_number
    )
    
    results = query.all()
    
    # Should have multiple turns
    assert len(results) > 0
    
    # First turn should be for rag-conv-1
    assert results[0][0] == "rag-conv-1"
    assert results[0][1] > 0  # turn_number
    assert results[0][2] in ["user", "assistant"]  # turn_type
    assert results[0][3] is not None  # content
    assert results[0][4] is not None  # timestamp
    assert results[0][5] in ["model_request", "model_response"]  # event_type 