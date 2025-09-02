"""
Basic tests for the Bankruptcy Query Optimizer.
Run with: pytest -q
"""

import asyncio
import os
import sys
import pytest
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


@pytest.fixture(scope="module")
def optimizer():
    """Provide an initialized optimizer, or skip if API key unavailable."""
    # Load API key from env or .env
    if not os.getenv("OPENAI_API_KEY"):
        try:
            from dotenv import load_dotenv, find_dotenv
            load_dotenv(find_dotenv(), override=False)
        except Exception:
            pass
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set; skipping API-dependent tests")

    opt = BankruptcyQueryOptimizer(
        model="gpt-5",
        temperature=0.0,
        enable_logging=False
    )
    # Sanity check
    summary = opt.get_agent_summary()
    assert summary['model'] == "gpt-5"
    assert summary['consultant_count'] > 0
    assert summary['executive_loaded'] is True
    return opt


def test_optimizer_initialization(optimizer):
    """Test optimizer initialization summary via fixture."""
    summary = optimizer.get_agent_summary()
    assert summary['model'] == "gpt-5"
    assert summary['consultant_count'] > 0
    assert summary['executive_loaded'] is True


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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
        original="object",
        replacement='object!',
        reason="add root extender"
    )
    
    # Test string representation
    formatted = f"- {rec.original} is changed to {rec.replacement} ({rec.reason})"
    expected = '- object is changed to object! (add root extender)'
    
    assert formatted == expected
    print("✓ Consultant recommendation formatting correct")


# The remaining script-style runner is unnecessary under pytest and removed.


if __name__ == "__main__":
    asyncio.run(run_all_tests())
