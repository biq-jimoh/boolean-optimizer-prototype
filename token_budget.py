# token_budget.py
"""
Token budget management for legal text fetching.
Handles allocation of available context window tokens across multiple citations.
"""
from typing import Dict, List


class TokenBudgetConfig:
    """Configuration for token budget allocation."""
    
    # GPT-4.1 context window and reserves
    TOTAL_CONTEXT_WINDOW = 1_000_000
    SYSTEM_PROMPTS_RESERVE = 50_000    # All consultant prompts
    EXECUTIVE_AGENT_RESERVE = 50_000   # Executive synthesis
    OUTPUT_RESERVE = 50_000            # Model outputs
    SAFETY_MARGIN = 100_000            # Buffer
    
    # Available for legal texts
    AVAILABLE_FOR_LEGAL_TEXTS = (
        TOTAL_CONTEXT_WINDOW - 
        SYSTEM_PROMPTS_RESERVE - 
        EXECUTIVE_AGENT_RESERVE - 
        OUTPUT_RESERVE - 
        SAFETY_MARGIN
    )  # = 750,000 tokens
    
    # Per-document limits
    MAX_TOKENS_PER_STATUTE = 50_000    # ~200 pages
    MAX_TOKENS_PER_CASE = 100_000      # ~400 pages
    MIN_TOKENS_PER_CITATION = 10_000   # Minimum useful content
    
    # Simple token estimation
    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough estimate: 1 token ≈ 4 characters"""
        return len(text) // 4


class TokenBudgetManager:
    """Manages token budget allocation across multiple citations."""
    
    def __init__(self, config: TokenBudgetConfig = None):
        self.config = config or TokenBudgetConfig()
    
    def allocate_budget(self, 
                       statute_citations: List[Dict[str, str]], 
                       case_citations: List[Dict[str, str]]) -> Dict[str, int]:
        """
        Dynamically allocate token budget across all citations.
        
        Args:
            statute_citations: List of statute citation dicts
            case_citations: List of case citation dicts
            
        Returns:
            Dict mapping citation key to allocated tokens
        """
        total_statutes = len(statute_citations)
        total_cases = len(case_citations)
        total_citations = total_statutes + total_cases
        
        if total_citations == 0:
            return {}
        
        allocations = {}
        
        # Strategy: Cases typically need more tokens than statutes
        # Use weighted allocation: cases get 2x weight of statutes
        STATUTE_WEIGHT = 1
        CASE_WEIGHT = 2
        
        total_weights = (total_statutes * STATUTE_WEIGHT + 
                        total_cases * CASE_WEIGHT)
        
        if total_weights == 0:
            return {}
        
        tokens_per_weight = self.config.AVAILABLE_FOR_LEGAL_TEXTS / total_weights
        
        # Allocate for statutes
        for citation in statute_citations:
            key = f"statute:{citation['citation']}"
            allocated = int(tokens_per_weight * STATUTE_WEIGHT)
            # Apply min/max bounds
            allocations[key] = max(
                min(allocated, self.config.MAX_TOKENS_PER_STATUTE),
                self.config.MIN_TOKENS_PER_CITATION
            )
        
        # Allocate for cases
        for citation in case_citations:
            key = f"case:{citation['case_name']}"
            allocated = int(tokens_per_weight * CASE_WEIGHT)
            # Apply min/max bounds
            allocations[key] = max(
                min(allocated, self.config.MAX_TOKENS_PER_CASE),
                self.config.MIN_TOKENS_PER_CITATION
            )
        
        # Redistribute unused budget proportionally
        used_budget = sum(allocations.values())
        remaining_budget = self.config.AVAILABLE_FOR_LEGAL_TEXTS - used_budget
        
        if remaining_budget > 1000:  # Only redistribute if significant
            # Distribute remaining budget proportionally to current allocations
            for key in allocations:
                if key.startswith('statute:'):
                    max_allowed = self.config.MAX_TOKENS_PER_STATUTE
                else:
                    max_allowed = self.config.MAX_TOKENS_PER_CASE
                
                current = allocations[key]
                if current < max_allowed:
                    share = current / used_budget
                    bonus = int(remaining_budget * share)
                    allocations[key] = min(current + bonus, max_allowed)
        
        return allocations