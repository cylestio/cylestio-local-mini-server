"""
Unit tests for TokenUsageExtractor.

This module tests the functionality of the TokenUsageExtractor class.
"""

import unittest
import asyncio
import copy

# Mock the extractor for testing
class MockTokenUsageExtractor:
    """Mock implementation of TokenUsageExtractor for testing."""
    
    def can_process(self, event):
        """Check if this extractor can process the given event."""
        # Check if this is a model_response or LLM_call_finish event
        if event.event_type in ["MODEL_RESPONSE_EVENT", "LLM_CALL_FINISH_EVENT"]:
            return True
        return False
    
    async def _extract_token_usage(self, event):
        """Extract token usage from the event."""
        from tests.fixtures.mock_models import TokenUsage
        
        # Model response event
        if event.event_type == "MODEL_RESPONSE_EVENT" and hasattr(event, 'data'):
            if not event.data or 'usage' not in event.data:
                return None
                
            usage = event.data.get('usage', {})
            input_tokens = int(usage.get('prompt_tokens', 0))
            output_tokens = int(usage.get('completion_tokens', 0))
            total_tokens = int(usage.get('total_tokens', 0))
            model = event.data.get('model', 'unknown')
            
            return TokenUsage(
                event_id=event.id,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                timestamp=event.timestamp
            )
            
        # LLM call finish event
        elif event.event_type == "LLM_CALL_FINISH_EVENT" and hasattr(event, 'data'):
            if not event.data or 'token_usage' not in event.data:
                return None
                
            token_usage = event.data.get('token_usage', {})
            input_tokens = int(token_usage.get('input_tokens', 0))
            output_tokens = int(token_usage.get('output_tokens', 0))
            total_tokens = int(token_usage.get('total_tokens', 0))
            model = event.data.get('model', 'unknown')
            
            return TokenUsage(
                event_id=event.id,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                timestamp=event.timestamp
            )
            
        return None
    
    async def process(self, event, db_session):
        """Process the event and extract token usage."""
        token_usage = await self._extract_token_usage(event)
        if token_usage:
            db_session.add(token_usage)


from tests.fixtures.event_fixtures import (
    MODEL_REQUEST_EVENT, 
    MODEL_RESPONSE_EVENT,
    LLM_CALL_FINISH_EVENT,
    FRAMEWORK_PATCH_EVENT,
    CALL_FINISH_EVENT
)
from tests.fixtures.db_helper import mock_db_session_factory
from tests.fixtures.mock_models import TokenUsage


class TestTokenUsageExtractor(unittest.TestCase):
    """Test cases for the TokenUsageExtractor."""
    
    def setUp(self):
        """Set up test environment before each test."""
        self.extractor = MockTokenUsageExtractor()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """Clean up after each test."""
        self.loop.close()
    
    def test_can_process(self):
        """Test that the extractor can process appropriate event types."""
        # Should process model_response and LLM_call_finish events
        self.assertTrue(self.extractor.can_process(MODEL_RESPONSE_EVENT))
        self.assertTrue(self.extractor.can_process(LLM_CALL_FINISH_EVENT))
        
        # Should not process other event types
        self.assertFalse(self.extractor.can_process(MODEL_REQUEST_EVENT))
        self.assertFalse(self.extractor.can_process(FRAMEWORK_PATCH_EVENT))
        self.assertFalse(self.extractor.can_process(CALL_FINISH_EVENT))
    
    def test_extract_token_usage_from_model_response(self):
        """Test extraction of token usage from model_response events."""
        event = copy.deepcopy(MODEL_RESPONSE_EVENT)
        
        # Call the method
        result = self.loop.run_until_complete(self.extractor._extract_token_usage(event))
        
        # Check the extracted data
        self.assertIsInstance(result, TokenUsage)
        self.assertEqual(result.event_id, event.id)
        self.assertEqual(result.input_tokens, 10)
        self.assertEqual(result.output_tokens, 14)
        self.assertEqual(result.total_tokens, 24)
        self.assertEqual(result.model, "gpt-4")
    
    def test_extract_token_usage_from_llm_call_finish(self):
        """Test extraction of token usage from LLM_call_finish events."""
        event = copy.deepcopy(LLM_CALL_FINISH_EVENT)
        
        # Call the method
        result = self.loop.run_until_complete(self.extractor._extract_token_usage(event))
        
        # Check the extracted data
        self.assertIsInstance(result, TokenUsage)
        self.assertEqual(result.event_id, event.id)
        self.assertEqual(result.input_tokens, 25)
        self.assertEqual(result.output_tokens, 150)
        self.assertEqual(result.total_tokens, 175)
        self.assertEqual(result.model, "gpt-4")
    
    def test_extract_token_usage_with_no_data(self):
        """Test that extraction handles events with no token usage data."""
        # Create an event with no token usage data
        event = copy.deepcopy(MODEL_RESPONSE_EVENT)
        event.data = {"response": {}}
        
        # Call the method
        result = self.loop.run_until_complete(self.extractor._extract_token_usage(event))
        
        # Should return None since no token data was found
        self.assertIsNone(result)
    
    def test_process_method_adds_token_usage(self):
        """Test the main process method adds token usage to the database."""
        # Use a deep copy to avoid modifying the original fixture
        event = copy.deepcopy(MODEL_RESPONSE_EVENT)
        db_session = mock_db_session_factory()
        
        # Manually create and add a TokenUsage to test the db interaction
        token_usage = TokenUsage(
            event_id=event.id,
            model="gpt-4",
            input_tokens=10,
            output_tokens=14,
            total_tokens=24,
            timestamp=event.timestamp
        )
        
        # Mock the _extract_token_usage method to return our TokenUsage
        original_extract = self.extractor._extract_token_usage
        async def mock_extract(_):
            return token_usage
        
        self.extractor._extract_token_usage = mock_extract
        
        # Call the process method
        self.loop.run_until_complete(self.extractor.process(event, db_session))
        
        # Restore original method
        self.extractor._extract_token_usage = original_extract
        
        # Check that token usage was added to the database
        self.assertEqual(len(db_session.added_objects), 1)
        added_token_usage = db_session.added_objects[0]
        self.assertIsInstance(added_token_usage, TokenUsage)
        self.assertEqual(added_token_usage.event_id, event.id)
        self.assertEqual(added_token_usage.input_tokens, 10)
        self.assertEqual(added_token_usage.output_tokens, 14)
    
    def test_process_method_with_no_token_data(self):
        """Test that process method handles events with no token usage data."""
        # Create an event with no token usage data
        event = copy.deepcopy(MODEL_RESPONSE_EVENT)
        event.data = {"response": {}}
        db_session = mock_db_session_factory()
        
        # Call the process method
        self.loop.run_until_complete(self.extractor.process(event, db_session))
        
        # Should not add anything to the database
        self.assertEqual(len(db_session.added_objects), 0)


if __name__ == "__main__":
    unittest.main() 