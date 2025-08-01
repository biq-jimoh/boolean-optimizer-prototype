"""
Citation Detection Module for Bankruptcy Query Optimizer
Uses the Agent SDK to detect statute and case citations in queries.
"""

from typing import Optional, Dict
from pydantic import BaseModel, Field
from agents import Agent, Runner, ModelSettings


class StatuteCitationOutput(BaseModel):
    """Output structure for statute citation detection"""
    found: bool = Field(description="Whether a statute citation was found")
    citation: str = Field(default="", description="Original citation text from query")
    normalized: str = Field(default="", description="Normalized format: '11 U.S.C. § [section]'")
    subsection: str = Field(default="", description="Subsection if applicable, e.g., '(f)(1)'")


class CaseCitationOutput(BaseModel):
    """Output structure for case citation detection"""
    found: bool = Field(description="Whether a case citation was found")
    case_name: str = Field(default="", description="Case name found in query")
    search_format: str = Field(default="", description="Format for searching: 'Case Name, Court, Year'")


class CitationDetector:
    """Detects legal citations in queries using LLM agents."""
    
    def __init__(self, model: str = "gpt-4o", temperature: float = 0.1):
        self.model = model
        self.model_settings = ModelSettings(temperature=temperature, max_tokens=500)
        
        # Create specialized agents for detection
        self.statute_detector = Agent(
            name="statute_citation_detector",
            instructions="""You are an expert at detecting bankruptcy statute citations in queries.
            
Examples of statute citations you should detect:
- "11 U.S.C. § 363(f)" or "11 USC 363(f)"
- "section 365(b)" or "Section 365b"
- "362(d)" or "362d"
- "§ 547(c)(2)"

Normalize all citations to the format: "11 U.S.C. § [section number]"

For subsections:
- Extract them separately (e.g., "(f)" or "(b)(1)(A)")
- The normalized form should be the parent section only

You must return a structured JSON response with these fields:
- found: boolean
- citation: the original text as it appears in the query
- normalized: the normalized parent section (e.g., "11 U.S.C. § 363")
- subsection: any subsection indicators (e.g., "(f)" or "(b)(1)")

If no statute citation is found, return {"found": false}""",
            model=self.model,
            model_settings=self.model_settings,
            output_type=StatuteCitationOutput
        )
        
        self.case_detector = Agent(
            name="case_citation_detector", 
            instructions="""You are an expert at detecting bankruptcy case citations in queries.
            
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

You must return a structured JSON response with these fields:
- found: boolean
- case_name: the case name as found in the query
- search_format: formatted for searching, e.g., "Stern v. Marshall, U.S. Supreme Court, 2011"

If no case citation is found, return {"found": false}""",
            model=self.model,
            model_settings=self.model_settings,
            output_type=CaseCitationOutput
        )
    
    async def detect_statute_citation(self, query: str) -> Optional[Dict]:
        """
        Detect statute citations in the query.
        
        Returns:
            Dictionary with citation info if found, None otherwise
        """
        try:
            result = await Runner.run(self.statute_detector, query)
            output: StatuteCitationOutput = result.final_output
            
            if output.found:
                return {
                    'found': True,
                    'citation': output.citation,
                    'normalized': output.normalized,
                    'subsection': output.subsection
                }
            return None
        except Exception as e:
            print(f"Error detecting statute citation: {e}")
            return None
    
    async def detect_case_citation(self, query: str) -> Optional[Dict]:
        """
        Detect case citations in the query.
        
        Returns:
            Dictionary with case info if found, None otherwise
        """
        try:
            result = await Runner.run(self.case_detector, query)
            output: CaseCitationOutput = result.final_output
            
            if output.found:
                return {
                    'found': True,
                    'case_name': output.case_name,
                    'search_format': output.search_format
                }
            return None
        except Exception as e:
            print(f"Error detecting case citation: {e}")
            return None