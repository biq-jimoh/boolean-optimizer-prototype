# Rate Limit Handling with Exponential Backoff

The Boolean Optimizer Agent now includes robust rate limit handling for the Brave Search API using exponential backoff with jitter.

## How It Works

When the Brave Search API returns a 429 (Too Many Requests) error, the system:

1. **Waits** before retrying with exponentially increasing delays
2. **Adds jitter** to prevent multiple clients from retrying at the same time
3. **Respects Retry-After** headers if provided by the API
4. **Logs attempts** clearly for debugging

## Configuration

The `BraveSearchService` constructor accepts retry parameters:

```python
service = BraveSearchService(
    api_key="your_key",
    max_retries=3,        # Number of retry attempts (default: 3)
    initial_backoff=1.0,  # Starting delay in seconds (default: 1.0)
    max_backoff=60.0      # Maximum delay in seconds (default: 60.0)
)
```

## Backoff Algorithm

The delay calculation follows this pattern:

```
delay = min(initial_backoff * (2 ^ attempt) + jitter, max_backoff)
```

Where:
- `attempt` starts at 0 for the first retry
- `jitter` is a random value between 0 and 0.1 seconds
- The delay is capped at `max_backoff`

### Example Progression

With default settings:
- 1st retry: ~1.0 seconds
- 2nd retry: ~2.0 seconds  
- 3rd retry: ~4.0 seconds
- 4th retry: ~8.0 seconds (if max_retries > 3)

## Benefits

1. **Automatic Recovery**: Temporary rate limits don't cause failures
2. **System Resilience**: Gracefully handles API constraints
3. **Clear Visibility**: Logs show retry attempts and delays
4. **Parallel Compatibility**: Works seamlessly with multiple citation fetching

## Example Log Output

When rate limiting occurs, you'll see:
```
Rate limited (429). Retrying in 2.1 seconds... (attempt 1/3)
Rate limited (429). Retrying in 4.0 seconds... (attempt 2/3)
```

If all retries fail:
```
Failed to search for statute after 3 retries
```

## Testing

Run the test script to see exponential backoff in action:
```bash
python test_exponential_backoff.py
```

This will:
- Make rapid consecutive searches to potentially trigger rate limiting
- Test parallel requests with backoff handling
- Show timing information for performance analysis

## Integration with Multiple Citations

The exponential backoff works seamlessly with the multiple citation feature:
- Each parallel fetch has its own retry logic
- Failed fetches after retries are gracefully skipped
- Other successful fetches continue normally

This ensures maximum resilience when fetching multiple legal texts simultaneously.