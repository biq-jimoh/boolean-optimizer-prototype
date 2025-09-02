"""
AWS Lambda handler for the Bankruptcy Query Optimizer API.

This module provides the Lambda function handler that integrates with API Gateway
to expose the query optimization functionality as a RESTful API.
"""

import json
import asyncio
import os
import logging
import time
import uuid
from typing import Dict, Any, Optional
from pathlib import Path

from bankruptcy_query_optimizer import BankruptcyQueryOptimizer

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Global optimizer instance (persists across warm invocations)
_optimizer: Optional[BankruptcyQueryOptimizer] = None


def get_optimizer() -> BankruptcyQueryOptimizer:
    """
    Get or create the optimizer instance.
    This helps with Lambda warm starts by reusing the instance.
    """
    global _optimizer
    if _optimizer is None:
        logger.info("Initializing optimizer (cold start)")
        _optimizer = BankruptcyQueryOptimizer(
            consultants_dir=os.environ.get('CONSULTANTS_DIR', 'prompts/consultants'),
            executive_path=os.environ.get('EXECUTIVE_PATH', 'prompts/executive/executive-agent.txt'),
            model=os.environ.get('MODEL', 'gpt-5'),
            temperature=float(os.environ.get('TEMPERATURE', '0.0')),
            enable_logging=False,  # Disable internal logging for Lambda
            brave_api_key=os.environ.get('BRAVE_SEARCH_API_KEY')
        )
        logger.info("Optimizer initialized successfully")
    return _optimizer


