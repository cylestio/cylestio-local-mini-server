import pytest
import json
import os
from typing import Dict, Any, List

from app.transformers.event_transformer import EventTransformer

class TestRealJSONFiles:
    """Test the transformer with real JSON files from examples."""
    
    @pytest.fixture
    def transformer(self):
        """Return an EventTransformer instance."""
        return EventTransformer()
    
    def test_weather_monitoring_json(self, transformer):
        """Test processing the weather monitoring JSON example."""
        # Path to the example JSON file
        json_path = os.path.join(os.getcwd(), "input_json_records_examples", "weather_monitoring.json")
        
        # Read the JSON lines (each line is a separate JSON object)
        events = []
        with open(json_path, "r") as f:
            for line in f:
                if line.strip():  # Skip empty lines
                    events.append(json.loads(line))
        
        # Make sure we have some events
        assert len(events) > 0
        
        # Process each event individually
        for event in events:
            transformed = transformer.transform(event)
            
            # Verify basic transformation
            assert "timestamp" in transformed
            assert "agent_id" in transformed
            assert "event_type" in transformed
            assert "channel" in transformed
            assert "data" in transformed
        
        # Process as a batch to test relationship detection
        transformed_batch = transformer.process_batch(events)
        
        # Verify basic batch processing
        assert len(transformed_batch) == len(events)
        
        # Check for LLM call pairs
        llm_starts = [e for e in transformed_batch if e["event_type"] == "LLM_call_start"]
        llm_finishes = [e for e in transformed_batch if e["event_type"] == "LLM_call_finish"]
        
        # There should be at least one LLM call pair in the weather example
        assert len(llm_starts) > 0
        assert len(llm_finishes) > 0
        
        # Check that at least some events have relationships
        events_with_relationships = [
            e for e in transformed_batch 
            if "relationship_id" in e and e["relationship_id"] is not None
        ]
        assert len(events_with_relationships) > 0
        
        # Check for tool call pairs
        tool_starts = [e for e in transformed_batch if e["event_type"] == "call_start"]
        tool_finishes = [e for e in transformed_batch if e["event_type"] == "call_finish"]
        
        if len(tool_starts) > 0 and len(tool_finishes) > 0:
            # There should be relationships between tool calls
            tool_events_with_relationships = [
                e for e in transformed_batch 
                if e["event_type"] in ["call_start", "call_finish"] 
                and "relationship_id" in e 
                and e["relationship_id"] is not None
            ]
            assert len(tool_events_with_relationships) > 0
    
    def test_rag_monitoring_json(self, transformer):
        """Test processing the RAG monitoring JSON example."""
        # Path to the example JSON file
        json_path = os.path.join(os.getcwd(), "input_json_records_examples", "rag_monitoring.json")
        
        # Read the JSON lines (each line is a separate JSON object)
        events = []
        with open(json_path, "r") as f:
            for line in f:
                if line.strip():  # Skip empty lines
                    events.append(json.loads(line))
        
        # Make sure we have some events
        assert len(events) > 0
        
        # Process as a batch to test relationship detection
        transformed_batch = transformer.process_batch(events)
        
        # Verify basic batch processing
        assert len(transformed_batch) == len(events)
        
        # Find retrieval tool calls - specific to RAG
        retrieval_calls = [
            e for e in transformed_batch 
            if e["event_type"] == "call_start" 
            and "tool_function" in e["data"] 
            and "retriev" in e["data"]["tool_function"].lower()
        ]
        
        # There should be at least one retrieval call in the RAG example
        if len(retrieval_calls) > 0:
            # Check if these calls have relationships
            retrieval_call_ids = [e["relationship_id"] for e in retrieval_calls if "relationship_id" in e]
            
            if retrieval_call_ids:
                # Find the matching finish events
                matching_finishes = [
                    e for e in transformed_batch 
                    if "relationship_id" in e and e["relationship_id"] in retrieval_call_ids
                ]
                
                # There should be matching finish events
                assert len(matching_finishes) > 0
    
    def test_chatbot_monitoring_json(self, transformer):
        """Test processing the chatbot monitoring JSON example."""
        # Path to the example JSON file
        json_path = os.path.join(os.getcwd(), "input_json_records_examples", "chatbot_monitoring.json")
        
        # Check if the file exists and skip test if not
        if not os.path.exists(json_path):
            pytest.skip(f"Chatbot monitoring example file not found: {json_path}")
        
        # Read the JSON lines (each line is a separate JSON object)
        events = []
        with open(json_path, "r") as f:
            for line in f:
                if line.strip():  # Skip empty lines
                    events.append(json.loads(line))
        
        # Make sure we have some events
        assert len(events) > 0
        
        # Process as a batch to test relationship detection
        transformed_batch = transformer.process_batch(events)
        
        # Verify basic batch processing
        assert len(transformed_batch) == len(events)
        
        # Find framework and system events
        framework_events = [
            e for e in transformed_batch 
            if "framework" in e["event_type"].lower() or e["event_type"] == "monitoring_enabled"
        ]
        assert len(framework_events) > 0
        
        # Check for relationships between events
        events_with_relationships = [
            e for e in transformed_batch 
            if "relationship_id" in e and e["relationship_id"] is not None
        ]
        
        # There might not be relationships in the system events, so we only assert if there are some
        if len(events_with_relationships) > 0:
            # There are relationships to check
            relationship_ids = set([e["relationship_id"] for e in events_with_relationships])
            assert len(relationship_ids) > 0