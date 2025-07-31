"""
Content Validation Module
Uses LLM to validate that search results contain the correct legal content.
"""

from typing import Dict
from pydantic import BaseModel, Field
from agents import Agent, Runner, ModelSettings


class ValidationOutput(BaseModel):
    """Output structure for content validation"""
    is_valid: bool = Field(description="Whether the content matches the citation")
    confidence: float = Field(description="Confidence score between 0 and 1")
    reason: str = Field(description="Explanation of the validation decision")


class ContentValidator:
    """Validates that web search results contain the correct legal content."""
    
    def __init__(self, model: str = "gpt-4o", temperature: float = 0.1):
        self.model = model
        self.model_settings = ModelSettings(temperature=temperature, max_tokens=500)
        
        # Create validation agents
        self.statute_validator = Agent(
            name="statute_content_validator",
            instructions="""You validate whether web search results contain the correct statute text.
            
Your task is to determine if a search result actually contains the statute being searched for.

Be strict in your validation:
- The page MUST be from law.cornell.edu (Legal Information Institute)
- The title or URL should clearly indicate it's the correct statute section
- The description should reference the specific section number
- Look for indicators like "U.S. Code", the section number, and relevant legal terminology

Return a structured response with:
- is_valid: true only if you're certain this is the correct statute page
- confidence: 0.0 to 1.0 (use 0.9+ only for clear matches)
- reason: brief explanation of your decision""",
            model=self.model,
            model_settings=self.model_settings,
            output_type=ValidationOutput
        )
        
        self.case_validator = Agent(
            name="case_content_validator",
            instructions="""You validate whether web search results contain the correct case opinion.
            
Your task is to determine if a search result actually contains the case being searched for.

Be strict in your validation:
- The page should be from courtlistener.com/opinion
- The title should contain the case name (parties)
- Look for court information and year if provided
- The description should indicate it's a court opinion

Consider variations in case names:
- "Stern v. Marshall" could appear as "Stern v Marshall" or "STERN v. MARSHALL"
- Partial matches are acceptable if clearly the same case

Return a structured response with:
- is_valid: true only if you're confident this is the correct case
- confidence: 0.0 to 1.0 (use 0.9+ only for clear matches)
- reason: brief explanation of your decision""",
            model=self.model,
            model_settings=self.model_settings,
            output_type=ValidationOutput
        )
    
    async def validate_statute_result(self, citation: str, search_result: Dict) -> ValidationOutput:
        """
        Validate that a search result contains the correct statute.
        
        Args:
            citation: The statute citation being searched for
            search_result: Search result dict with title, url, description
            
        Returns:
            ValidationOutput with validation results
        """
        try:
            # Prepare validation prompt
            prompt = f"""Validate this search result for statute: {citation}

Title: {search_result.get('title', '')}
URL: {search_result.get('url', '')}
Description: {search_result.get('description', '')}

Is this the correct statute page?"""
            
            result = await Runner.run(self.statute_validator, prompt)
            return result.final_output
            
        except Exception as e:
            print(f"Error validating statute result: {e}")
            # Return invalid result on error
            return ValidationOutput(
                is_valid=False,
                confidence=0.0,
                reason=f"Validation error: {str(e)}"
            )
    
    async def validate_case_result(self, case_name: str, search_result: Dict) -> ValidationOutput:
        """
        Validate that a search result contains the correct case.
        
        Args:
            case_name: The case name being searched for
            search_result: Search result dict with title, url, description
            
        Returns:
            ValidationOutput with validation results
        """
        try:
            # Prepare validation prompt
            prompt = f"""Validate this search result for case: {case_name}

Title: {search_result.get('title', '')}
URL: {search_result.get('url', '')}
Description: {search_result.get('description', '')}

Is this the correct case opinion?"""
            
            result = await Runner.run(self.case_validator, prompt)
            return result.final_output
            
        except Exception as e:
            print(f"Error validating case result: {e}")
            # Return invalid result on error
            return ValidationOutput(
                is_valid=False,
                confidence=0.0,
                reason=f"Validation error: {str(e)}"
            )