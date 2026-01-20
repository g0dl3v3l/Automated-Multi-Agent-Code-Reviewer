"""
Performance Agent Implementation.

This module implements "The Architect" (Agent B) using a ReAct graph.
It adapts the strict AgentPayload into the LangGraph context and maps
the LLM's findings back into ReviewIssue objects.
"""

import json
import uuid
from typing import List, Any

from langchain_core.messages import SystemMessage, HumanMessage

from src.core.interfaces import BaseAgent
from src.core.llm import LLMProvider
from src.schemas.common import (
    AgentPayload,
    ReviewIssue,
    Category,
    Severity
)
from src.utils.logger import get_logger
from src.agents.performance.graph import build_performance_graph, PERFORMANCE_TOOLS
from langchain_core.globals import set_debug
logger = get_logger(__name__)

# --- System Prompt ---
PERFORMANCE_SYSTEM_PROMPT = """
You are "The Architect", a Principal Systems Engineer.
Your goal is to optimize code for Scalability, Concurrency, and Maintainability.

### PROTOCOL:
1.  **Map the Territory**: ALWAYS start by running `scan_structure`.
    * Look for **"Monolithic Classes"** (method_count > 20) or "Spaghetti Code" (nesting > 4).
    * If found, flag as ARCHITECTURE issues.
2.  **Investigate Mechanics**:
    * If the code contains loops, run `scan_loops`.
    * Look specifically for Database/API calls inside loops (N+1 Problem).
    * If found, flag as PERFORMANCE (High Severity).
3.  **Verify Concurrency**:
    * If the code uses `async def`, run `scan_async`.
    * Flag any blocking calls (`time.sleep`, `requests`) as PERFORMANCE (Critical Severity).
4.  **Resource Audit**:
    * Run `scan_resources` to check for infinite loops or unbounded file reads.

### OUTPUT FORMAT:
Return a SINGLE JSON object containing a list of issues. Do not use Markdown.
Format:
{
  "issues": [
    {
      "title": "Short title of issue",
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "line_number": <int>,
      "description": "Detailed technical explanation.",
      "suggestion": "Refactoring advice (e.g., 'Extract Service', 'Use batch query')."
    }
  ]
}
If no issues are found, return {"issues": []}.
"""


class PerformanceAgent(BaseAgent):
    """The Architect Agent.

    It orchestrates the structural analysis of files using a LangGraph ReAct loop.
    """

    def __init__(self, name: str, slug: str, llm_provider: LLMProvider):
        """
        Initializes the agent and builds its specific ReAct graph.

        Args:
            name: Human readable name.
            slug: Machine key.
            llm_provider: The centralized AI provider.
        """
        # 1. Initialize Base Class
        super().__init__(name=name, slug=slug, llm_provider=llm_provider)

        # 2. Get the specific model for this agent
        # We use a slightly higher temperature (0.2) than Security (0.1) 
        # because Architecture requires a bit more reasoning/synthesis.
        self.model = self.llm.get_chat_model(temperature=0.2)
        set_debug(True)
        # 3. Build the Graph using THIS model instance
        self.graph = build_performance_graph(self.model)
        
        logger.info(f"Performance Graph compiled for {self.name}")

    def run(self, payload: AgentPayload) -> List[ReviewIssue]:
        """Executes the performance analysis pipeline.

        Args:
            payload (AgentPayload): The input payload containing files to review.

        Returns:
            List[ReviewIssue]: A list of performance/architectural issues found.
        """
        all_issues: List[ReviewIssue] = []

        if not payload.target_files:
            logger.warning("Performance Agent received empty file list.")
            return []

        for file_data in payload.target_files:
            logger.info(f"Performance Agent analyzing: {file_data.file_path}")
            
            # 1. Prepare Input State for LangGraph
            initial_state = {
                "messages": [
                    SystemMessage(content=PERFORMANCE_SYSTEM_PROMPT),
                    HumanMessage(content=f"Analyze this file.\nFilename: {file_data.file_path}\n\nCode:\n{file_data.content}")
                ],
                "filename": file_data.file_path,
                "file_content": file_data.content
            }

            try:
                # 2. Run the Graph (Synchronously via invoke)
                # Recursion limit controls the maximum "Thought -> Tool" loops
                final_state = self.graph.invoke(initial_state, config={"recursion_limit": 12})
                
                # 3. Extract and Parse Response
                last_message = final_state["messages"][-1]
                response_text = last_message.content

                # Clean potential markdown fences from LLM
                cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
                
                llm_output = json.loads(cleaned_text)
                found_issues = llm_output.get("issues", [])

                # 4. Map JSON to ReviewIssue Objects
                for issue in found_issues:
                    mapped_issue = ReviewIssue(
                        id=str(uuid.uuid4())[:8],
                        file_path=file_data.file_path,
                        line_start=issue.get("line_number", 1),
                        line_end=issue.get("line_number", 1),
                        category=Category.PERFORMANCE, # Default category
                        severity=self._map_severity(issue.get("severity", "MEDIUM")),
                        title=issue.get("title", "Performance Notice"),
                        body=issue.get("description", "No description provided."),
                        suggestion=issue.get("suggestion", "Consider refactoring."),
                        rationale="Structural Analysis Finding",
                        policy_violated="performance.scalability_standards"
                    )
                    
                    # Refine Category based on title/body keywords
                    # Updated to check for "Monolithic Class"
                    if "Monolithic Class" in mapped_issue.title or "Coupling" in mapped_issue.title:
                        mapped_issue.category = Category.ARCHITECTURE
                    
                    all_issues.append(mapped_issue)

            except json.JSONDecodeError:
                logger.error(f"Failed to parse Performance Agent JSON for {file_data.file_path}")
            except Exception as e:
                logger.error(f"Performance Agent failed on {file_data.file_path}: {e}")

        return all_issues

    def get_tools(self) -> List[Any]:
        """Retrieves the list of tools available to this agent."""
        return PERFORMANCE_TOOLS

    def _map_severity(self, severity_str: str) -> Severity:
        """Helper to map LLM string severity to Enum using dictionary lookup."""
        try:
            return Severity[severity_str.upper()]
        except KeyError:
            return Severity.MEDIUM