def create_response(status_code: int, body: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Create a properly formatted API Gateway response."""
    response = {
        'statusCode': status_code,
        'body': json.dumps(body),
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',  # Configure CORS as needed
            'Access-Control-Allow-Headers': 'Content-Type,X-Api-Key',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        }
    }
    
    if headers:
        response['headers'].update(headers)
    
    return response


def validate_request(body: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """Validate the request body."""
    if not body:
        return False, "Request body is required"
    
    if 'query' not in body:
        return False, "Query field is required"
    
    query = body.get('query', '').strip()
    if not query:
        return False, "Query cannot be empty"
    
    if len(query) > 1000:  # Reasonable limit
        return False, "Query too long (max 1000 characters)"
    
    return True, None


async def process_single_query(optimizer: BankruptcyQueryOptimizer, query: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single query with the given options."""
    request_id = str(uuid.uuid4())
    logger.info(f"Processing query: {request_id} - '{query[:50]}...'")
    
    start_time = time.time()
    
    try:
        # Run optimization
        result = await optimizer.optimize_query(query)
        
        # Format response based on options
        response = {
            'request_id': request_id,
            'original_query': query,
            'execution_time': f"{time.time() - start_time:.2f}s",
            'active_consultants': result['active_consultants'],
            'total_consultants': result['consultant_count']
        }
        
        # Handle version filtering
        version = options.get('version')
        if version and isinstance(version, int) and 1 <= version <= 4:
            version_key = f'version{version}'
            if version_key in result['optimized_queries']:
                response['optimized_queries'] = {
                    version_key: result['optimized_queries'][version_key]
                }
            else:
                raise ValueError(f"Version {version} not found in results")
        else:
            response['optimized_queries'] = result['optimized_queries']
        
        # Optionally remove detailed changes
        if not options.get('include_changes', True):
            for version_data in response['optimized_queries'].values():
                version_data.pop('changes', None)
        
        logger.info(f"Query processed successfully: {request_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error processing query {request_id}: {str(e)}")
        raise


async def handle_optimize_request(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle the /optimize endpoint."""
    try:
        body = json.loads(event.get('body', '{}'))
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    
    # Validate request
    is_valid, error_message = validate_request(body)
    if not is_valid:
        return create_response(400, {'error': error_message})
    
    query = body['query'].strip()
    options = body.get('options', {})
    
    # Validate options
    if 'version' in options:
        version = options['version']
        if version is not None and (not isinstance(version, int) or version < 1 or version > 4):
            return create_response(400, {'error': 'Version must be null or an integer between 1 and 4'})
    
    try:
        optimizer = get_optimizer()
        result = await process_single_query(optimizer, query, options)
        return create_response(200, result)
    except Exception as e:
        logger.exception("Unexpected error in optimization")
        return create_response(500, {
            'error': 'Internal server error',
            'message': str(e)
        })


async def handle_batch_request(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle the /optimize/batch endpoint."""
    try:
        body = json.loads(event.get('body', '{}'))
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    
    if 'queries' not in body:
        return create_response(400, {'error': 'Queries field is required'})
    
    queries = body.get('queries', [])
    if not isinstance(queries, list):
        return create_response(400, {'error': 'Queries must be a list'})
    
    if len(queries) == 0:
        return create_response(400, {'error': 'At least one query is required'})
    
    if len(queries) > 10:  # Reasonable limit for batch processing
        return create_response(400, {'error': 'Maximum 10 queries per batch'})
    
    options = body.get('options', {})
    
    try:
        optimizer = get_optimizer()
        
        # Process queries in parallel (with some concurrency limit)
        tasks = []
        for query in queries:
            if not isinstance(query, str) or not query.strip():
                return create_response(400, {'error': 'All queries must be non-empty strings'})
            tasks.append(process_single_query(optimizer, query.strip(), options))
        
        # Limit concurrency to avoid overwhelming the API
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Format batch response
        batch_response = {
            'request_id': str(uuid.uuid4()),
            'results': [],
            'summary': {
                'total': len(queries),
                'successful': 0,
                'failed': 0
            }
        }
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                batch_response['results'].append({
                    'query': queries[i],
                    'error': str(result),
                    'status': 'failed'
                })
                batch_response['summary']['failed'] += 1
            else:
                result['status'] = 'success'
                batch_response['results'].append(result)
                batch_response['summary']['successful'] += 1
        
        return create_response(200, batch_response)
        
    except Exception as e:
        logger.exception("Unexpected error in batch optimization")
        return create_response(500, {
            'error': 'Internal server error',
            'message': str(e)
        })


def handle_health_check() -> Dict[str, Any]:
    """Handle the /health endpoint."""
    try:
        # Check if optimizer can be initialized
        optimizer = get_optimizer()
        consultant_summary = optimizer.get_agent_summary()
        
        return create_response(200, {
            'status': 'healthy',
            'model': consultant_summary['model'],
            'consultants': consultant_summary['consultant_count'],
            'brave_search_enabled': bool(optimizer.brave_api_key)
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return create_response(503, {
            'status': 'unhealthy',
            'error': str(e)
        })


def handle_consultants_list() -> Dict[str, Any]:
    """Handle the /consultants endpoint."""
    try:
        optimizer = get_optimizer()
        
        consultants_info = []
        for agent in optimizer.consultant_agents:
            consultants_info.append({
                'id': agent.name.split()[-1],  # Extract ID from name
                'name': agent.name,
                'active': True
            })
        
        return create_response(200, {
            'consultants': consultants_info,
            'total': len(consultants_info)
        })
    except Exception as e:
        logger.error(f"Error listing consultants: {str(e)}")
        return create_response(500, {
            'error': 'Failed to list consultants',
            'message': str(e)
        })


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler function.
    
    Routes requests to appropriate handlers based on the path and method.
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Extract HTTP method and path
    http_method = event.get('httpMethod', 'GET')
    path = event.get('path', '/')
    
    # Handle CORS preflight
    if http_method == 'OPTIONS':
        return create_response(200, {})
    
    # Route to appropriate handler
    if path == '/optimize' and http_method == 'POST':
        return asyncio.run(handle_optimize_request(event))
    elif path == '/optimize/batch' and http_method == 'POST':
        return asyncio.run(handle_batch_request(event))
    elif path == '/health' and http_method == 'GET':
        return handle_health_check()
    elif path == '/consultants' and http_method == 'GET':
        return handle_consultants_list()
    else:
        return create_response(404, {
            'error': 'Not found',
            'message': f'No handler for {http_method} {path}'
        })


# For local testing
if __name__ == "__main__":
    # Test event
    test_event = {
        'httpMethod': 'POST',
        'path': '/optimize',
        'body': json.dumps({
            'query': 'preference action trustee',
            'options': {
                'include_changes': True
            }
        })
    }
    
    response = lambda_handler(test_event, None)
    print(json.dumps(response, indent=2))
