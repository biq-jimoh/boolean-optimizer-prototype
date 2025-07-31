"""
Bankruptcy Query Optimizer
A system that runs multiple consultant agents in parallel to optimize Boolean queries
for bankruptcy court transcript searches.
"""

import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from agents import Agent, Runner, ModelSettings
import time
from datetime import datetime


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
                 model: str = "gpt-4.1",
                 temperature: float = 0.1,
                 enable_logging: bool = True):
        self.consultants_dir = Path(consultants_dir)
        self.executive_path = Path(executive_path)
        self.model = model
        self.model_settings = ModelSettings(
            temperature=temperature,
            parallel_tool_calls=False
        )
        self.consultant_agents = []
        self.executive_agent = None
        self.enable_logging = enable_logging
        self._load_agents()
    
    def _log(self, message: str):
        """Simple logging helper."""
        if self.enable_logging:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] {message}")
    
    def _load_agents(self):
        """Load all consultant agents and the executive agent from prompt files."""
        self._log(f"Loading agents from {self.consultants_dir} and {self.executive_path}")
        
        # Load consultant agents with structured output
        consultant_files = sorted(self.consultants_dir.glob("*.txt"))
        self._log(f"Found {len(consultant_files)} consultant prompt files")
        
        for prompt_file in consultant_files:
            try:
                with open(prompt_file, 'r') as f:
                    original_instructions = f.read()
                
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
    
    async def optimize_query(self, query: str, max_concurrent: int = 10) -> Dict[str, Any]:
        """
        Main method to optimize a query using all consultants and the executive.
        
        Args:
            query: The Boolean query to optimize
            max_concurrent: Maximum number of consultants to run simultaneously
        """
        start_time = time.time()
        self._log(f"Starting optimization for query: '{query}'")
        
        # Step 1: Run consultant agents with concurrency limit
        self._log(f"Running {len(self.consultant_agents)} consultant agents with {self.model} (max {max_concurrent} concurrent)")
        
        # Create a semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def run_consultant_with_semaphore(agent):
            async with semaphore:
                return await self.run_consultant(agent, query)
        
        consultant_results = await asyncio.gather(
            *(run_consultant_with_semaphore(agent) for agent in self.consultant_agents)
        )
        
        # Step 2: Filter and format consultant recommendations
        active_recommendations = []
        consultant_summary = []
        all_structured_outputs = {}
        
        for result in consultant_results:
            if result["has_recommendations"]:
                active_recommendations.append(f"### {result['consultant']}\n{result['recommendations']}")
                consultant_summary.append(result['consultant'])
            
            # Store structured outputs for analysis
            if result.get("structured_output"):
                all_structured_outputs[result['consultant']] = result['structured_output']
        
        self._log(f"Active consultants: {len(active_recommendations)}/{len(consultant_results)}")
        if consultant_summary:
            self._log(f"Consultants with recommendations: {', '.join(consultant_summary)}")
        
        # Step 3: Prepare input for executive agent
        executive_input = self._prepare_executive_input(query, active_recommendations)
        
        # Step 4: Run executive agent to synthesize recommendations
        self._log(f"Running executive agent ({self.model}) to synthesize recommendations")
        executive_result = await Runner.run(self.executive_agent, executive_input)
        
        # Step 5: Process structured executive output
        executive_output: ExecutiveOutput = executive_result.final_output
        
        execution_time = time.time() - start_time
        self._log(f"Optimization completed in {execution_time:.2f} seconds")
        
        return {
            "original_query": query,
            "model_used": self.model,
            "consultant_count": len(consultant_results),
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