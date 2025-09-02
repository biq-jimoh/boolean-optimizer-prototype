# Web Search Implementation for SI-7 and SI-8

## Overview

This implementation adds web search capability to the SI-7 (Statute Citation) and SI-8 (Case Citation) consultants, allowing them to fetch actual legal text from authoritative sources before making recommendations.

## Architecture

### Components

1. **CitationDetector** (`citation_detector.py`)
   - Uses Agent SDK to detect statute and case citations in queries
   - Flexibly recognizes various formats: "363a", "363f3", "365b1A", etc.
   - Normalizes citations and extracts subsection structure

2. **BraveSearchService** (`brave_search_service.py`)
   - Performs web searches using Brave Search API via direct HTTP calls
   - Searches law.cornell.edu for statutes
   - Searches courtlistener.com/opinion for cases

3. **ContentValidator** (`content_validator.py`)
   - Uses Agent SDK to validate search results using raw HTML
   - Leverages large-context models (e.g., gpt-5)
   - Analyzes HTML structure to find specific provisions

4. **ContentExtractor** (`content_extractor.py`)
   - Simple HTTP client that fetches raw HTML
   - No complex parsing or extraction - just returns the full page
   - Lets the LLM handle understanding the content

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
   - Fetch the full HTML page
   - Validate using the actual page content (not just metadata)
4. **Enhanced Execution**: 
   - If web content is found: SI-7 and SI-8 receive the original query plus the fetched legal text
   - If no web content found: SI-7 and SI-8 are skipped entirely
5. **Normal Flow**: Results from all consultants that ran are combined and sent to the executive agent

### Important Behavior

- SI-7 and SI-8 **only** make recommendations based on actual legal text from web searches
- They are **skipped entirely** if web search fails or returns no valid results
- They **never** use their built-in knowledge to make recommendations

### Raw HTML Validation

The system now uses raw HTML for validation, taking advantage of large model context windows:

1. **Full Context**: The entire HTML page (typically 70-100KB) is sent to the validator
2. **Structure-Aware**: The validator can see HTML elements like `<a name="a">` for subsections
3. **Flexible Recognition**: Understands that "363a" means section 363(a)
4. **No Regex Bugs**: Eliminates complex extraction logic that was causing errors
5. **Better Accuracy**: Can find nested subsections and understand page structure

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

If `BRAVE_SEARCH_API_KEY` is not provided or no valid content is retrieved:
- SI-7 and SI-8 are skipped to avoid uninformed expansions
- Other consultants still run and produce results
- A warning is logged and the system continues to function

## Testing

You can validate behavior using the local CLI or lambda-local tests, for example:

```bash
# CLI example
python optimize_query.py "section 544(a) financing"

# Lambda-local happy path
python scripts/lambda_local_test.py optimize_simple
```

## Example Usage

```python
from bankruptcy_query_optimizer import BankruptcyQueryOptimizer

# Initialize with Brave API key
optimizer = BankruptcyQueryOptimizer(
    brave_api_key="your_brave_api_key"  # Or set BRAVE_SEARCH_API_KEY env var
)

# Query with various statute formats
result = optimizer.optimize_query_sync("544a")
result = optimizer.optimize_query_sync("547c2")
result = optimizer.optimize_query_sync("section 522(f)")

# Query with case citation  
result = optimizer.optimize_query_sync("Stern v. Marshall")
```

## Performance Considerations

- Web searches add 2-5 seconds to SI-7/SI-8 execution time
- Other consultants are not affected and run at full speed
- Failed web searches gracefully fall back to skipping the consultants
- HTML pages are typically 70-100KB and fit comfortably within modern large-context models

## Security Considerations

- User-Agent header identifies requests as coming from BankruptcyQueryOptimizer
- No credentials are sent to law.cornell.edu or courtlistener.com
- Brave API key is kept secure and never logged
- Raw HTML is sent directly to the LLM without processing
