"""Security Agent Implementation.

This module implements the Security Hawk agent using a ReAct graph.
It adapts the strictly typed AgentPayload into the LangGraph context
and maps the LLM's findings back into ReviewIssue objects.
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
from src.agents.security.graph import build_security_graph, SECURITY_TOOLS
from langchain_core.globals import set_debug  # <--- WORKS (included in core)
logger = get_logger(__name__)

# --- System Prompt ---
SECURITY_SYSTEM_PROMPT = """
You are "The Hawk", a Senior Security Auditor.
Your goal is to audit code for security vulnerabilities using deterministic tools.

### PROTOCOL:
1.  **Analyze Metadata**: Look at the filename.
    * If `.py`: Run `scan_secrets`, `analyze_ast`, and `audit_routes`.
    * If `requirements.txt`: Run `cve_lookup`.
    * Other: Run `scan_secrets` (for leaked keys).
2.  **Verify**: Do not blindly trust tool outputs. Context matters.
    * High Entropy variable named `checksum`? IGNORE.
    * High Entropy variable named `api_key`? REPORT.

### OUTPUT FORMAT:
Return a SINGLE JSON object containing a list of issues. Do not use Markdown.
Format:
{
  "issues": [
    {
      "title": "Short title of vulnerability",
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "line_number": <int>,
      "description": "Detailed explanation of the attack vector.",
      "suggestion": "Specific code fix or mitigation."
    }
  ]
}
If no issues are found, return {"issues": []}.
"""


class SecurityAgent(BaseAgent):
    """The Security Hawk Agent.

    It orchestrates the analysis of files using a LangGraph ReAct loop
    and converts findings into standardized ReviewIssues.
    """

    def __init__(self, name: str, slug: str, llm_provider: LLMProvider):
        """
        Initializes the agent and builds its specific ReAct graph.

        Args:
            name: Human readable name.
            slug: Machine key.
            llm_provider: The centralized AI provider.
        """
        # 1. Initialize Base Class (Contract Fulfillment)
        super().__init__(name=name, slug=slug, llm_provider=llm_provider)
        #set_debug(True)
        # 2. Get the specific model for this agent (LangChain compatible)
        # We use a lower temperature for deterministic security analysis
        self.model = self.llm.get_chat_model(temperature=0.1)

        # 3. Build the Graph using THIS model instance
        self.graph = build_security_graph(self.model)
        
        logger.info(f"Security Graph compiled for {self.name}")

    def run(self, payload: AgentPayload) -> List[ReviewIssue]:
        """Executes the security audit pipeline.

        Args:
            payload (AgentPayload): The input payload containing files to review.

        Returns:
            List[ReviewIssue]: A list of security issues found in the files.
        """
        all_issues: List[ReviewIssue] = []

        if not payload.target_files:
            logger.warning("Security Agent received empty file list.")
            return []

        for file_data in payload.target_files:
            logger.info(f"Security Agent analyzing: {file_data.file_path}")
            
            # 1. Prepare Input State for LangGraph
            initial_state = {
                "messages": [
                    SystemMessage(content=SECURITY_SYSTEM_PROMPT),
                    HumanMessage(content=f"Analyze this file.\nFilename: {file_data.file_path}\n\nCode:\n{file_data.content}")
                ],
                "filename": file_data.file_path,
                "file_content": file_data.content
            }

            try:
                # 2. Run the Graph (Synchronously via invoke)
                # Recursion limit controls the maximum "Thought -> Tool" loops
                final_state = self.graph.invoke(initial_state, config={"recursion_limit": 10})
                
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
                        category=Category.SECURITY,
                        severity=self._map_severity(issue.get("severity", "MEDIUM")),
                        title=issue.get("title", "Security Notice"),
                        body=issue.get("description", "No description provided."),
                        suggestion=issue.get("suggestion", "Please review manually."),
                        rationale="Automated Security Tool Finding",
                        policy_violated="security.general_vulnerability"
                    )
                    all_issues.append(mapped_issue)

            except json.JSONDecodeError:
                logger.error(f"Failed to parse Security Agent JSON for {file_data.file_path}")
            except Exception as e:
                logger.error(f"Security Agent failed on {file_data.file_path}: {e}")

        return all_issues

    def get_tools(self) -> List[Any]:
        """Retrieves the list of tools available to this agent."""
        return SECURITY_TOOLS

    def _map_severity(self, severity_str: str) -> Severity:
        """Helper to map LLM string severity to Enum using dictionary lookup."""
        try:
            # "HIGH" -> Severity.HIGH
            return Severity[severity_str.upper()]
        except KeyError:
            # Fallback for unknown strings
            return Severity.MEDIUM