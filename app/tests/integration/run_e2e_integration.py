#!/usr/bin/env python3
"""
End-to-End Integration Test for Cylestio Mini-Local Server

This script simulates the complete flow of telemetry data through the system:
1. Starts the server (if not already running)
2. Reads example telemetry records
3. Sends them one by one to the telemetry API
4. Queries the API to verify data storage and transformation
5. Simulates dashboard queries
"""

import asyncio
import json
import os
import sys
import time
import requests
import subprocess
import signal
from pathlib import Path
import argparse
import platform
from datetime import datetime, timedelta
import traceback
import random
from typing import List, Dict, Any, Optional

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

# Configuration
BASE_URL = "http://localhost:8000"
SERVER_HOST = "localhost"
SERVER_PORT = 8000
AGENT_ID = "test-agent"  # Will be updated in runtime

async def start_server(use_test_db=True):
    """Start the server process for testing."""
    print("Starting test server...")
    
    # Determine the server script path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    server_script = os.path.join(script_dir, "../../../run.py")
    
    # Prepare environment variables
    env = os.environ.copy()
    if use_test_db:
        test_db_path = os.path.join(script_dir, "../../../data/test_db.sqlite")
        # Ensure the directory exists
        os.makedirs(os.path.dirname(test_db_path), exist_ok=True)
        
        # Delete the test database if it exists
        if os.path.exists(test_db_path):
            print(f"Removing existing test database at {test_db_path}")
            os.remove(test_db_path)
            
        env["DATABASE_URL"] = f"sqlite:///{test_db_path}"
        print(f"Using test database: {env['DATABASE_URL']}")
    
    # Start the server
    cmd = [sys.executable, server_script]
    try:
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        print(f"Server process started with PID {process.pid}")
        return process
    except Exception as e:
        print(f"Failed to start server: {e}")
        raise

async def wait_for_server(max_retries=30, retry_delay=1.0):
    """Wait for the server to be ready."""
    print("Waiting for server to be ready...", end="", flush=True)
    
    for attempt in range(max_retries):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=1)
            if response.status_code == 200:
                server_time = response.json().get("server_time")
                print(f"\nServer is ready! Server time: {server_time}")
                return True
        except requests.RequestException:
            print(".", end="", flush=True)
            await asyncio.sleep(retry_delay)
    
    print("\nServer failed to start within the expected time")
    raise Exception("Server failed to start within the expected time")

