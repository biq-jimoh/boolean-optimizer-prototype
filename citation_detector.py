"""
Citation Detection Module for Bankruptcy Query Optimizer
Uses the Agent SDK to detect statute and case citations in queries.
"""

from typing import Optional, Dict, List
from pydantic import BaseModel, Field
from agents import Agent, Runner, ModelSettings
from openai.types.shared import Reasoning


class StatuteCitation(BaseModel):
    """Individual statute citation"""
    citation: str = Field(description="Original citation text from query")
    normalized: str = Field(description="Normalized format: '11 U.S.C. § [section]'")
    subsection: str = Field(default="", description="Subsection if applicable, e.g., '(f)(1)'")


class StatuteCitationsOutput(BaseModel):
    """Output structure for statute citation detection"""
    found: bool = Field(description="Whether any statute citations were found")
    citations: List[StatuteCitation] = Field(default_factory=list, description="List of all statute citations found")


class CaseCitation(BaseModel):
    """Individual case citation"""
    case_name: str = Field(description="Case name found in query")
    search_format: str = Field(description="Format for searching: 'Case Name, Court, Year'")


class CaseCitationsOutput(BaseModel):
    """Output structure for case citation detection"""
    found: bool = Field(description="Whether any case citations were found")
    citations: List[CaseCitation] = Field(default_factory=list, description="List of all case citations found")


class CitationDetector:
    """Detects legal citations in queries using LLM agents."""
    
    def __init__(self, model: str = "gpt-5", temperature: float = 0.0):
        self.model = model
        temp_for_model = None if str(model).startswith("gpt-5") else temperature
        self.model_settings = ModelSettings(
            temperature=temp_for_model,
            max_tokens=500,
            reasoning=None,
            extra_body={"reasoning": {"effort": "minimal"}}
        )
        
        # Create specialized agents for detection
        self.statute_detector = Agent(
            name="statute_citation_detector",
            instructions="""You are an expert at detecting ALL bankruptcy statute citations in queries.

Examples of statute citations you should detect:
- "11 U.S.C. § 363(f)" or "11 USC 363(f)" 
- "section 365(b)" or "Section 365b"
- "362(d)" or "362d"
- "§ 547(c)(2)"
- "363a" or "363A" (both mean section 363(a))
- "363f3" or "363F3" (both mean section 363(f)(3))
- "365b1A" or "365B1a" (both mean section 365(b)(1)(A))
- "547c2Bii" (means section 547(c)(2)(B)(ii))
- "727a2A" (means section 727(a)(2)(A))

Normalize all citations to the format: "11 U.S.C. § [section number]"

For subsections:
- People type them many ways - be flexible
- Extract what seems to be the subsection structure
- Add parentheses in the standard legal format
- Examples of what you might see:
  - "363a" → "(a)"
  - "363f3" → "(f)(3)"
  - "365b1A" → "(b)(1)(A)"
  - "547c2Bii" → "(c)(2)(B)(ii)"

Use your judgment to parse the subsection structure. Don't worry about perfect rules - focus on understanding the user's intent.

IMPORTANT: Find ALL statute citations in the query, not just the first one.

You must return a structured JSON response with:
- found: boolean (true if ANY statute citations found)
- citations: array of objects, each with:
  - citation: the original text as it appears in the query
  - normalized: the normalized parent section (e.g., "11 U.S.C. § 363")
  - subsection: your best interpretation of the subsection with parentheses

If no statute citations are found, return {"found": false, "citations": []}""",
            model=self.model,
            model_settings=self.model_settings,
            output_type=StatuteCitationsOutput
        )
        
        self.case_detector = Agent(
            name="case_citation_detector", 
            instructions="""You are an expert at detecting ALL bankruptcy case citations in queries.
            
Focus on landmark bankruptcy cases that are commonly cited. Examples:
- "Stern v. Marshall" or just "Stern"
- "Till v. SCS Credit" or just "Till"
- "RadLAX Gateway Hotel" or just "RadLAX"
- "Granfinanciera"
- "Indiana State Police Pension Trust v. Chrysler"

For each detected case, determine the proper search format including:
- Full case name
- Court (if known, especially for Supreme Court cases)
- Year (if commonly associated with the case)

IMPORTANT: Find ALL case citations in the query, not just the first one.

You must return a structured JSON response with:
- found: boolean (true if ANY case citations found)
- citations: array of objects, each with:
  - case_name: the case name as found in the query
  - search_format: formatted for searching, e.g., "Stern v. Marshall, U.S. Supreme Court, 2011"

If no case citations are found, return {"found": false, "citations": []}""",
            model=self.model,
            model_settings=self.model_settings,
            output_type=CaseCitationsOutput
        )
    
    async def detect_statutes(self, query: str) -> StatuteCitationsOutput:
        """
        Detect all statute citations in the query.
        
        Returns:
            StatuteCitationsOutput with all found citations
        """
        try:
            result = await Runner.run(self.statute_detector, query)
            output: StatuteCitationsOutput = result.final_output
            return output
        except Exception as e:
            print(f"Error detecting statute citations: {e}")
            return StatuteCitationsOutput(found=False, citations=[])
    
    async def detect_cases(self, query: str) -> CaseCitationsOutput:
        """
        Detect all case citations in the query.
        
        Returns:
            CaseCitationsOutput with all found citations
        """
        try:
            result = await Runner.run(self.case_detector, query)
            output: CaseCitationsOutput = result.final_output
            return output
        except Exception as e:
            print(f"Error detecting case citations: {e}")
            return CaseCitationsOutput(found=False, citations=[])
    
    # Legacy single-detection methods for backward compatibility
    async def detect_statute_citation(self, query: str) -> Optional[Dict]:
        """
        Detect a single statute citation (legacy method).
        Returns the first citation found or None.
        """
        output = await self.detect_statutes(query)
        if output.found and output.citations:
            citation = output.citations[0]
            return {
                'found': True,
                'citation': citation.citation,
                'normalized': citation.normalized,
                'subsection': citation.subsection
            }
        return None
    
    async def detect_case_citation(self, query: str) -> Optional[Dict]:
        """
        Detect a single case citation (legacy method).
        Returns the first citation found or None.
        """
        output = await self.detect_cases(query)
        if output.found and output.citations:
            citation = output.citations[0]
            return {
                'found': True,
                'case_name': citation.case_name,
                'search_format': citation.search_format
            }
        return None
