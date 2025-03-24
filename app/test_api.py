#!/usr/bin/env python3
"""
API test script for Cylestio metrics endpoints.

This script demonstrates how to use all the metrics endpoints in the Cylestio API.
"""

import requests
import sys
import json
from datetime import datetime, timedelta
import argparse

def test_metrics_endpoints(base_url="http://localhost:9999"):
    """Test all metrics endpoints and print the results."""
    
    # Set up common parameters
    params = {
        "start_time": (datetime.now() - timedelta(days=7)).isoformat(),
        "end_time": datetime.now().isoformat()
    }
    
    # Define all endpoints to test
    endpoints = [
        # Test endpoint
        "/api/v1/metrics/test",
        
        # Performance metrics
        "/api/v1/metrics/response_time/average",
        "/api/v1/metrics/response_time/percentiles",
        "/api/v1/metrics/response_time/trend",
        
        # Token usage metrics
        "/api/v1/metrics/token_usage/total",
        "/api/v1/metrics/token_usage/average",
        "/api/v1/metrics/token_usage/by_model",
        
        # Security metrics
        "/api/v1/metrics/security/alerts/count",
        "/api/v1/metrics/security/risk_level",
        "/api/v1/metrics/security/alerts/by_category",
        "/api/v1/metrics/security/alerts/trend",
        
        # Usage metrics
        "/api/v1/metrics/usage/requests/by_agent",
        "/api/v1/metrics/usage/frameworks/distribution", 
        "/api/v1/metrics/usage/events/distribution",
        "/api/v1/metrics/usage/sessions/count"
    ]
    
    results = {}
    
    print("Testing Cylestio metrics API endpoints:")
    print("-" * 50)
    
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        print(f"Testing endpoint: {endpoint}")
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            results[endpoint] = {
                "status": response.status_code,
                "data": response.json()
            }
            print(f"  ✅ Success! Status: {response.status_code}")
        except requests.exceptions.RequestException as e:
            results[endpoint] = {
                "status": getattr(e.response, 'status_code', None),
                "error": str(e)
            }
            print(f"  ❌ Error: {str(e)}")
            
        # Add a separator line
        print("-" * 50)
    
    return results

def main():
    """Main function to run the API test."""
    parser = argparse.ArgumentParser(description="Test Cylestio metrics API endpoints")
    parser.add_argument("--url", default="http://localhost:9999", help="Base URL for the API")
    parser.add_argument("--output", help="Output file for results (JSON)")
    
    args = parser.parse_args()
    
    results = test_metrics_endpoints(args.url)
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to {args.output}")

if __name__ == "__main__":
    main() 