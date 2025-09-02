"""
Bankruptcy Query Optimizer
A system that runs multiple consultant agents in parallel to optimize Boolean queries
for bankruptcy court transcript searches.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from agents import Agent, Runner, ModelSettings
from openai.types.shared import Reasoning
import time
from datetime import datetime

# Import new modules for web search functionality
from boolean_optimizer.citations.detector import CitationDetector
from boolean_optimizer.services.brave_search import BraveSearchService
from boolean_optimizer.web.content_validator import ContentValidator
from boolean_optimizer.web.content_extractor import ContentExtractor
from boolean_optimizer.utils.url_cleaner import clean_courtlistener_url
from boolean_optimizer.core.token_budget import TokenBudgetManager


# Structured output models for consultants
class ConsultantRecommendation(BaseModel):
    """Structure for a single recommendation from a consultant."""
    original: str = Field(description="The original text/pattern to be changed")
    replacement: str = Field(description="What it should be changed to")
    reason: str = Field(description="Brief explanation of why this change is recommended")


class ConsultantOutput(BaseModel):
    """Structured output for consultant agents."""
    has_recommendations: bool = Field(
        description="True if there are recommendations to apply, False if no changes needed"
    )
    recommendations: List[ConsultantRecommendation] = Field(
        default_factory=list,
        description="List of recommendations. Empty list if has_recommendations is False"
    )
    summary: Optional[str] = Field(
        default=None,
        description="Optional summary message, especially useful when no recommendations"
    )


# Structured output models for executive agent  
class VersionChange(BaseModel):
    """A single change applied in a version."""
    rule_id: str = Field(description="The rule ID (e.g., 'AC-1', 'SI-4')")
    rule_name: str = Field(description="The name of the rule")
    change: str = Field(description="Description of the specific change made")


class QueryVersion(BaseModel):
    """A single optimized query version."""
    allowed_rules: List[str] = Field(description="List of rule IDs allowed for this version")
    query: str = Field(description="The optimized query")
    changes: List[VersionChange] = Field(
        default_factory=list,
        description="List of changes applied in this version"
    )


class ExecutiveOutput(BaseModel):
    """Structured output for the executive agent."""
    version1: QueryVersion
    version2: QueryVersion
    version3: QueryVersion
    version4: QueryVersion


class BankruptcyQueryOptimizer:
    """
    Main optimizer class that coordinates consultant agents and executive synthesis.
    """
    
    def __init__(self, 
                 consultants_dir: str = "prompts/consultants", 
                 executive_path: str = "prompts/executive/executive-agent.txt",
                 model: str = "gpt-5",
                 temperature: float = 0.0,
                 enable_logging: bool = True,
                 brave_api_key: Optional[str] = None):
        self.consultants_dir = Path(consultants_dir)
        self.executive_path = Path(executive_path)
        self.model = model
        # GPT-5 models ignore temperature; keep for others
        temp_for_model = None if str(model).startswith("gpt-5") else temperature
        self.model_settings = ModelSettings(
            temperature=temp_for_model,
            parallel_tool_calls=False,
            reasoning=None,
            extra_body={"reasoning": {"effort": "minimal"}}
        )
        self.consultant_agents = []
        self.executive_agent = None
        self.enable_logging = enable_logging
        
        # Initialize web search components
        self.citation_detector = CitationDetector(model=model, temperature=temperature)
        self.brave_api_key = brave_api_key or os.getenv("BRAVE_SEARCH_API_KEY")
        if self.brave_api_key:
            self.brave_search = BraveSearchService(api_key=self.brave_api_key)
            self.content_validator = ContentValidator(model=model, temperature=temperature)
            self.content_extractor = ContentExtractor()
        else:
            self._log("Warning: BRAVE_SEARCH_API_KEY not found. SI-7 and SI-8 will run without web enhancement.")
            self.brave_search = None
            self.content_validator = None
            self.content_extractor = None
        
        self._load_agents()
    
    def _log(self, message: str):
        """Simple logging helper."""
        if self.enable_logging:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] {message}")
    
    def _load_agents(self):
        """Load all consultant agents and the executive agent from prompt files."""
        self._log(f"Loading agents from {self.consultants_dir} and {self.executive_path}")
        
        # Load mandatory formatting requirements
        requirements_path = Path("prompts/shared/mandatory_formatting_requirements.txt")
        requirements_content = ""
        if requirements_path.exists():
            try:
                with open(requirements_path, 'r') as f:
                    requirements_content = f.read()
                self._log("Loaded mandatory formatting requirements")
            except Exception as e:
                self._log(f"Warning: Could not load mandatory formatting requirements: {e}")
        else:
            self._log("Warning: mandatory_formatting_requirements.txt not found")
        
        # Load consultant agents with structured output
        consultant_files = sorted(self.consultants_dir.glob("*.txt"))
        self._log(f"Found {len(consultant_files)} consultant prompt files")
        
        for prompt_file in consultant_files:
            try:
                with open(prompt_file, 'r') as f:
                    original_instructions = f.read()
                
                # Inject mandatory formatting requirements
                if requirements_content and "{{MANDATORY_FORMATTING_REQUIREMENTS}}" in original_instructions:
                    original_instructions = original_instructions.replace(
                        "{{MANDATORY_FORMATTING_REQUIREMENTS}}",
                        requirements_content
                    )
                
                # Enhance instructions to work with structured output
                enhanced_instructions = f"""{original_instructions}

