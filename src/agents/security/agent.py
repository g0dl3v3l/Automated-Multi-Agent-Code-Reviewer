"""Security Agent Implementation.

This module implements the Security Hawk agent using a ReAct graph.
It adapts the strictly typed AgentPayload into the LangGraph context
and maps the LLM's findings back into ReviewIssue objects.
"""

import json
import uuid
import re
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
from langchain_core.globals import set_debug

logger = get_logger(__name__)

# --- [UPGRADE] RANGE-AWARE SYSTEM PROMPT ---
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
3.  **Define Range**: If a vulnerability spans multiple lines (e.g., a multi-line SQL string or a large hardcoded dict), provide the `end_line_number`.

### CRITICAL OUTPUT INSTRUCTIONS:
* You must output **ONLY VALID JSON**.
* **DO NOT** include conversational text.
* Start your response directly with the character `{`.

### JSON FORMAT:
{
  "issues": [
    {
      "title": "Short title of vulnerability",
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "line_number": <int> (Start of the issue),
      "end_line_number": <int> (Optional: End of the issue block),
      "description": "Detailed explanation of the attack vector.",
      "suggestion": "Specific code fix or mitigation."
    }
  ]
}
If no issues are found, return {"issues": []}.
"""


class SecurityAgent(BaseAgent):
    """The Security Hawk Agent."""

    def __init__(self, name: str, slug: str, llm_provider: LLMProvider):
        super().__init__(name=name, slug=slug, llm_provider=llm_provider)
        set_debug(True)
        # Low temp for deterministic security analysis
        self.model = self.llm.get_chat_model(temperature=0.1)
        self.graph = build_security_graph(self.model)
        logger.info(f"Security Graph compiled for {self.name}")

    def run(self, payload: AgentPayload) -> List[ReviewIssue]:
        all_issues: List[ReviewIssue] = []

        if not payload.target_files:
            logger.warning("Security Agent received empty file list.")
            return []

        for file_data in payload.target_files:
            logger.info(f"Security Agent analyzing: {file_data.file_path}")
            
            initial_state = {
                "messages": [
                    SystemMessage(content=SECURITY_SYSTEM_PROMPT),
                    HumanMessage(content=f"Analyze this file.\nFilename: {file_data.file_path}\n\nCode:\n{file_data.content}")
                ],
                "filename": file_data.file_path,
                "file_content": file_data.content
            }

            try:
                final_state = self.graph.invoke(initial_state, config={"recursion_limit": 10})
                last_message = final_state["messages"][-1]
                response_text = last_message.content

                # Robust Parsing
                llm_output = self._parse_json(response_text)
                found_issues = llm_output.get("issues", [])

                # Prepare for line snapping
                file_lines = file_data.content.split("\n")

                for issue in found_issues:
                    # 1. Get Raw Lines
                    start_raw = issue.get("line_number", 1)
                    end_raw = issue.get("end_line_number", start_raw) # Default to start if missing

                    # 2. Snap Start Line (Fix Empty Lines)
                    final_start = self._snap_line(start_raw, file_lines)
                    
                    # 3. Handle End Line (Ensure valid range)
                    # If end_line was provided but is somehow smaller than start, fix it.
                    final_end = max(final_start, end_raw)

                    mapped_issue = ReviewIssue(
                        id=str(uuid.uuid4())[:8],
                        file_path=file_data.file_path,
                        line_start=final_start,
                        line_end=final_end, # <--- Now supports ranges
                        category=Category.SECURITY,
                        severity=self._map_severity(issue.get("severity", "MEDIUM")),
                        title=issue.get("title", "Security Notice"),
                        body=issue.get("description", "No description provided."),
                        suggestion=issue.get("suggestion", "Please review manually."),
                        rationale="Automated Security Tool Finding",
                        policy_violated="security.general_vulnerability"
                    )
                    all_issues.append(mapped_issue)

            except Exception as e:
                logger.error(f"Security Agent failed on {file_data.file_path}: {e}")

        return all_issues

    def _snap_line(self, raw_line: int, file_lines: List[str]) -> int:
        """Fixes 'Off-by-one' errors where AI flags empty lines."""
        idx = raw_line - 1
        idx = max(0, min(idx, len(file_lines) - 1))
        
        # Walk up if empty
        while idx > 0 and not file_lines[idx].strip():
            idx -= 1
            
        return idx + 1

    def _parse_json(self, text: str) -> dict:
        """Robust JSON extraction using Regex."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        try:
            match = re.search(r"(\{.*\})", text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
        cleaned = text.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
             logger.error(f"Failed to parse JSON. Raw content preview: {text[:200]}...")
             return {"issues": []}

    def get_tools(self) -> List[Any]:
        return SECURITY_TOOLS

    def _map_severity(self, severity_str: str) -> Severity:
        try:
            return Severity[severity_str.upper()]
        except KeyError:
            return Severity.MEDIUM