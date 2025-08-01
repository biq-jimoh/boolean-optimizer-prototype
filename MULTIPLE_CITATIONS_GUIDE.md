# Multiple Citations Support

The Boolean Optimizer Agent now supports queries with multiple statute and case citations, fetching all relevant legal texts in parallel while managing token limits intelligently.

## Features

### 1. Multiple Citation Detection
The system now detects ALL citations in a query, not just the first one:
- **Statutes**: `544a`, `547c2`, `section 365(b)`, etc.
- **Cases**: `Stern`, `Till v. SCS Credit`, `RadLAX`, etc.
- **Mixed**: Combines both statute and case citations

Examples:
```
"544a and 547c2"
"Compare Stern with Till"
"544a trustee powers and Stern v. Marshall jurisdiction"
```

### 2. Token Budget Management
With GPT-4.1's 1M token context window, we allocate 750K tokens for legal texts:
- **Per-statute limit**: 50K tokens (~200 pages)
- **Per-case limit**: 100K tokens (~400 pages)
- **Dynamic allocation**: Cases get 2x the weight of statutes
- **Smart redistribution**: Unused tokens redistributed to other citations

### 3. Parallel Fetching
All citations are fetched simultaneously for minimal latency:
- **Single citation**: ~800ms (same as before)
- **Multiple citations**: Still ~800ms (runs in parallel)
- **Latency formula**: `total_time = max(individual_fetch_times)`

### 4. Enhanced Query Format
Fetched content is clearly organized for consultants:
```
Original query

--- FETCHED STATUTE TEXTS ---

[544a]
<full HTML content of 11 U.S.C. § 544(a)>

[547c2]
<full HTML content of 11 U.S.C. § 547(c)(2)>

--- FETCHED CASE OPINION TEXTS ---

[Stern v. Marshall]
<full HTML content of Stern opinion>
```

## Usage

Simply include multiple citations in your query:

```python
# Multiple statutes
result = await optimizer.optimize_query("544a and 547c2")

# Multiple cases
result = await optimizer.optimize_query("Stern and Till")

# Mixed citations
result = await optimizer.optimize_query("544a powers vs Stern limitations")

# Many citations (token budget automatically managed)
result = await optimizer.optimize_query("363a, 365b, 544a, 547c2, and 522f")
```

## Token Allocation Examples

| Scenario | Allocation |
|----------|------------|
| 1 statute | 50K tokens (max for statute) |
| 1 case | 100K tokens (max for case) |
| 2 statutes + 1 case | 50K + 50K + 100K = 200K total |
| 10 statutes + 5 cases | ~43K each statute, ~86K each case |
| 20+ citations | Minimum 10K per citation guaranteed |

## Implementation Details

### Files Modified
1. **`token_budget.py`** (new): Token budget configuration and allocation
2. **`citation_detector.py`**: New list-based detection methods
3. **`content_extractor.py`**: Added token limit support
4. **`bankruptcy_query_optimizer.py`**: Rewritten for parallel multi-citation handling
5. **`SI-7` and `SI-8` prompts**: Updated to handle multiple texts

### Backward Compatibility
- Legacy single-detection methods still available
- Existing single-citation queries work unchanged
- No breaking changes to public API

## Testing

Run the test script to see multiple citations in action:
```bash
python test_multiple_citations.py
```

This tests:
- Token budget allocation
- Various citation combinations
- Parallel fetching performance