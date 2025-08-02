"""
Basic tests for the Bankruptcy Query Optimizer.
Run with: python test_optimizer.py
"""

import asyncio
import os
import sys
from bankruptcy_query_optimizer import BankruptcyQueryOptimizer, ConsultantOutput, ExecutiveOutput


def test_consultant_output_model():
    """Test the ConsultantOutput model."""
    print("Testing ConsultantOutput model...")
    
    # Test with recommendations
    output1 = ConsultantOutput(
        has_recommendations=True,
        recommendations=[
            {
                "original": "staulking horse",
                "replacement": "stalking horse",
                "reason": "correcting typo"
            }
        ]
    )
    assert output1.has_recommendations == True
    assert len(output1.recommendations) == 1
    assert output1.recommendations[0].original == "staulking horse"
    
    # Test without recommendations
    output2 = ConsultantOutput(
        has_recommendations=False,
        recommendations=[],
        summary="No typos identified"
    )
    assert output2.has_recommendations == False
    assert len(output2.recommendations) == 0
    assert output2.summary == "No typos identified"
    
    print("✓ ConsultantOutput model tests passed")


def test_optimizer_initialization():
    """Test optimizer initialization."""
    print("\nTesting optimizer initialization...")
    
    try:
        optimizer = BankruptcyQueryOptimizer(
            model="gpt-4.1",
            temperature=0.0,
            enable_logging=False
        )
        
        summary = optimizer.get_agent_summary()
        assert summary['model'] == "gpt-4.1"
        assert summary['consultant_count'] > 0
        assert summary['executive_loaded'] == True
        
        print(f"✓ Optimizer initialized successfully")
        print(f"  - Model: {summary['model']}")
        print(f"  - Consultants: {summary['consultant_count']}")
        print(f"  - Consultant names: {', '.join(summary['consultant_names'][:5])}...")
        
        return optimizer
        
    except Exception as e:
        print(f"✗ Optimizer initialization failed: {e}")
        return None


async def test_single_query_optimization(optimizer):
    """Test optimizing a single query."""
    print("\nTesting query optimization...")
    
    test_query = "preference action"
    
    try:
        result = await optimizer.optimize_query(test_query, max_concurrent=5)
        
        # Check result structure
        assert 'original_query' in result
        assert 'optimized_queries' in result
        assert 'execution_time' in result
        assert 'active_consultants' in result
        
        # Check optimized queries
        queries = result['optimized_queries']
        assert 'version1' in queries
        assert 'version2' in queries
        assert 'version3' in queries
        assert 'version4' in queries
        
        # Check each version has required fields
        for version in ['version1', 'version2', 'version3', 'version4']:
            assert 'query' in queries[version]
            assert 'allowed_rules' in queries[version]
            assert 'changes' in queries[version]
        
        print(f"✓ Query optimization successful")
        print(f"  - Original: {test_query}")
        print(f"  - Version 1: {queries['version1']['query']}")
        print(f"  - Execution time: {result['execution_time']}")
        print(f"  - Active consultants: {result['active_consultants']}")
        
        return result
        
    except Exception as e:
        print(f"✗ Query optimization failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_multiple_queries(optimizer):
    """Test optimizing multiple queries."""
    print("\nTesting multiple query optimization...")
    
    test_queries = [
        "section 363",
        "Till v. SCS Credit",
        "can't file"
    ]
    
    try:
        results = await asyncio.gather(
            *(optimizer.optimize_query(q, max_concurrent=3) for q in test_queries)
        )
        
        assert len(results) == len(test_queries)
        
        for i, result in enumerate(results):
            assert result is not None
            assert result['original_query'] == test_queries[i]
        
        print(f"✓ Multiple query optimization successful")
        print(f"  - Processed {len(results)} queries")
        
    except Exception as e:
        print(f"✗ Multiple query optimization failed: {e}")


def test_consultant_recommendation_format():
    """Test that consultant recommendations are properly formatted."""
    print("\nTesting consultant recommendation formatting...")
    
    from bankruptcy_query_optimizer import ConsultantRecommendation
    
    rec = ConsultantRecommendation(
        original="roll-up",
        replacement='roll-up OR rollup OR "roll up"',
        reason="adding hyphenation variations"
    )
    
    # Test string representation
    formatted = f"- {rec.original} is changed to {rec.replacement} ({rec.reason})"
    expected = '- roll-up is changed to roll-up OR rollup OR "roll up" (adding hyphenation variations)'
    
    assert formatted == expected
    print("✓ Consultant recommendation formatting correct")


async def run_all_tests():
    """Run all tests."""
    print("="*60)
    print("Bankruptcy Query Optimizer Tests")
    print("="*60)
    
    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠️  WARNING: OPENAI_API_KEY not set!")
        print("   API-dependent tests will be skipped.")
        print("   Set your API key to run full tests.")
        api_key_available = False
    else:
        api_key_available = True
    
    # Run model tests (no API needed)
    test_consultant_output_model()
    test_consultant_recommendation_format()
    
    if api_key_available:
        # Run API-dependent tests
        optimizer = test_optimizer_initialization()
        
        if optimizer:
            await test_single_query_optimization(optimizer)
            await test_multiple_queries(optimizer)
    
    print("\n" + "="*60)
    print("Test suite completed!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(run_all_tests())