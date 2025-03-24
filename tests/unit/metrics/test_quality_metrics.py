"""
Unit tests for quality metrics calculators.
"""

import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, UTC

from app.business_logic.metrics.quality_metrics import (
    ResponseComplexityCalculator,
    ResponseAppropriatenessCalculator,
    ContentTypeDistributionCalculator
)


class TestResponseComplexityCalculator(unittest.TestCase):
    """Tests for the ResponseComplexityCalculator class."""
    
    def setUp(self):
        """Set up test data for each test."""
        self.calculator = ResponseComplexityCalculator()
        self.mock_db = MagicMock()
        
        # Create mock response events
        self.mock_events = [
            MagicMock(
                data={
                    "response": {
                        "message": {
                            "content": "This is a short response.",
                            "usage_metadata": {
                                "output_tokens": 10
                            }
                        }
                    }
                }
            ),
            MagicMock(
                data={
                    "response": {
                        "message": {
                            "content": "This is a longer response with multiple sentences. It has more complexity. How about that?",
                            "usage_metadata": {
                                "output_tokens": 25
                            }
                        }
                    }
                }
            ),
            MagicMock(
                data={
                    "content": "Another example. With two sentences.",
                    "llm_output": {
                        "usage": {
                            "output_tokens": 15
                        }
                    }
                }
            ),
        ]
    
    def test_calculate_complexity_metrics(self):
        """Test calculation of complexity metrics."""
        # Mock the get_filtered_events method
        self.calculator.get_filtered_events = MagicMock(return_value=self.mock_events)
        
        # Calculate metrics
        metrics = self.calculator.calculate(self.mock_db)
        
        # Verify metrics
        self.assertEqual(metrics["response_count"], 3)
        self.assertEqual(metrics["responses_with_metrics"], 3)
        
        # Verify average tokens per response
        self.assertAlmostEqual(metrics["average_tokens_per_response"], (10 + 25 + 15) / 3)
        
        # Verify word counts
        expected_word_count = (
            len("This is a short response.".split()) + 
            len("This is a longer response with multiple sentences. It has more complexity. How about that?".split()) +
            len("Another example. With two sentences.".split())
        ) / 3
        self.assertAlmostEqual(metrics["average_word_count"], expected_word_count)
        
        # Verify sentence counts (simplified check)
        self.assertTrue(metrics["average_sentence_count"] > 0)
        self.assertTrue(metrics["average_words_per_sentence"] > 0)


class TestResponseAppropriatenessCalculator(unittest.TestCase):
    """Tests for the ResponseAppropriatenessCalculator class."""
    
    def setUp(self):
        """Set up test data for each test."""
        self.calculator = ResponseAppropriatenessCalculator()
        self.mock_db = MagicMock()
        
        # Create mock response events
        self.mock_events = [
            # Normal response
            MagicMock(
                data={
                    "response": {
                        "message": {
                            "content": "This is a normal response."
                        }
                    }
                }
            ),
            # Error response
            MagicMock(
                data={
                    "response": {
                        "message": {
                            "content": "Error occurred during processing."
                        }
                    },
                    "error": "Some error",
                }
            ),
            # Refusal response
            MagicMock(
                data={
                    "content": "I'm sorry, I cannot provide that information as it's against policy."
                }
            ),
            # Hallucination response
            MagicMock(
                data={
                    "content": "The moon is made of cheese.",
                    "hallucination_detected": True
                }
            ),
        ]
    
    def test_calculate_appropriateness_metrics(self):
        """Test calculation of appropriateness metrics."""
        # Mock the get_filtered_events method
        self.calculator.get_filtered_events = MagicMock(return_value=self.mock_events)
        
        # Calculate metrics
        metrics = self.calculator.calculate(self.mock_db)
        
        # Verify metrics
        self.assertEqual(metrics["response_count"], 4)
        
        # Verify error rate
        self.assertEqual(metrics["error_count"], 1)
        self.assertEqual(metrics["error_response_rate"], 0.25)
        
        # Verify refusal rate
        self.assertEqual(metrics["refusal_count"], 1)
        self.assertEqual(metrics["refusal_rate"], 0.25)
        
        # Verify hallucination rate
        self.assertEqual(metrics["hallucination_count"], 1)
        self.assertEqual(metrics["hallucination_rate"], 0.25)


class TestContentTypeDistributionCalculator(unittest.TestCase):
    """Tests for the ContentTypeDistributionCalculator class."""
    
    def setUp(self):
        """Set up test data for each test."""
        self.calculator = ContentTypeDistributionCalculator()
        self.mock_db = MagicMock()
        
        # Create mock response events
        self.mock_events = [
            # Code response
            MagicMock(
                data={
                    "content": "Here's an example:\n```python\ndef hello():\n    print('Hello')\n```"
                }
            ),
            # URL response
            MagicMock(
                data={
                    "content": "Check out this link: https://example.com"
                }
            ),
            # List response
            MagicMock(
                data={
                    "content": "Here are some items:\n- Item 1\n- Item 2\n- Item 3"
                }
            ),
            # JSON response
            MagicMock(
                data={
                    "content": '{\n  "name": "Example",\n  "value": 123\n}'
                }
            ),
            # Plain text response
            MagicMock(
                data={
                    "content": "Just a simple text response."
                }
            ),
        ]
    
    def test_calculate_content_type_metrics(self):
        """Test calculation of content type metrics."""
        # Mock the get_filtered_events method
        self.calculator.get_filtered_events = MagicMock(return_value=self.mock_events)
        
        # Calculate metrics
        metrics = self.calculator.calculate(self.mock_db)
        
        # Verify metrics
        self.assertEqual(metrics["response_count"], 5)
        
        # Verify content type counts
        self.assertEqual(metrics["code_count"], 1)
        self.assertEqual(metrics["url_count"], 1)
        self.assertEqual(metrics["list_count"], 1)
        self.assertEqual(metrics["json_count"], 1)
        
        # Verify rates
        self.assertEqual(metrics["code_rate"], 0.2)
        self.assertEqual(metrics["url_rate"], 0.2)
        self.assertEqual(metrics["list_rate"], 0.2)
        self.assertEqual(metrics["json_rate"], 0.2)


if __name__ == "__main__":
    unittest.main() 