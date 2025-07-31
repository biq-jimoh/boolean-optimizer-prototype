# Web Search Implementation for SI-7 and SI-8

## Overview

This implementation adds web search capability to the SI-7 (Statute Citation) and SI-8 (Case Citation) consultants, allowing them to fetch actual legal text from authoritative sources before making recommendations.

## Architecture

### Components

1. **CitationDetector** (`citation_detector.py`)
   - Uses Agent SDK to detect statute and case citations in queries
   - Normalizes statute citations to standard format (e.g., "11 U.S.C. § 363")
   - Formats case names for searching

2. **BraveSearchService** (`brave_search_service.py`)
   - Performs web searches using Brave Search API
   - Searches law.cornell.edu for statutes
   - Searches courtlistener.com/opinion for cases

3. **ContentValidator** (`content_validator.py`)
   - Uses Agent SDK to validate search results
   - Ensures the found page contains the correct legal document
   - Provides confidence scores

4. **ContentExtractor** (`content_extractor.py`)
   - Fetches web pages and extracts relevant text
   - Handles HTML parsing and cleanup
   - Intelligently truncates content to fit context limits

### Modified Files

- **bankruptcy_query_optimizer.py**
  - Separates consultants into immediate and delayed groups
  - Runs pre-scan for citations while other consultants execute
  - SI-7 and SI-8 wait for web content before running
  - All other consultants run immediately

## How It Works

1. **Query Analysis**: When a query is submitted, the system starts a pre-scan to detect citations
2. **Parallel Execution**: 
   - All consultants except SI-7 and SI-8 run immediately
   - Citation detection and web searches happen in parallel
3. **Web Search Process** (for detected citations):
   - Search the appropriate legal database
   - Validate the first result using LLM
   - Extract the relevant content from the page
4. **Enhanced Execution**: SI-7 and SI-8 receive the original query plus the fetched legal text
5. **Normal Flow**: Results from all consultants are combined and sent to the executive agent

## Configuration

### Environment Variables

```bash
# Required for all consultants
OPENAI_API_KEY=your_openai_api_key

# Required for web search functionality
BRAVE_SEARCH_API_KEY=your_brave_search_api_key
```

Get your Brave Search API key at: https://api.search.brave.com/app/keys

### Graceful Degradation

If `BRAVE_SEARCH_API_KEY` is not provided:
- SI-7 and SI-8 will still run but without web content
- They will use their internal knowledge as before
- A warning is logged but the system continues to function

## Testing

Run the test script to verify the implementation:

```bash
python test_web_search.py
```

The test script includes:
- Statute citation query test
- Case citation query test  
- Mixed citation query test
- Non-citation query test (verifies no blocking)

## Example Usage

```python
from bankruptcy_query_optimizer import BankruptcyQueryOptimizer

# Initialize with Brave API key
optimizer = BankruptcyQueryOptimizer(
    brave_api_key="your_brave_api_key"  # Or set BRAVE_SEARCH_API_KEY env var
)

# Query with statute citation
result = optimizer.optimize_query_sync("section 363(f)")

# Query with case citation  
result = optimizer.optimize_query_sync("Stern v. Marshall")
```

## Performance Considerations

- Web searches add 2-5 seconds to SI-7/SI-8 execution time
- Other consultants are not affected and run at full speed
- Failed web searches gracefully fall back to original behavior
- Timeouts prevent indefinite waiting

## Security Considerations

- User-Agent header identifies requests as coming from BankruptcyQueryOptimizer
- No credentials are sent to law.cornell.edu or courtlistener.com
- Brave API key is kept secure and never logged
- HTML content is sanitized before processing