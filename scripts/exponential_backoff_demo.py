#!/usr/bin/env python3
"""
Test script to demonstrate exponential backoff handling for 429 errors.
"""
import asyncio
from boolean_optimizer.services.brave_search import BraveSearchService


async def test_backoff():
    """Test the exponential backoff functionality."""
    print("Testing Exponential Backoff for Rate Limiting")
    print("=" * 60)
    
    # Initialize service with custom retry settings
    service = BraveSearchService(
        max_retries=3,
        initial_backoff=1.0,
        max_backoff=30.0
    )
    
    # Test with multiple rapid requests
    test_citations = [
        "11 U.S.C. § 363",
        "11 U.S.C. § 365", 
        "11 U.S.C. § 544",
        "11 U.S.C. § 547",
        "11 U.S.C. § 548"
    ]
    
    print("\nMaking rapid consecutive searches to trigger rate limiting...")
    print("-" * 60)
    
    for citation in test_citations:
        print(f"\nSearching for: {citation}")
        results = await service.search_statute(citation)
        
        if results:
            print(f"  ✓ Found {len(results)} results")
            if results:
                print(f"  → Top result: {results[0]['title']}")
        else:
            print(f"  ✗ No results found")
        
        # Small delay to show the pattern
        await asyncio.sleep(0.1)
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("\nNotes:")
    print("- If rate limiting occurs, you'll see retry messages with backoff times")
    print("- Backoff times double with each retry: 1s, 2s, 4s, 8s, etc.")
    print("- Maximum backoff is capped at 30 seconds")
    print("- Random jitter (0-0.1s) is added to prevent thundering herd")


async def test_parallel_with_backoff():
    """Test parallel requests with backoff handling."""
    print("\n\nTesting Parallel Requests with Backoff")
    print("=" * 60)
    
    service = BraveSearchService(
        max_retries=2,
        initial_backoff=2.0,
        max_backoff=10.0
    )
    
    # Create parallel search tasks
    citations = ["363a", "544a", "547c2"]
    
    print(f"\nSearching for {len(citations)} statutes in parallel...")
    print("-" * 60)
    
    tasks = [
        service.search_statute(f"11 U.S.C. § {cite}")
        for cite in citations
    ]
    
    start_time = asyncio.get_event_loop().time()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    end_time = asyncio.get_event_loop().time()
    
    for i, (cite, result) in enumerate(zip(citations, results)):
        if isinstance(result, Exception):
            print(f"\n{cite}: ✗ Error - {type(result).__name__}: {result}")
        elif result:
            print(f"\n{cite}: ✓ Found {len(result)} results")
        else:
            print(f"\n{cite}: ✗ No results")
    
    print(f"\nTotal time for parallel requests: {end_time - start_time:.2f} seconds")
    print("\nNote: Even with retries, parallel requests complete faster than sequential")


if __name__ == "__main__":
    print("Exponential Backoff Test for Brave Search API")
    print("=" * 60)
    
    # Run tests
    asyncio.run(test_backoff())
asyncio.run(test_parallel_with_backoff())