async def test_server_time():
    """Test the server's health endpoint and return the server time."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            server_time = response.json().get("server_time")
            print(f"Server time: {server_time}")
            return server_time
        else:
            raise Exception(f"Health check failed with status code {response.status_code}")
    except requests.RequestException as e:
        raise Exception(f"Health check request failed: {e}")

async def test_telemetry_ingestion():
    """Test ingesting telemetry events."""
    print("\nTesting telemetry ingestion...")
    
    # Generate test telemetry events
    num_events = 50
    telemetry_events = []
    
    # Create a mix of events and metrics
    event_types = ["system_start", "login", "logout", "error", "warning", "info"]
    
    for i in range(num_events):
        event_type = random.choice(event_types)
        
        # Generate a timestamp within last hour
        timestamp = (datetime.utcnow() - timedelta(minutes=random.randint(1, 60))).isoformat()
        
        # Create event data
        event_data = {
            "agent_id": AGENT_ID,
            "event_type": event_type,
            "timestamp": timestamp,
            "data": {
                "test_id": i,
                "severity": random.choice(["low", "medium", "high"]),
                "message": f"Test event {i} of type {event_type}",
                "value": random.randint(1, 100)
            }
        }
        telemetry_events.append(event_data)
    
    # Send the events
    print(f"Sending {num_events} telemetry events...")
    
    # Only use versioned API - no need for backward compatibility
    api_path = "/api/v1/telemetry"
    success_count = 0
    errors = []
    
    for i, event in enumerate(telemetry_events):
        try:
            url = f"{BASE_URL}{api_path}"
            response = requests.post(url, json=event, timeout=5)
            
            if response.status_code == 200 or response.status_code == 201:
                success_count += 1
            else:
                errors.append(f"Event {i}: Status {response.status_code} - {response.text}")
        except requests.RequestException as e:
            errors.append(f"Event {i}: Request error - {str(e)}")
    
    success_rate = (success_count / num_events) * 100
    print(f"  {api_path}: {success_count}/{num_events} events sent successfully ({success_rate:.1f}%)")
    
    if success_count == 0:
        raise Exception("Failed to send any telemetry events to API endpoint")
    
    print(f"Telemetry ingestion complete")
    return success_count

async def test_events_query():
    """Test querying events."""
    print("\nTesting events query...")
    
    # Get events for our test agent
    start_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    
    # Only use versioned API - no need for backward compatibility
    api_path = f"/api/v1/agents/{AGENT_ID}/events"
    
    try:
        url = f"{BASE_URL}{api_path}"
        response = requests.get(
            url,
            params={"start_time": start_time},
            timeout=5
        )
        
        if response.status_code == 200:
            events = response.json()
        else:
            raise Exception(f"Query failed with status {response.status_code}")
    except requests.RequestException as e:
        raise Exception(f"Request error: {str(e)}")
    
    print(f"  {api_path}: Retrieved {len(events)} events")
    
    # Print some sample events
    if events:
        print("  Sample events:")
        for i, event in enumerate(events[:3]):
            print(f"    Event {i+1}: Type={event.get('event_type')}, Time={event.get('timestamp')}")
    
    print("Events query test completed")
    return events

async def test_dashboard_query():
    """Test querying metrics for dashboard."""
    print("\nTesting dashboard/metrics query...")
    
    # Get metrics for our test agent
    start_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    end_time = datetime.utcnow().isoformat()
    
    # Only use versioned API - no need for backward compatibility
    api_path = f"/api/v1/agents/{AGENT_ID}/metrics"
    
    try:
        url = f"{BASE_URL}{api_path}"
        response = requests.get(
            url,
            params={
                "start_time": start_time,
                "end_time": end_time,
                "agent_id": AGENT_ID
            },
            timeout=5
        )
        
        if response.status_code == 200:
            metrics = response.json()
        else:
            # Try dashboard endpoint as fallback
            api_path = f"/api/v1/dashboard/metrics"
            url = f"{BASE_URL}{api_path}"
            response = requests.get(
                url,
                params={
                    "start_time": start_time,
                    "end_time": end_time
                },
                timeout=5
            )
            
            if response.status_code == 200:
                metrics = response.json()
            else:
                raise Exception(f"Dashboard query failed: {response.status_code}")
    except requests.RequestException as e:
        raise Exception(f"Request error: {str(e)}")
    
    # Print metric information
    print(f"  {api_path}: Retrieved metric data")
    
    # Show some sample metrics if available
    try:
        if isinstance(metrics, list) and metrics:
            print(f"  Retrieved {len(metrics)} metrics")
            print("  Sample metrics:")
            for i, metric in enumerate(metrics[:3]):
                print(f"    Metric {i+1}: {metric}")
        elif isinstance(metrics, dict):
            print("  Metrics data structure:")
            for key, value in metrics.items():
                if isinstance(value, list):
                    print(f"    {key}: {len(value)} items")
                else:
                    print(f"    {key}: {type(value).__name__}")
    except Exception as e:
        print(f"  Error processing metrics: {e}")
    
    print("Dashboard query test completed")
    return metrics

async def test_error_handling():
    """Test error handling with invalid requests."""
    print("Testing error handling...")
    
    invalid_payloads = [
        {},  # Empty payload
        {"incomplete": "data"},  # Missing required fields
        {"agent_id": "test", "event_type": "test", "timestamp": "invalid-date"}  # Invalid data type
    ]

    # Only use versioned API - no need for backward compatibility
    api_path = "/api/v1/telemetry"
    
    for i, payload in enumerate(invalid_payloads):
        try:
            url = f"{BASE_URL}{api_path}"
            response = requests.post(
                url,
                json=payload,
                timeout=5
            )
            
            if response.status_code >= 400:
                print(f"Invalid payload {i+1}/{len(invalid_payloads)}: Server correctly returned {response.status_code}")
            else:
                print(f"Error test failed: Server accepted invalid payload {i+1}/{len(invalid_payloads)}")
        
        except requests.RequestException as e:
            print(f"Request error with invalid payload {i+1}/{len(invalid_payloads)}: {e}")
    
    print("Error handling test completed")

async def test_api_versioning():
    """Test API versioned endpoints to ensure they're working correctly."""
    print("\nTesting API v1 endpoints...")
    
    # Test the versioned endpoints
    versioned_endpoints = {
        "Telemetry": "/api/v1/telemetry",
        "Events": f"/api/v1/agents/{AGENT_ID}/events",
        "Metrics": f"/api/v1/agents/{AGENT_ID}/metrics"
    }
    
    for endpoint_type, path in versioned_endpoints.items():
        try:
            url = f"{BASE_URL}{path}"
            if endpoint_type == "Telemetry":
                # For telemetry endpoints, send a POST request
                response = requests.post(
                    url,
                    json={"agent_id": AGENT_ID, "event_type": "test_version", 
                          "timestamp": datetime.utcnow().isoformat(), "data": {"test": True}},
                    timeout=5
                )
            else:
                # For retrieval endpoints, send a GET request
                response = requests.get(
                    url,
                    params={"start_time": (datetime.utcnow() - timedelta(hours=1)).isoformat()},
                    timeout=5
                )
            
            if response.status_code < 400:
                print(f"  ✅ {endpoint_type} ({path}): OK ({response.status_code})")
            else:
                print(f"  ❌ {endpoint_type} ({path}): Failed ({response.status_code})")
        except requests.RequestException as e:
            print(f"  ❌ {endpoint_type} ({path}): Request error: {e}")
    
    print("\nAPI endpoint testing completed")

