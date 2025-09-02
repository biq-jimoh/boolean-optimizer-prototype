# Bankruptcy Query Optimizer API Documentation

## Overview

The Bankruptcy Query Optimizer API provides a RESTful interface to optimize Boolean queries for bankruptcy court transcript searches. The API is deployed on AWS Lambda and secured with API key authentication.

## Base URL

```
https://{api-id}.execute-api.{region}.amazonaws.com/{stage}
```

Example:
```
https://abc123.execute-api.us-east-1.amazonaws.com/prod
```

## Authentication

All endpoints (except `/health`) require API key authentication. Include your API key in the request headers:

```
X-Api-Key: your-api-key-here
```

## Rate Limiting

- **Rate Limit**: 10 requests per second
- **Burst Limit**: 20 requests
- **Monthly Quota**: 10,000 requests per API key

## Endpoints

### 1. Optimize Query

Optimize a single bankruptcy query.

**Endpoint**: `POST /optimize`

**Request Body**:
```json
{
  "query": "preference action trustee motion",
  "options": {
    "version": null,
    "include_changes": true,
    "enable_web_search": true
  }
}
```

**Request Parameters**:
- `query` (required, string): The bankruptcy query to optimize (max 1000 characters)
- `options` (optional, object):
  - `version` (integer or null): Specific version (1-4) or null for all versions
  - `include_changes` (boolean, default: true): Include detailed change information
  - `enable_web_search` (boolean, default: true): Enable web search for statute/case citations

**Response** (200 OK):
```json
{
  "request_id": "123e4567-e89b-12d3-a456-426614174000",
  "original_query": "preference action trustee motion",
  "optimized_queries": {
    "version1": {
      "query": "preference action trustee motion",
      "changes": []
    },
    "version2": {
      "query": "preferenc! action trustee motion",
      "changes": [
        {
          "rule_id": "AC-1",
          "rule_name": "Fix typos",
          "change": "Added typo variation: preference → preferenc!"
        }
      ]
    },
    "version3": {
      "query": "(preference OR preferential) action trustee motion",
      "changes": [
        {
          "rule_id": "SI-4",
          "rule_name": "Add synonyms",
          "change": "Added synonym: preference → preferential"
        }
      ]
    },
    "version4": {
      "query": "(preference OR preferential) action /3 (trustee OR debtor) motion",
      "changes": [
        {
          "rule_id": "SI-5",
          "rule_name": "Use proximity",
          "change": "Added proximity operator between action and trustee"
        }
      ]
    }
  },
  "execution_time": "2.34s",
  "active_consultants": 14,
  "total_consultants": 14
}
```

**Error Responses**:
- `400 Bad Request`: Invalid request format or parameters
- `401 Unauthorized`: Missing or invalid API key
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

### 2. Batch Optimize

Optimize multiple queries in a single request.

**Endpoint**: `POST /optimize/batch`

**Request Body**:
```json
{
  "queries": [
    "preference action",
    "section 363 sale",
    "Till v. SCS Credit"
  ],
  "options": {
    "version": 3,
    "include_changes": false
  }
}
```

**Request Parameters**:
- `queries` (required, array): Array of queries to optimize (max 10 queries)
- `options` (optional, object): Same as single optimize endpoint

**Response** (200 OK):
```json
{
  "request_id": "456e7890-e89b-12d3-a456-426614174000",
  "results": [
    {
      "request_id": "789e0123-e89b-12d3-a456-426614174000",
      "original_query": "preference action",
      "optimized_queries": {...},
      "execution_time": "1.23s",
      "active_consultants": 14,
      "total_consultants": 14,
      "status": "success"
    },
    {
      "query": "invalid query with error",
      "error": "Query processing failed",
      "status": "failed"
    }
  ],
  "summary": {
    "total": 3,
    "successful": 2,
    "failed": 1
  }
}
```

### 3. Health Check

Check API health and configuration.

**Endpoint**: `GET /health`

**Authentication**: Not required

**Response** (200 OK):
```json
{
  "status": "healthy",
  "model": "gpt-5",
  "consultants": 14,
  "brave_search_enabled": true
}
```

### 4. List Consultants

Get information about available consultant agents.

**Endpoint**: `GET /consultants`

**Response** (200 OK):
```json
{
  "consultants": [
    {
      "id": "AC-1",
      "name": "Consultant AC-1",
      "active": true
    },
    {
      "id": "AC-3",
      "name": "Consultant AC-3",
      "active": true
    }
  ],
  "total": 14
}
```

## Response Headers

All responses include:
- `Content-Type: application/json`
- `X-Request-Id`: Unique request identifier
- `X-RateLimit-Limit`: Rate limit
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Reset timestamp

## Error Format

All error responses follow this format:
```json
{
  "error": "Error type",
  "message": "Detailed error message"
}
```

## Code Examples

### Python
```python
import requests

url = "https://api.example.com/prod/optimize"
headers = {
    "X-Api-Key": "your-api-key",
    "Content-Type": "application/json"
}
data = {
    "query": "preference action trustee",
    "options": {
        "version": 3
    }
}

response = requests.post(url, json=data, headers=headers)
result = response.json()
print(result["optimized_queries"]["version3"]["query"])
```

### cURL
```bash
curl -X POST https://api.example.com/prod/optimize \
  -H "X-Api-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "preference action trustee",
    "options": {
      "version": 3
    }
  }'
```

### JavaScript
```javascript
const response = await fetch('https://api.example.com/prod/optimize', {
  method: 'POST',
  headers: {
    'X-Api-Key': 'your-api-key',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    query: 'preference action trustee',
    options: {
      version: 3
    }
  })
});

const result = await response.json();
console.log(result.optimized_queries.version3.query);
```

## Timeout Considerations

- Lambda timeout is set to 5 minutes
- Most queries complete in 2-5 seconds
- Complex queries with web search may take up to 30 seconds
- Consider implementing client-side timeouts of 60 seconds

## Best Practices

1. **Batch Processing**: Use the batch endpoint for multiple queries to reduce API calls
2. **Version Selection**: Request specific versions if you don't need all four
3. **Caching**: Cache results for identical queries to reduce costs
4. **Error Handling**: Implement retry logic with exponential backoff for transient errors
5. **Monitoring**: Track your usage against the monthly quota
