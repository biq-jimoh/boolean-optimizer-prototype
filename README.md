# Bankruptcy Query Optimizer

A sophisticated system that uses OpenAI's Agents SDK to optimize Boolean queries for bankruptcy court transcript searches. The system runs multiple specialized consultant agents in parallel to analyze queries and provide recommendations, which are then synthesized by an executive agent into four optimized versions.

## Features

- **14 Specialized Consultant Agents**: Each focusing on specific query optimization techniques
- **Parallel Processing**: All consultants run simultaneously for fast results
- **Structured Outputs**: Reliable, consistent results using Pydantic models
- **4 Optimization Levels**: From basic corrections to comprehensive enhancements
- **Flexible Usage**: Python API and CLI tool

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd bankruptcy-query-optimizer
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
# Copy the example environment file
cp env.example .env

# Edit .env and add your API keys
# - OPENAI_API_KEY (required)
# - BRAVE_SEARCH_API_KEY (optional, enables web search for SI-7 and SI-8)
```

Or set them directly:
```bash
export OPENAI_API_KEY="your-openai-api-key"
export BRAVE_SEARCH_API_KEY="your-brave-api-key"  # Optional
```

## Quick Start

### Command Line Interface

Optimize a single query:
```bash
python optimize_query.py "preference action trustee motion"
```

Show only Version 3 (broadest optimization):
```bash
python optimize_query.py -v 3 "section 363 sale"
```

Process multiple queries from a file:
```bash
python optimize_query.py -f queries.txt
```

Get JSON output:
```bash
python optimize_query.py --json "Till v. SCS Credit"
```

### Python API

```python
from bankruptcy_query_optimizer import BankruptcyQueryOptimizer

# Initialize optimizer
optimizer = BankruptcyQueryOptimizer(model="gpt-5")

# Optimize a query
result = optimizer.optimize_query_sync("preference action")

# Access optimized versions
print(result['optimized_queries']['version1']['query'])
print(result['optimized_queries']['version2']['query'])
print(result['optimized_queries']['version3']['query'])
print(result['optimized_queries']['version4']['query'])
```

 

## How It Works

### Consultant Agents

The system includes 14 consultant agents, each specializing in different optimization techniques:

**Automatic Corrections (AC):**
- AC-1: Fix typos
- AC-3: Expand acronyms
- AC-4: Quote statute citations
- AC-5: Add statute citation variations
- AC-6: Convert case names to proximity format

**Suggestion Improvements (SI):**
- SI-1: Add root extenders
- SI-2: Quote multi-word phrases
- SI-3: Remove unnecessary quotes
- SI-4: Add synonyms (broadening)
- SI-5: Use proximity for legal phrases
- SI-6: Add AND between adjacent words (narrowing)
- SI-7: Statute citation to core concept expansion (broadening)
- SI-8: Case citation to core concept expansion (broadening)
- SI-9: Add case name variations

### Optimization Versions

The executive agent synthesizes consultant recommendations into 4 versions:

1. **Version 1**: Basic corrections only (AC-1, AC-3, AC-4, AC-5, AC-6)
2. **Version 2**: Version 1 + base improvements (SI-1, SI-2, SI-3, SI-5, SI-9)
3. **Version 3**: Version 2 + broadening suggestions (SI-4, SI-7, SI-8)
4. **Version 4**: Version 2 + narrowing suggestion (SI-6)

## Example Output

Input query: `preference action trustee motion`

**Version 1**: `preference action trustee motion`  
(No corrections needed)

**Version 2**: `preference! action! trustee! motion!`  
(Added root extenders)

**Version 3**: `(preference! OR preferential) (action! OR lawsuit OR proceeding) (trustee! OR "bankruptcy trustee") motion!`  
(Added synonyms for broader coverage)

**Version 4**: `preference! AND action! AND trustee! AND motion!`  
(Added AND operators for narrower results)

## Advanced Usage

### Custom Model Configuration

```python
optimizer = BankruptcyQueryOptimizer(
    model="gpt-5",
    temperature=0.1,  # Ignored for gpt-5; applies to non-GPT-5 models
    consultants_dir="custom/consultants",
    executive_path="custom/executive.txt"
)
```

### Async Usage

```python
import asyncio

async def optimize_multiple_queries():
    optimizer = BankruptcyQueryOptimizer()
    queries = ["query1", "query2", "query3"]
    
    results = await asyncio.gather(
        *(optimizer.optimize_query(q) for q in queries)
    )
    
    return results

results = asyncio.run(optimize_multiple_queries())
```

### Accessing Detailed Consultant Output

```python
result = optimizer.optimize_query_sync("section 363 sale")

# View which consultants had recommendations
print("Active consultants:", result['active_consultant_names'])

# Access structured consultant outputs
for consultant, details in result['consultant_details'].items():
    if details['has_recommendations']:
        print(f"\n{consultant}:")
        for rec in details['recommendations']:
            print(f"  - {rec['original']} → {rec['replacement']}")
```

## Performance Considerations

- **Concurrency**: Default max concurrent consultants is 10 (configurable)
- **Execution Time**: Typically 5-15 seconds per query
- **Rate Limits**: Built-in semaphore prevents overwhelming API limits
- **Model**: Uses gpt-5 by default for high-quality results

## Troubleshooting

### Common Issues

1. **"OPENAI_API_KEY not set"**: Ensure your API key is exported in your environment
2. **Rate limit errors**: Reduce `max_concurrent` parameter
3. **JSON parsing errors**: Check that consultant/executive prompts are properly formatted

### Debug Mode

Enable verbose logging:
```bash
python optimize_query.py --verbose "your query"
```

## Project Structure

```
bankruptcy-query-optimizer/
├── bankruptcy_query_optimizer.py  # Main optimizer implementation
├── optimize_query.py             # CLI tool
├── requirements.txt              # Python dependencies
├── README.md                     # This file
└── prompts/                      # Prompt templates (required)
    ├── consultants/              # Consultant agent prompts
    └── executive/                # Executive agent prompt
```

## License

[Your License Here]

## Contributing

[Contributing guidelines if applicable]