async def time_function(func):
    """Execute a function and return the elapsed time in seconds."""
    start = time.time()
    await func()
    return time.time() - start

async def run_integration_test(use_test_db=True, start_new_server=True):
    """Run the full integration test."""
    
    start_time = datetime.now()
    print(f"\n{'-'*80}")
    print(f" STARTING INTEGRATION TEST AT {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'-'*80}")
    
    if start_new_server:
        server_process = await start_server(use_test_db)
    else:
        server_process = None
        print("Using existing server, no new server started")
    
    try:
        print(f"\nSystem information: {platform.system()} {platform.release()}")
        print(f"Python version: {platform.python_version()}")
        
        # Generate a unique agent ID for this test run
        global AGENT_ID
        AGENT_ID = f"test-agent-{int(time.time())}"
        print(f"Using test agent ID: {AGENT_ID}")
        
        # Wait for server to start
        await wait_for_server()
        
        # Run the individual test functions
        print("\nRunning individual tests:")
        print(f"{'-'*40}")
        
        server_time = await test_server_time()
        
        telemetry_timing = await time_function(test_telemetry_ingestion)
        
        # Allow time for data to be processed
        await asyncio.sleep(1)
        
        events_timing = await time_function(test_events_query)
        dashboard_timing = await time_function(test_dashboard_query)
        error_timing = await time_function(test_error_handling)
        versioning_timing = await time_function(test_api_versioning)
        
        # Report test timings
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        print(f"\n{'-'*80}")
        print(f" TEST PERFORMANCE SUMMARY ")
        print(f"{'-'*80}")
        print(f"Telemetry ingestion: {telemetry_timing:.2f} seconds")
        print(f"Events query: {events_timing:.2f} seconds")
        print(f"Dashboard query: {dashboard_timing:.2f} seconds")
        print(f"Error handling: {error_timing:.2f} seconds")
        print(f"API versioning: {versioning_timing:.2f} seconds")
        print(f"Total test time: {total_time:.2f} seconds")
        
        print(f"\n✅ All tests completed successfully!")
        print(f"Test finished at {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        traceback.print_exc()
        return False
    finally:
        if server_process:
            print("\nShutting down test server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
                print("Server shutdown complete")
            except subprocess.TimeoutExpired:
                print("Server didn't shut down gracefully, forcing...")
                server_process.kill()
    
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run end-to-end integration tests for the Cylestio Mini-Local Server")
    parser.add_argument("--use-existing-server", action="store_true", help="Use an existing server instead of starting a new one")
    parser.add_argument("--production-db", action="store_true", help="Use the production database instead of a test database")
    args = parser.parse_args()
    
    # Run the integration test
    success = asyncio.run(run_integration_test(
        use_test_db=not args.production_db,
        start_new_server=not args.use_existing_server
    ))
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1) 