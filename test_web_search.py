"""
Test script for web search functionality in SI-7 and SI-8 consultants.
"""

import asyncio
import os
from dotenv import load_dotenv
from bankruptcy_query_optimizer import BankruptcyQueryOptimizer

# Load environment variables
load_dotenv()


async def test_statute_query():
    """Test with a statute citation query."""
    print("\n" + "="*80)
    print("Testing with statute citation query")
    print("="*80)
    
    optimizer = BankruptcyQueryOptimizer(enable_logging=True)
    query = "section 363(f)"
    
    print(f"\nOriginal Query: {query}")
    print("\nRunning optimization...")
    
    result = await optimizer.optimize_query(query)
    
    print(f"\nExecution time: {result['execution_time']}")
    print(f"Active consultants: {result['active_consultants']}/{result['consultant_count']}")
    
    if result['active_consultant_names']:
        print(f"\nConsultants with recommendations:")
        for name in result['active_consultant_names']:
            print(f"  - {name}")
    
    # Check if SI-7 provided recommendations
    si7_output = result['consultant_details'].get('SI-7-Statute-Citation-to-Core-Concept-Expansion')
    if si7_output and si7_output['has_recommendations']:
        print(f"\nSI-7 Recommendations:")
        for rec in si7_output['recommendations']:
            print(f"  - {rec['original']} → {rec['replacement']}")
            print(f"    Reason: {rec['reason']}")


async def test_case_query():
    """Test with a case citation query."""
    print("\n" + "="*80)
    print("Testing with case citation query")
    print("="*80)
    
    optimizer = BankruptcyQueryOptimizer(enable_logging=True)
    query = "Stern v. Marshall"
    
    print(f"\nOriginal Query: {query}")
    print("\nRunning optimization...")
    
    result = await optimizer.optimize_query(query)
    
    print(f"\nExecution time: {result['execution_time']}")
    print(f"Active consultants: {result['active_consultants']}/{result['consultant_count']}")
    
    if result['active_consultant_names']:
        print(f"\nConsultants with recommendations:")
        for name in result['active_consultant_names']:
            print(f"  - {name}")
    
    # Check if SI-8 provided recommendations
    si8_output = result['consultant_details'].get('SI-8-Case-Citation-to-Core-Concept-Expansion')
    if si8_output and si8_output['has_recommendations']:
        print(f"\nSI-8 Recommendations:")
        for rec in si8_output['recommendations']:
            print(f"  - {rec['original']} → {rec['replacement']}")
            print(f"    Reason: {rec['reason']}")


async def test_mixed_query():
    """Test with both statute and case citations."""
    print("\n" + "="*80)
    print("Testing with mixed citation query")
    print("="*80)
    
    optimizer = BankruptcyQueryOptimizer(enable_logging=True)
    query = "section 365(b) Till"
    
    print(f"\nOriginal Query: {query}")
    print("\nRunning optimization...")
    
    result = await optimizer.optimize_query(query)
    
    print(f"\nExecution time: {result['execution_time']}")
    print(f"Active consultants: {result['active_consultants']}/{result['consultant_count']}")
    
    # Show first optimized query
    if result['optimized_queries']['version1']:
        print(f"\nVersion 1 (All Rules):")
        print(f"Query: {result['optimized_queries']['version1']['query']}")


async def test_no_citation_query():
    """Test with a query that has no citations."""
    print("\n" + "="*80)
    print("Testing with non-citation query")
    print("="*80)
    
    optimizer = BankruptcyQueryOptimizer(enable_logging=True)
    query = "stalking horse"
    
    print(f"\nOriginal Query: {query}")
    print("\nRunning optimization...")
    
    result = await optimizer.optimize_query(query)
    
    print(f"\nExecution time: {result['execution_time']}")
    print(f"Active consultants: {result['active_consultants']}/{result['consultant_count']}")
    
    # Verify SI-7 and SI-8 ran but found no citations
    print("\nVerifying SI-7 and SI-8 behavior without citations...")
    for consultant in ['SI-7-Statute-Citation-to-Core-Concept-Expansion', 
                      'SI-8-Case-Citation-to-Core-Concept-Expansion']:
        output = result['consultant_details'].get(consultant)
        if output:
            print(f"  - {consultant}: {'has recommendations' if output['has_recommendations'] else 'no recommendations'}")


async def main():
    """Run all tests."""
    # Check for required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found in environment")
        return
    
    if not os.getenv("BRAVE_SEARCH_API_KEY"):
        print("Warning: BRAVE_SEARCH_API_KEY not found. Web search will be disabled.")
        print("SI-7 and SI-8 will run without web content enhancement.")
    
    # Run tests
    await test_statute_query()
    await test_case_query()
    await test_mixed_query()
    await test_no_citation_query()
    
    print("\n" + "="*80)
    print("All tests completed!")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())