IMPORTANT: You must respond with a structured JSON output containing:
- has_recommendations: boolean (true if you have recommendations, false otherwise)
- recommendations: array of recommendation objects, each with:
  - original: the text to be changed
  - replacement: what it should be changed to  
  - reason: brief explanation
- summary: optional message (especially if no recommendations)

Example response with recommendations:
{{
  "has_recommendations": true,
  "recommendations": [
    {{
      "original": "staulking horse",
      "replacement": "stalking horse",
      "reason": "correcting typo"
    }}
  ]
}}

Example response without recommendations:
{{
  "has_recommendations": false,
  "recommendations": [],
  "summary": "No typos identified"
}}"""
                
                agent = Agent(
                    name=prompt_file.stem,
                    instructions=enhanced_instructions,
                    model=self.model,
                    model_settings=self.model_settings,
                    output_type=ConsultantOutput  # Structured output
                )
                self.consultant_agents.append(agent)
                self._log(f"Loaded consultant: {prompt_file.stem}")
                
            except Exception as e:
                self._log(f"Error loading consultant {prompt_file.stem}: {e}")
        
        # Load executive agent with structured output
        try:
            with open(self.executive_path, 'r') as f:
                executive_instructions = f.read()
            
            # Inject mandatory formatting requirements
            if requirements_content and "{{MANDATORY_FORMATTING_REQUIREMENTS}}" in executive_instructions:
                executive_instructions = executive_instructions.replace(
                    "{{MANDATORY_FORMATTING_REQUIREMENTS}}",
                    requirements_content
                )
            
            self.executive_agent = Agent(
                name="Executive-Agent",
                instructions=executive_instructions,
                model=self.model,
                model_settings=self.model_settings,
                output_type=ExecutiveOutput  # Structured output
            )
            self._log("Loaded executive agent")
            
        except Exception as e:
            self._log(f"Error loading executive agent: {e}")
            raise
    
    async def _pre_scan_for_citations(self, query: str) -> Dict[str, str]:
        """
        Pre-scans query for all citations and fetches content with token budget management.
        Returns enhanced queries for SI-7 and SI-8.
        """
        enhanced_queries = {}
        
        if not self.brave_search:
            return enhanced_queries
        
        # Detect ALL citations
        statute_result = await self.citation_detector.detect_statutes(query)
        case_result = await self.citation_detector.detect_cases(query)
        
        # Convert to dicts for budget allocation
        statute_citations = [
            {
                'citation': c.citation,
                'normalized': c.normalized,
                'subsection': c.subsection
            }
            for c in statute_result.citations
        ] if statute_result.found else []
        
        case_citations = [
            {
                'case_name': c.case_name,
                'search_format': c.search_format
            }
            for c in case_result.citations
        ] if case_result.found else []
        
        # Allocate token budget
        budget_manager = TokenBudgetManager()
        token_allocations = budget_manager.allocate_budget(
            statute_citations,
            case_citations
        )
        
        # Create all fetch tasks for maximum parallelism
        fetch_tasks = []
        
        # Add statute fetch tasks
        for citation in statute_citations:
            budget_key = f"statute:{citation['citation']}"
            max_tokens = token_allocations.get(budget_key, 50_000)
            
            task = asyncio.create_task(
                self._fetch_single_statute(citation, max_tokens)
            )
            fetch_tasks.append(('statute', citation['citation'], task))
        
        # Add case fetch tasks
        for citation in case_citations:
            budget_key = f"case:{citation['case_name']}"
            max_tokens = token_allocations.get(budget_key, 100_000)
            
            task = asyncio.create_task(
                self._fetch_single_case(citation, max_tokens)
            )
            fetch_tasks.append(('case', citation['case_name'], task))
        
        # Wait for all fetches in parallel
        if fetch_tasks:
            results = await asyncio.gather(
                *[task for _, _, task in fetch_tasks],
                return_exceptions=True
            )
            
            # Aggregate successful results
            statute_contents = {}
            case_contents = {}
            
            for i, (type, key, _) in enumerate(fetch_tasks):
                if not isinstance(results[i], Exception) and results[i]:
                    if type == 'statute':
                        statute_contents[key] = results[i]
                    else:
                        case_contents[key] = results[i]
            
            # Build enhanced queries
            if statute_contents:
                enhanced_query = f"{query}\n\n--- FETCHED STATUTE TEXTS ---"
                for citation, content in statute_contents.items():
                    enhanced_query += f"\n\n[{citation}]\n{content}"
                enhanced_queries['statute_enhanced_query'] = enhanced_query
            
            if case_contents:
                enhanced_query = f"{query}\n\n--- FETCHED CASE OPINION TEXTS ---"
                for case_name, content in case_contents.items():
                    enhanced_query += f"\n\n[{case_name}]\n{content}"
                enhanced_queries['case_enhanced_query'] = enhanced_query
            
        return enhanced_queries
    
    async def _fetch_single_statute(self, citation_info: Dict[str, str], max_tokens: int) -> Optional[str]:
        """
        Fetches content for a single statute citation with token limit.
        
        Args:
            citation_info: Dict with citation, normalized, subsection
            max_tokens: Maximum tokens for this citation
            
        Returns:
            Content string if successful, None otherwise
        """
        try:
            self._log(f"Fetching statute: {citation_info['citation']} (max {max_tokens} tokens)")
            
            # Search on law.cornell.edu
            search_results = await self.brave_search.search_statute(
                citation_info['normalized']
            )
            
            if not search_results:
                self._log(f"No search results found for statute {citation_info['citation']}")
                return None
                
            # Extract content with token limit
            self._log(f"Fetching content from: {search_results[0]['url']}")
            content = await self.content_extractor.extract_statute_text(
                search_results[0]['url'],
                citation_info.get('subsection'),
                max_tokens=max_tokens
            )
            
            if not content or len(content.strip()) < 100:
                self._log("Failed to extract meaningful content from page")
                return None
            
            # Validate with actual content
            validation = await self.content_validator.validate_statute_result(
                citation_info,
                search_results[0],
                content
            )
            
            if not validation.is_valid:
                self._log(f"Validation failed: {validation.reason}")
                return None
                
            self._log(f"Valid statute page found: {search_results[0]['url']}")
            
            # Return just the content
            return content
            
        except Exception as e:
            self._log(f"Error fetching statute {citation_info['citation']}: {e}")
            return None
    
    async def _legacy_check_and_fetch_statute(self, query: str) -> Optional[str]:
        """
        Detects statute citation and fetches content from law.cornell.edu
        """
        try:
            # 1. Quick LLM check for statute
            citation_info = await self.citation_detector.detect_statute_citation(query)
            if not citation_info or not citation_info.get('found'):
                return None
                
            self._log(f"Detected statute citation: {citation_info['citation']}")
            
            # 2. Search on law.cornell.edu
            search_results = await self.brave_search.search_statute(
                citation_info['normalized']
            )
            
            if not search_results:
                self._log("No search results found for statute")
                return None
                
            # 3. Extract content first to validate with actual page content
            self._log(f"Fetching content from: {search_results[0]['url']}")
            content = await self.content_extractor.extract_statute_text(
                search_results[0]['url'],
                citation_info.get('subsection')
            )
            
            if not content or len(content.strip()) < 100:
                self._log("Failed to extract meaningful content from page")
                return None
            
            # 4. Validate with actual content
            validation = await self.content_validator.validate_statute_result(
                citation_info,  # Pass full citation info dict
                search_results[0],
                content  # Pass the actual page content
            )
            
            if not validation.is_valid:
                self._log(f"Validation failed: {validation.reason}")
                return None
                
            self._log(f"Valid statute page found: {search_results[0]['url']}")
            
            # 5. Return enhanced query
            return f"{query}\n\nSTATUTE TEXT FROM {search_results[0]['url']}:\n{content}"
            
        except Exception as e:
            self._log(f"Error in statute pre-scan: {e}")
            return None
    
    async def _fetch_single_case(self, case_info: Dict[str, str], max_tokens: int) -> Optional[str]:
        """
        Fetches content for a single case citation with token limit.
        
        Args:
            case_info: Dict with case_name, search_format
            max_tokens: Maximum tokens for this citation
            
        Returns:
            Content string if successful, None otherwise
        """
        try:
            self._log(f"Fetching case: {case_info['case_name']} (max {max_tokens} tokens)")
            
            # Search on courtlistener.com
            search_results = await self.brave_search.search_case(
                case_info['search_format']
            )
            
            if not search_results:
                self._log(f"No search results found for case {case_info['case_name']}")
                return None
            
            # Clean CourtListener URL to ensure we get the main opinion page
            cleaned_url = clean_courtlistener_url(search_results[0]['url'])
            self._log(f"Cleaned URL: {cleaned_url}")
            
            # Extract content with token limit
            self._log(f"Fetching content from: {cleaned_url}")
            content = await self.content_extractor.extract_case_text(
                cleaned_url,
                max_tokens=max_tokens
            )
            
            if not content or len(content.strip()) < 100:
                self._log("Failed to extract meaningful content from page")
                return None
            
            # Validate with actual content
            validation = await self.content_validator.validate_case_result(
                case_info,
                search_results[0],
                content
            )
            
            if not validation.is_valid:
                self._log(f"Validation failed: {validation.reason}")
                return None
                
            self._log(f"Valid case opinion found: {cleaned_url}")
            
            # Return just the content
            return content
            
        except Exception as e:
            self._log(f"Error fetching case {case_info['case_name']}: {e}")
            return None
    
    async def _legacy_check_and_fetch_case(self, query: str) -> Optional[str]:
        """
        Detects case citation and fetches content from courtlistener.com
        """
        try:
            # 1. Quick LLM check for case
            case_info = await self.citation_detector.detect_case_citation(query)
            if not case_info or not case_info.get('found'):
                return None
                
            self._log(f"Detected case citation: {case_info['case_name']}")
            
            # 2. Search on courtlistener.com
            search_results = await self.brave_search.search_case(
                case_info['search_format']
            )
            
            if not search_results:
                self._log("No search results found for case")
                return None
                
            # 3. Clean the URL to ensure we get the main opinion page
            original_url = search_results[0]['url']
            cleaned_url = clean_courtlistener_url(original_url)
            
            if original_url != cleaned_url:
                self._log(f"Cleaned URL from: {original_url}")
                self._log(f"Cleaned URL to: {cleaned_url}")
                # Update the search result with cleaned URL
                search_results[0]['url'] = cleaned_url
            
            # 4. Extract content first to validate with actual page content
            self._log(f"Fetching content from: {search_results[0]['url']}")
            content = await self.content_extractor.extract_case_text(
                search_results[0]['url']
            )
            
            if not content or len(content.strip()) < 100:
                self._log("Failed to extract meaningful content from page")
                return None
            
            # 4. Validate with actual content
            validation = await self.content_validator.validate_case_result(
                case_info,  # Pass full case info dict
                search_results[0],
                content  # Pass the actual page content
            )
            
            if not validation.is_valid:
                self._log(f"Validation failed: {validation.reason}")
                return None
                
            self._log(f"Valid case opinion found: {search_results[0]['url']}")
            
            # 5. Return enhanced query
            return f"{query}\n\nCASE OPINION TEXT FROM {search_results[0]['url']}:\n{content}"
            
        except Exception as e:
            self._log(f"Error in case pre-scan: {e}")
            return None

    async def run_consultant(self, agent: Agent, query: str) -> Dict[str, Any]:
        """Run a single consultant agent and return its recommendations."""
        try:
            self._log(f"Running consultant: {agent.name}")
            result = await Runner.run(agent, query)
            
            # The output is already structured as ConsultantOutput
            output: ConsultantOutput = result.final_output
            
            # Format recommendations for executive if any exist
            formatted_recommendations = ""
            if output.has_recommendations and output.recommendations:
                rec_lines = ["Update the query so that:"]
                for rec in output.recommendations:
                    rec_lines.append(f"- {rec.original} is changed to {rec.replacement} ({rec.reason})")
                formatted_recommendations = "\n".join(rec_lines)
            elif output.summary:
                formatted_recommendations = output.summary
            else:
                formatted_recommendations = "No recommendations identified."
            
            self._log(f"Consultant {agent.name} completed with {len(output.recommendations)} recommendations")
            
            # Log the actual recommendations if any
            if output.has_recommendations and output.recommendations:
                for rec in output.recommendations:
                    self._log(f"  → {rec.original} ➔ {rec.replacement} (Reason: {rec.reason})")
            
            return {
                "consultant": agent.name,
                "recommendations": formatted_recommendations,
                "has_recommendations": output.has_recommendations,
                "structured_output": output.model_dump()  # Keep structured data
            }
        except Exception as e:
            self._log(f"Error running consultant {agent.name}: {e}")
            return {
                "consultant": agent.name,
                "recommendations": f"Error: {str(e)}",
                "has_recommendations": False,
                "structured_output": None
            }
    
    async def _apply_acronym_review(self, consultant_result: Dict[str, Any], original_query: str) -> Dict[str, Any]:
        """
        Apply acronym review to SI-7 and SI-8 recommendations.
        """
        # Only process SI-7 and SI-8
        if consultant_result['consultant'] not in ['SI-7-Statute-Citation-to-Core-Concept-Expansion', 
                                                  'SI-8-Case-Citation-to-Core-Concept-Expansion']:
            return consultant_result
        
        if not consultant_result.get('has_recommendations'):
            return consultant_result
        
        # Load the review agent if not already loaded
        if not hasattr(self, 'acronym_review_agent'):
            review_prompt_path = self.consultants_dir / 'RI-1-Review-Acronym-Expansion.txt'
            if not review_prompt_path.exists():
                self._log("RI-1 review consultant not found, skipping acronym review")
                return consultant_result
            
            try:
                # Load the review consultant
                with open(review_prompt_path, 'r') as f:
                    original_instructions = f.read()
                
                # Inject mandatory formatting requirements
                requirements_path = Path("prompts/shared/mandatory_formatting_requirements.txt")
                requirements_content = ""
                if requirements_path.exists():
                    with open(requirements_path, 'r') as f:
                        requirements_content = f.read()
                
                if requirements_content and "{{MANDATORY_FORMATTING_REQUIREMENTS}}" in original_instructions:
                    original_instructions = original_instructions.replace(
                        "{{MANDATORY_FORMATTING_REQUIREMENTS}}",
                        requirements_content
                    )
                
                # Enhance instructions for structured output
                enhanced_instructions = f"""{original_instructions}

