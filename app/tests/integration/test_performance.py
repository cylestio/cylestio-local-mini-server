"""
Performance tests for the Cylestio Monitor.

These tests evaluate:
1. Extraction performance with batch processing
2. API response times
3. Performance under load
"""

import pytest
import json
import os
import time
import random
import asyncio
from datetime import datetime, timedelta
from httpx import AsyncClient
import statistics
from typing import List, Dict, Any

from app.main import app
from app.dependencies import get_db
from app.business_logic.event_processor import EventProcessor
from app.models.event import Event
from app.schemas.event import EventCreate


class TestPerformance:
    """Performance tests for extraction pipeline and APIs."""
    
    @pytest.fixture
    def example_records(self):
        """Load example records from the resources directory."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        example_file = os.path.join(
            script_dir, 
            "../../../resources/example_input_json_records/example_input_json_records.json"
        )
        
        # Read the file line by line as it contains one JSON object per line
        records = []
        with open(example_file, 'r') as f:
            for line in f:
                if line.strip():  # Skip empty lines
                    try:
                        record = json.loads(line)
                        records.append(record)
                    except json.JSONDecodeError as e:
                        print(f"Error parsing JSON: {e}")
        
        return records
    
    @pytest.fixture
    async def event_processor(self):
        """Create an event processor instance."""
        return EventProcessor()
    
    @pytest.fixture
    async def populated_db(self, example_records):
        """Populate the database with example records."""
        records = []
        agent_ids = []
        
        async for db in get_db():
            # First clear any existing data
            await db.execute("DELETE FROM performance_metrics")
            await db.execute("DELETE FROM token_usage")
            await db.execute("DELETE FROM model_details")
            await db.execute("DELETE FROM security_alerts")
            await db.execute("DELETE FROM framework_details")
            await db.execute("DELETE FROM events")
            await db.execute("DELETE FROM sessions")
            await db.commit()
            
            # Process example records
            processor = EventProcessor()
            
            for record in example_records:
                # Create an event from the record
                event_create = EventCreate(
                    timestamp=record.get("timestamp"),
                    level=record.get("level", "INFO"),
                    agent_id=record.get("agent_id"),
                    event_type=record.get("event_type"),
                    channel=record.get("channel", "UNKNOWN"),
                    session_id=record.get("session_id"),
                    data=record
                )
                
                # Save to database
                event = Event(**event_create.model_dump())
                db.add(event)
                await db.commit()
                await db.refresh(event)
                
                # Process through extractors
                await processor.process_event(event, db)
                records.append(event)
                
                if event.agent_id not in agent_ids:
                    agent_ids.append(event.agent_id)
            
            # Return info about populated data
            return {
                "record_count": len(records),
                "agent_ids": agent_ids
            }
    
    @pytest.mark.asyncio
    async def test_batch_processing_performance(self, example_records, event_processor):
        """Test the performance of batch processing events."""
        batch_sizes = [1, 5, 10, 20, 50]
        results = {}
        
        async for db in get_db():
            # Prepare data
            events = []
            for record in example_records:
                event_create = EventCreate(
                    timestamp=record.get("timestamp"),
                    level=record.get("level", "INFO"),
                    agent_id=record.get("agent_id"),
                    event_type=record.get("event_type"),
                    channel=record.get("channel", "UNKNOWN"),
                    session_id=record.get("session_id"),
                    data=record
                )
                
                event = Event(**event_create.model_dump())
                events.append(event)
            
            # Test different batch sizes
            for batch_size in batch_sizes:
                # Skip if we don't have enough events
                if len(events) < batch_size:
                    continue
                    
                # Select a random batch of events
                batch = random.sample(events, batch_size)
                
                # Measure processing time
                start_time = time.time()
                processed_events = await event_processor.process_events(batch, db)
                end_time = time.time()
                
                processing_time = end_time - start_time
                events_per_second = batch_size / processing_time if processing_time > 0 else 0
                
                # Store results
                results[batch_size] = {
                    "processing_time_seconds": processing_time,
                    "events_per_second": events_per_second
                }
                
                print(f"Batch size {batch_size}: {processing_time:.4f} seconds, {events_per_second:.2f} events/sec")
        
        # Assert we have results
        assert results
        
        # Verify that we're processing at a reasonable rate
        # This is just a basic sanity check - adjust based on expected performance
        for batch_size, perf in results.items():
            if batch_size > 1:  # Only check for batch sizes > 1
                assert perf["events_per_second"] > 0.5, f"Processing too slow for batch size {batch_size}"
    
    @pytest.mark.asyncio
    async def test_api_response_times(self, populated_db):
        """Test the response times of various API endpoints."""
        endpoints = [
            "/api/v1/events?limit=10",
            "/api/v1/agents",
            f"/api/v1/events?agent_id={populated_db['agent_ids'][0]}&limit=10",
            f"/api/v1/metrics/token-usage?agent_id={populated_db['agent_ids'][0]}&timeframe=day",
            f"/api/v1/metrics/latency?agent_id={populated_db['agent_ids'][0]}&timeframe=day",
            f"/api/v1/metrics/request-volume?agent_id={populated_db['agent_ids'][0]}&timeframe=day"
        ]
        
        results = {}
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            for endpoint in endpoints:
                response_times = []
                
                # Make multiple calls to get an average
                for _ in range(5):
                    start_time = time.time()
                    response = await client.get(endpoint)
                    end_time = time.time()
                    
                    assert response.status_code == 200
                    response_times.append(end_time - start_time)
                
                # Calculate stats
                avg_time = statistics.mean(response_times)
                max_time = max(response_times)
                min_time = min(response_times)
                
                results[endpoint] = {
                    "avg_response_time": avg_time,
                    "min_response_time": min_time,
                    "max_response_time": max_time
                }
                
                print(f"Endpoint {endpoint}: avg={avg_time:.4f}s, min={min_time:.4f}s, max={max_time:.4f}s")
        
        # Assert we have results
        assert results
        
        # Verify reasonable response times (adjust thresholds as needed)
        for endpoint, times in results.items():
            assert times["avg_response_time"] < 1.0, f"Average response time too slow for {endpoint}"
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_performance(self, populated_db):
        """Test performance under concurrent load."""
        base_endpoints = [
            "/api/v1/events?limit=10",
            "/api/v1/agents",
            f"/api/v1/metrics/token-usage?agent_id={populated_db['agent_ids'][0]}&timeframe=day"
        ]
        
        # Create a list of endpoints by repeating the base endpoints
        endpoints = base_endpoints * 5  # 15 total requests
        
        async def make_request(client, endpoint):
            """Make a request and return the response time."""
            start_time = time.time()
            response = await client.get(endpoint)
            end_time = time.time()
            return end_time - start_time
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Make requests concurrently
            start_time = time.time()
            tasks = [make_request(client, endpoint) for endpoint in endpoints]
            response_times = await asyncio.gather(*tasks)
            end_time = time.time()
            
            total_time = end_time - start_time
            avg_time = statistics.mean(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            
            print(f"Concurrent requests: total={total_time:.4f}s, avg={avg_time:.4f}s, min={min_time:.4f}s, max={max_time:.4f}s")
            
            # If these were sequential, total time would be sum(response_times)
            # Concurrent should be much faster
            sequential_time = sum(response_times)
            
            print(f"Sequential time would be {sequential_time:.4f}s, concurrent is {total_time:.4f}s")
            print(f"Speedup factor: {sequential_time/total_time:.2f}x")
            
            assert total_time < sequential_time, "Concurrent requests should be faster than sequential"
            # Expect at least 2x speedup from concurrency (adjust if needed)
            assert sequential_time / total_time > 2.0, "Not getting enough speedup from concurrent requests"
    
    @pytest.mark.asyncio
    async def test_database_query_performance(self, populated_db):
        """Test the performance of common database queries."""
        queries = [
            "SELECT COUNT(*) FROM events",
            "SELECT COUNT(*) FROM model_details",
            "SELECT COUNT(*) FROM token_usage",
            "SELECT COUNT(*) FROM events WHERE agent_id = :agent_id",
            "SELECT COUNT(*) FROM events WHERE event_type = 'model_request'",
            "SELECT COUNT(*) FROM events WHERE event_type = 'model_response'",
            "SELECT COUNT(*) FROM events WHERE timestamp > :recent_time"
        ]
        
        results = {}
        recent_time = (datetime.now() - timedelta(days=30)).isoformat()
        
        async for db in get_db():
            for query in queries:
                params = {}
                if ":agent_id" in query:
                    params["agent_id"] = populated_db["agent_ids"][0]
                if ":recent_time" in query:
                    params["recent_time"] = recent_time
                
                # Measure query time
                start_time = time.time()
                await db.execute(query, params)
                end_time = time.time()
                
                query_time = end_time - start_time
                results[query] = query_time
                
                print(f"Query: {query}, Time: {query_time:.4f}s")
        
        # Assert we have results
        assert results
        
        # Verify reasonable query times (adjust thresholds as needed)
        for query, time_taken in results.items():
            assert time_taken < 0.5, f"Query too slow: {query}" 