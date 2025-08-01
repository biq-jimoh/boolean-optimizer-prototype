#!/usr/bin/env python3
"""
Test script for multiple citation handling with token budget management.
"""
import asyncio
from bankruptcy_query_optimizer import BankruptcyQueryOptimizer


async def test_multiple_citations():
    """Test the system with queries containing multiple citations."""
    
    # Initialize optimizer
    optimizer = BankruptcyQueryOptimizer(
        consultants_dir="prompts/consultants",
        executive_prompt_path="prompts/executive/executive-agent.txt",
        model="gpt-4.1"
    )
    
    # Test cases
    test_queries = [
        # Single citations (should work as before)
        "544a",
        "Stern v. Marshall",
        
        # Multiple statute citations
        "544a and 547c2",
        "Compare 363a with 365b",
        
        # Multiple case citations
        "Stern and Till",
        "RadLAX Gateway Hotel and Granfinanciera",
        
        # Mixed citations
        "544a and Stern v. Marshall",
        "Till case and 547c2 preference defense",
        
        # Many citations (to test token budget allocation)
        "363a, 365b, 544a, 547c2, and 522f",
    ]
    
    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"Testing query: {query}")
        print(f"{'='*80}")
        
        try:
            result = await optimizer.optimize_query(query)
            print(f"\nOptimized query:\n{result}")
        except Exception as e:
            print(f"Error: {e}")
        
        print("\n" + "-"*40)
        await asyncio.sleep(2)  # Brief pause between queries


async def test_token_budget():
    """Test token budget allocation directly."""
    from token_budget import TokenBudgetManager
    
    manager = TokenBudgetManager()
    
    # Test different scenarios
    scenarios = [
        # Scenario 1: Single statute
        {
            "statutes": [{"citation": "544a"}],
            "cases": []
        },
        # Scenario 2: Multiple statutes
        {
            "statutes": [{"citation": "544a"}, {"citation": "547c2"}, {"citation": "363a"}],
            "cases": []
        },
        # Scenario 3: Mixed citations
        {
            "statutes": [{"citation": "544a"}, {"citation": "547c2"}],
            "cases": [{"case_name": "Stern"}, {"case_name": "Till"}]
        },
        # Scenario 4: Many citations
        {
            "statutes": [{"citation": f"36{i}" for i in range(10)}],
            "cases": [{"case_name": f"Case{i}"} for i in range(5)]
        }
    ]
    
    print("\nToken Budget Allocation Tests:")
    print("="*80)
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\nScenario {i}:")
        print(f"  Statutes: {len(scenario['statutes'])}")
        print(f"  Cases: {len(scenario['cases'])}")
        
        allocations = manager.allocate_budget(
            scenario['statutes'], 
            scenario['cases']
        )
        
        print("\n  Allocations:")
        for key, tokens in allocations.items():
            print(f"    {key}: {tokens:,} tokens")
        
        total = sum(allocations.values())
        print(f"\n  Total allocated: {total:,} tokens")
        print(f"  Available budget: {manager.config.AVAILABLE_FOR_LEGAL_TEXTS:,} tokens")
        print(f"  Utilization: {total/manager.config.AVAILABLE_FOR_LEGAL_TEXTS*100:.1f}%")


if __name__ == "__main__":
    print("Testing Multiple Citation Handling")
    print("="*80)
    
    # First test token budget allocation
    asyncio.run(test_token_budget())
    
    # Then test the full system
    print("\n\nTesting Full System with Multiple Citations")
    print("="*80)
    asyncio.run(test_multiple_citations())