# AWS Lambda API Deployment Plan for Boolean Optimizer Agent

## Overview

This document outlines the plan to convert the Boolean Optimizer Agent from a CLI tool to a serverless API deployed on AWS Lambda.

## Architecture Overview

### Current State
- CLI-based tool using asyncio
- Multiple consultant agents running in parallel
- OpenAI Agents SDK integration
- Optional Brave Search API for web searches
- Heavy dependencies (playwright, etc.)

### Target State
- RESTful API deployed on AWS Lambda
- API Gateway for HTTP endpoints
- Containerized Lambda function (due to dependencies)
- Stateless design with async handling
- CloudWatch logging and monitoring

## API Design

### Endpoints

#### 1. POST /optimize
Main endpoint for query optimization.

**Request:**
```json
{
  "query": "preference action trustee motion",
  "options": {
    "version": null,  // null for all versions, or 1-4 for specific
    "include_changes": true,  // Include detailed change information
    "enable_web_search": true  // Enable SI-7/SI-8 web search
  }
}
```

**Response:**
```json
{
  "request_id": "uuid-here",
  "original_query": "preference action trustee motion",
  "optimized_queries": {
    "version1": {
      "query": "optimized query here",
      "changes": [...]
    },
    "version2": {...},
    "version3": {...},
    "version4": {...}
  },
  "execution_time": "2.34s",
  "active_consultants": 14,
  "total_consultants": 14
}
```

#### 2. POST /optimize/batch
Batch processing endpoint for multiple queries.

**Request:**
```json
{
  "queries": ["query1", "query2", "query3"],
  "options": {...}
}
```

#### 3. GET /health
Health check endpoint.

#### 4. GET /consultants
List active consultants and their status.

## Implementation Steps

### 1. Create Lambda Handler (lambda_handler.py)

The handler will:
- Parse API Gateway events
- Initialize the optimizer (with caching for warm starts)
- Handle async execution within Lambda
- Format responses for API Gateway

### 2. Dependency Optimization

#### Lightweight Requirements
Create `requirements-lambda.txt` excluding heavy dependencies:
- Remove playwright (not needed for Lambda)
- Use minimal versions of libraries
- Consider Lambda layers for common dependencies

#### Container Approach
Due to OpenAI Agents SDK and other dependencies:
- Use AWS Lambda container images
- Base image: `public.ecr.aws/lambda/python:3.11`
- Multi-stage build to minimize size

### 3. Code Refactoring

#### Async Handling
- Modify the main optimization flow to work with Lambda's event loop
- Implement proper timeout handling (Lambda max: 15 minutes)
- Add circuit breakers for external API calls

#### State Management
- Remove all file-based state
- Load consultant prompts into memory on cold start
- Cache initialized agents between invocations

### 4. Error Handling & Logging

- Structured logging for CloudWatch
- Proper error responses with status codes
- Retry logic for transient failures
- Dead letter queue for failed requests

### 5. Authentication

- API Key authentication via API Gateway
- Rate limiting per API key
- Usage tracking and quotas

## AWS Infrastructure

### Required Services
1. **AWS Lambda**: Function execution
2. **API Gateway**: HTTP API endpoints
3. **ECR**: Container image repository
4. **CloudWatch**: Logs and metrics
5. **IAM**: Permissions and roles
6. **Secrets Manager**: API keys storage
7. **S3**: Consultant prompts storage (optional)

### Deployment Configuration (serverless.yml)

```yaml
service: bankruptcy-query-optimizer

provider:
  name: aws
  runtime: python3.11
  stage: ${opt:stage, 'dev'}
  region: ${opt:region, 'us-east-1'}
  timeout: 300  # 5 minutes
  memorySize: 3008  # 3GB for faster processing
  environment:
    OPENAI_API_KEY: ${ssm:/bankruptcy-optimizer/openai-api-key}
    BRAVE_SEARCH_API_KEY: ${ssm:/bankruptcy-optimizer/brave-api-key}

functions:
  optimize:
    image: 
      uri: ${ssm:/bankruptcy-optimizer/ecr-uri}:latest
    events:
      - http:
          path: optimize
          method: post
          cors: true
          authorizer:
            name: apiKeyAuthorizer
            type: request
```

## Performance Considerations

### Cold Start Optimization
1. Keep container image small (<250MB)
2. Lazy load heavy dependencies
3. Use provisioned concurrency for consistent performance
4. Pre-warm functions with scheduled pings

### Concurrent Execution
1. Set reserved concurrency (e.g., 100)
2. Implement request queuing for bursts
3. Monitor throttling metrics

### Timeout Handling
1. Default timeout: 5 minutes
2. Implement async job pattern for longer queries:
   - Return job ID immediately
   - Process in background
   - Provide status endpoint

## Cost Optimization

1. **Lambda Pricing**:
   - Pay per request and compute time
   - Estimate: ~$0.02-0.05 per optimization

2. **API Gateway**:
   - $3.50 per million requests
   - Data transfer costs

3. **Cost Reduction**:
   - Use Lambda SnapStart for Java (if switching)
   - Implement caching for repeated queries
   - Batch processing for bulk operations

## Monitoring & Observability

1. **CloudWatch Dashboards**:
   - Request rate and latency
   - Error rates and types
   - Consultant performance metrics

2. **Alarms**:
   - High error rate
   - Timeout threshold
   - API throttling

3. **X-Ray Tracing**:
   - End-to-end request tracing
   - Performance bottleneck identification

## Security Considerations

1. **API Security**:
   - HTTPS only via API Gateway
   - API key rotation policy
   - IP whitelisting (optional)

2. **Secrets Management**:
   - Store API keys in AWS Secrets Manager
   - IAM roles for Lambda execution
   - Principle of least privilege

3. **Input Validation**:
   - Query length limits
   - Character sanitization
   - Rate limiting per client

## Migration Strategy

### Phase 1: Local Testing
1. Create Lambda handler
2. Test locally with SAM CLI
3. Verify all consultants work correctly

### Phase 2: Dev Deployment
1. Deploy to dev environment
2. Test all endpoints
3. Performance benchmarking

### Phase 3: Production Deployment
1. Deploy with blue/green strategy
2. Monitor closely for first 24 hours
3. Implement gradual rollout

## Next Steps

1. Create the Lambda handler implementation
2. Set up Docker container configuration
3. Create serverless deployment configuration
4. Implement API authentication
5. Set up CI/CD pipeline
6. Create comprehensive API documentation