IMPORTANT: You must respond with a structured JSON output containing:
- has_recommendations: boolean (true if you have recommendations, false otherwise)
- recommendations: array of recommendation objects, each with:
  - original: the text to be changed
  - replacement: what it should be changed to  
  - reason: brief explanation
- summary: optional message (especially if no recommendations)"""
                
                self.acronym_review_agent = Agent(
                    name='RI-1-Review-Acronym-Expansion',
                    instructions=enhanced_instructions,
                    model=self.model,
                    model_settings=self.model_settings,
                    output_type=ConsultantOutput  # Structured output
                )
                self._log("Loaded RI-1 review consultant for acronym expansion")
            except Exception as e:
                self._log(f"Error loading RI-1 review consultant: {e}")
                return consultant_result
        
        # Pass recommendations through the review
        review_input = f"""
Original query: {original_query}

Recommendations to review:
{consultant_result['recommendations']}
"""
        
        try:
            review_result = await self.run_consultant(self.acronym_review_agent, review_input)
            
            if review_result['has_recommendations']:
                # Replace the recommendations with the enhanced version
                consultant_result['recommendations'] = review_result['recommendations']
                self._log(f"Enhanced {consultant_result['consultant']} with acronym expansions")
            
            return consultant_result
        except Exception as e:
            self._log(f"Error in acronym review: {e}")
            return consultant_result  # Return original if review fails
    
    async def optimize_query(self, query: str, max_concurrent: int = 10) -> Dict[str, Any]:
        """
        Main method to optimize a query using all consultants and the executive.
        SI-7 and SI-8 wait for web content while other consultants run immediately.
        
        Args:
            query: The Boolean query to optimize
            max_concurrent: Maximum number of consultants to run simultaneously
        """
        start_time = time.time()
        self._log(f"Starting optimization for query: '{query}'")
        
        # Separate consultants into two groups
        immediate_consultants = []
        delayed_consultants = []  # SI-7 and SI-8
        
        for agent in self.consultant_agents:
            if agent.name in ["SI-7-Statute-Citation-to-Core-Concept-Expansion", 
                             "SI-8-Case-Citation-to-Core-Concept-Expansion"]:
                delayed_consultants.append(agent)
            else:
                immediate_consultants.append(agent)
        
        # Start pre-scan for SI-7/SI-8
        pre_scan_task = asyncio.create_task(self._pre_scan_for_citations(query))
        
        # Step 1: IMMEDIATELY run all other consultants
        self._log(f"Running {len(immediate_consultants)} consultants immediately with {self.model}")
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def run_consultant_with_semaphore(agent, enhanced_query=None):
            async with semaphore:
                return await self.run_consultant(agent, enhanced_query or query)
        
        # Run immediate consultants
        immediate_results = await asyncio.gather(
            *(run_consultant_with_semaphore(agent) for agent in immediate_consultants)
        )
        
        # Wait for pre-scan to complete
        if delayed_consultants:
            self._log("Waiting for pre-scan to complete for SI-7/SI-8")
            enhanced_queries = await pre_scan_task
        else:
            enhanced_queries = {}
        
        # Step 2: Run delayed consultants (SI-7/SI-8) with enhanced content
        delayed_results = []
        if delayed_consultants:
            # Only run consultants that have web content
            delayed_tasks = []
            for agent in delayed_consultants:
                should_run = False
                enhanced_query = query
                
                if agent.name == "SI-7-Statute-Citation-to-Core-Concept-Expansion":
                    if enhanced_queries.get('statute_enhanced_query'):
                        enhanced_query = enhanced_queries['statute_enhanced_query']
                        should_run = True
                    else:
                        self._log(f"Skipping {agent.name} - no statute content found")
                elif agent.name == "SI-8-Case-Citation-to-Core-Concept-Expansion":
                    if enhanced_queries.get('case_enhanced_query'):
                        enhanced_query = enhanced_queries['case_enhanced_query']
                        should_run = True
                    else:
                        self._log(f"Skipping {agent.name} - no case content found")
                else:
                    # Other delayed consultants (shouldn't happen, but just in case)
                    should_run = True
                
                if should_run:
                    delayed_tasks.append(run_consultant_with_semaphore(agent, enhanced_query))
            
            if delayed_tasks:
                self._log(f"Running {len(delayed_tasks)} delayed consultants with enhanced content")
                delayed_results = await asyncio.gather(*delayed_tasks)
                
                # Apply acronym review to SI-7/SI-8 results
                reviewed_results = []
                for result in delayed_results:
                    reviewed_result = await self._apply_acronym_review(result, query)
                    reviewed_results.append(reviewed_result)
                delayed_results = reviewed_results
            else:
                self._log("No delayed consultants to run (no web content found)")
        
        # Combine all results
        all_consultant_results = immediate_results + delayed_results
        
        # Step 3: Filter and format consultant recommendations
        active_recommendations = []
        consultant_summary = []
        all_structured_outputs = {}
        
        for result in all_consultant_results:
            if result["has_recommendations"]:
                active_recommendations.append(f"### {result['consultant']}\n{result['recommendations']}")
                consultant_summary.append(result['consultant'])
            
            # Store structured outputs for analysis
            if result.get("structured_output"):
                all_structured_outputs[result['consultant']] = result['structured_output']
        
        self._log(f"Active consultants: {len(active_recommendations)}/{len(all_consultant_results)}")
        if consultant_summary:
            self._log(f"Consultants with recommendations: {', '.join(consultant_summary)}")
        
        # Step 4: Prepare input for executive agent
        executive_input = self._prepare_executive_input(query, active_recommendations)
        
        # Step 5: Run executive agent to synthesize recommendations
        self._log(f"Running executive agent ({self.model}) to synthesize recommendations")
        executive_result = await Runner.run(self.executive_agent, executive_input)
        
        # Step 6: Process structured executive output
        executive_output: ExecutiveOutput = executive_result.final_output
        execution_time = time.time() - start_time
        self._log(f"Optimization completed in {execution_time:.2f} seconds")
        
        return {
            "original_query": query,
            "model_used": self.model,
            "consultant_count": len(all_consultant_results),
            "active_consultants": len(active_recommendations),
            "execution_time": f"{execution_time:.2f} seconds",
            "optimized_queries": executive_output.model_dump(),
            "active_consultant_names": consultant_summary,
            "consultant_details": all_structured_outputs  # Include structured consultant outputs
        }
    
    def _prepare_executive_input(self, query: str, recommendations: List[str]) -> str:
        """Format the input for the executive agent."""
        return f"""Query to optimize: {query}

## Consultant Recommendations

{chr(10).join(recommendations) if recommendations else "No consultant recommendations were provided."}

Please synthesize these recommendations and produce the 4 optimized query versions as specified in your instructions."""

    def optimize_query_sync(self, query: str, max_concurrent: int = 10) -> Dict[str, Any]:
        """Synchronous wrapper for optimize_query."""
        return asyncio.run(self.optimize_query(query, max_concurrent))
    
    def get_agent_summary(self) -> Dict[str, Any]:
        """Get a summary of loaded agents."""
        return {
            "model": self.model,
            "consultant_count": len(self.consultant_agents),
            "consultant_names": [agent.name for agent in self.consultant_agents],
            "executive_loaded": self.executive_agent is not None
        }
