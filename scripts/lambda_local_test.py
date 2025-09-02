#!/usr/bin/env python3
"""
Local testing script for the Lambda handler.
This allows testing the Lambda function locally before deployment.
"""

import json
import os
import sys
from lambda_handler import lambda_handler

# Test events
TEST_EVENTS = {
    "health_check": {
        "httpMethod": "GET",
        "path": "/health",
        "headers": {},
        "body": None
    },
    
    "optimize_simple": {
        "httpMethod": "POST",
        "path": "/optimize",
        "headers": {
            "X-Api-Key": "test-key"
        },
        "body": json.dumps({
            "query": "preference action trustee"
        })
    },
    
    "optimize_with_options": {
        "httpMethod": "POST",
        "path": "/optimize",
        "headers": {
            "X-Api-Key": "test-key"
        },
        "body": json.dumps({
            "query": "section 363 sale",
            "options": {
                "version": 3,
                "include_changes": True
            }
        })
    },
    
    "batch_optimize": {
        "httpMethod": "POST",
        "path": "/optimize/batch",
        "headers": {
            "X-Api-Key": "test-key"
        },
        "body": json.dumps({
            "queries": [
                "preference action",
                "Till v. SCS Credit",
                "section 547"
            ],
            "options": {
                "version": 2
            }
        })
    },
    
    "consultants_list": {
        "httpMethod": "GET",
        "path": "/consultants",
        "headers": {
            "X-Api-Key": "test-key"
        },
        "body": None
    },
    
    "invalid_request": {
        "httpMethod": "POST",
        "path": "/optimize",
        "headers": {
            "X-Api-Key": "test-key"
        },
        "body": json.dumps({
            "invalid": "request"
        })
    }
}


def test_endpoint(name: str, event: dict):
    """Test a single endpoint."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"Method: {event['httpMethod']} {event['path']}")
    if event.get('body'):
        print(f"Body: {event['body'][:100]}...")
    print(f"{'='*60}")
    
    try:
        # Call the Lambda handler
        response = lambda_handler(event, None)
        
        # Print response
        print(f"Status: {response['statusCode']}")
        print(f"Headers: {json.dumps(response['headers'], indent=2)}")
        
        # Parse and pretty print body
        if response.get('body'):
            body = json.loads(response['body'])
            print(f"Body: {json.dumps(body, indent=2)}")
        
        # Check if request was successful
        if response['statusCode'] == 200:
            print(f"\n✅ {name} - SUCCESS")
        else:
            print(f"\n❌ {name} - FAILED (Status: {response['statusCode']})")
            
    except Exception as e:
        print(f"\n❌ {name} - ERROR: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests or specific test."""
    # Check for API key; fallback to .env if missing
    if not os.getenv("OPENAI_API_KEY"):
        try:
            from dotenv import load_dotenv, find_dotenv
            load_dotenv(find_dotenv(), override=False)
        except Exception:
            pass
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set (you can add it to a .env file)")
        sys.exit(1)
    
    # Parse arguments
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        if test_name in TEST_EVENTS:
            test_endpoint(test_name, TEST_EVENTS[test_name])
        else:
            print(f"Unknown test: {test_name}")
            print(f"Available tests: {', '.join(TEST_EVENTS.keys())}")
            sys.exit(1)
    else:
        # Run all tests
        print("Running all tests...")
        for name, event in TEST_EVENTS.items():
            test_endpoint(name, event)
        
        print("\n" + "="*60)
        print("All tests completed!")


if __name__ == "__main__":
    main()
