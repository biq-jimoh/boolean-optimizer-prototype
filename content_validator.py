"""
Content Validation Module
Uses LLM to validate that search results contain the correct legal content.
Now works with raw HTML for better accuracy.
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
            instructions="""You validate whether web pages contain the correct statute text.
            
Your task is to analyze HTML content and determine if it contains the statute being searched for.

Be strict in your validation:
- The page MUST be from law.cornell.edu (Legal Information Institute)
- Look for the specific statute section and subsection in the HTML
- Understand that citations like "363a" mean section 363(a)
- Check for HTML anchors like <a name="a"> for subsections

Return a structured response with:
- is_valid: true only if you're certain this page contains the requested provision
- confidence: 0.0 to 1.0 (use 0.9+ only for clear matches)
- reason: brief explanation of your decision""",
            model=self.model,
            model_settings=self.model_settings,
            output_type=ValidationOutput
        )
        
        self.case_validator = Agent(
            name="case_content_validator",
            instructions="""You validate whether web pages contain the correct case opinion.
            
Your task is to analyze HTML content and determine if it contains the case being searched for.

Be strict in your validation:
- The page should be from courtlistener.com/opinion
- Look for the actual opinion text, not just citations or authorities pages
- Check for judge names, court information, and legal analysis
- The URL might have tabs like /authorities/ - these are NOT the opinion

Return a structured response with:
- is_valid: true only if this contains the actual court opinion
- confidence: 0.0 to 1.0 (use 0.9+ only for clear matches)
- reason: brief explanation of your decision""",
            model=self.model,
            model_settings=self.model_settings,
            output_type=ValidationOutput
        )
    
    async def validate_statute_result(self, citation_info: Dict[str, str], search_result: Dict, page_content: str = None) -> ValidationOutput:
        """
        Validate that a search result contains the correct statute.
        
        Args:
            citation_info: Dict with 'citation', 'normalized', and optionally 'subsection'
            search_result: Search result dict with title, url, description
            page_content: The raw HTML content of the page
            
        Returns:
            ValidationOutput with validation results
        """
        try:
            if page_content and not page_content.startswith("Error"):
                # Use full HTML for validation
                if citation_info.get('subsection'):
                    # User typed something like "544a", "544a1", "544a1Ai", etc.
                    prompt = f"""Validate this page for a statute citation.

URL: {search_result.get('url', '')}

FULL HTML CONTENT:
{page_content}

User searched for: "{citation_info['citation']}"
We interpret this as:
- Parent section: {citation_info['normalized']} 
- Subsection path: {citation_info['subsection']}

Please verify:
1. Is this the correct parent section ({citation_info['normalized']})?
2. Does this section contain the subsection path {citation_info['subsection']}?

Subsection examples:
- (a) = first level
- (a)(1) = second level 
- (a)(1)(A) = third level
- (a)(1)(A)(i) = fourth level

Return true if the page contains the parent section AND the specified subsection path."""
                else:
                    # User typed just a section number like "544"
                    prompt = f"""Validate this page for statute: {citation_info['normalized']}
    
URL: {search_result.get('url', '')}

FULL HTML CONTENT:
{page_content}

Is this the correct page for {citation_info['normalized']}?"""
            else:
                # Fallback to metadata validation
                prompt = f"""Validate this search result for statute: {citation_info.get('citation', citation_info.get('normalized', ''))}

Title: {search_result.get('title', '')}
URL: {search_result.get('url', '')}
Description: {search_result.get('description', '')}

Is this the correct statute page?"""
            
            result = await Runner.run(self.statute_validator, prompt)
            return result.final_output
            
        except Exception as e:
            print(f"Error validating statute result: {e}")
            return ValidationOutput(
                is_valid=False,
                confidence=0.0,
                reason=f"Validation error: {str(e)}"
            )
    
    async def validate_case_result(self, case_name: str, search_result: Dict, page_content: str = None) -> ValidationOutput:
        """
        Validate that a search result contains the correct case.
        
        Args:
            case_name: The case name being searched for
            search_result: Search result dict with title, url, description
            page_content: The raw HTML content of the page
            
        Returns:
            ValidationOutput with validation results
        """
        try:
            if page_content and not page_content.startswith("Error"):
                # Use full HTML for validation
                prompt = f"""Validate this HTML page for case: {case_name}

URL: {search_result.get('url', '')}

FULL HTML CONTENT:
{page_content}

Does this page contain the full opinion for the cited case {case_name}?

Important: 
- Look for the actual judicial opinion with analysis and decision
- Check if this is the main opinion page, not /authorities/ or /citations/
- The HTML should contain judge names, court analysis, legal reasoning
- Verify this is from courtlistener.com/opinion

Return true only if this contains the actual court opinion."""
            else:
                # Fallback to metadata validation
                prompt = f"""Validate this search result for case: {case_name}

Title: {search_result.get('title', '')}
URL: {search_result.get('url', '')}
Description: {search_result.get('description', '')}

Is this the correct case opinion?"""
            
            result = await Runner.run(self.case_validator, prompt)
            return result.final_output
            
        except Exception as e:
            print(f"Error validating case result: {e}")
            return ValidationOutput(
                is_valid=False,
                confidence=0.0,
                reason=f"Validation error: {str(e)}"
            )
