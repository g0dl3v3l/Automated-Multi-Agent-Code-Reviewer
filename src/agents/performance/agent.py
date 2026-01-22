"""Performance Agent Implementation.

This module implements "The Architect" (Agent B) using a ReAct graph logic.
It adapts the strict AgentPayload into the LangGraph context, orchestrates
the tool execution via the LLM, and maps the findings back into standardized
ReviewIssue objects.
"""

import json
import uuid
import re
from typing import List, Any, Dict

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

# --- [FIXED] AGGRESSIVE TOOL USE PROMPT ---
PERFORMANCE_SYSTEM_PROMPT = """
You are "The Architect", a Principal Systems Engineer.
Your goal is to perform a Multi-Language Code Review focusing on Scalability, Concurrency, and Maintainability.

### 🧠 STRATEGY: HYBRID CHAIN-OF-THOUGHT (CoT)
You must combine **Structural Analysis** (Tools) with **Semantic Reasoning** (Your Brain).
Do not rely on hardcoded lists. Use **First Principles** to identify bottlenecks in unknown libraries.

#### ONE-SHOT LEARNING EXAMPLE (How you should think):
> **Scenario:** You see `async def process()` calling `legacy_lib.download_sync(url)`.
> **Bad Robot:** " 'legacy_lib' is not in my banned list. No issue."
> **The Architect (You):** "1. I see an `async` context. 2. The function `download_sync` is called without `await`. 3. The name implies Network IO. 4. **Principle Violation:** Synchronous IO inside an Event Loop blocks the thread. 5. **Verdict:** Critical Blocking Call."

---

### 🔍 ANALYSIS FRAMEWORK (The First Principles)

#### 1. CONCURRENCY: THE "SYNC-IN-ASYNC" MISMATCH
* **The Principle:** In Async/Event-Driven code (Python `async`, JS, Go Goroutines), the thread must never block.
* **What to Look For (Generalize):**
    * Any function call inside an async block that appears **Synchronous** (no `await`) AND implies **IO or Waiting**.
    * **Signatures:** Names containing `fetch`, `download`, `read`, `write`, `sleep`, `wait`, `connect`, `request`.
    * **CPU Burn:** Infinite loops (`while True`) that lack a yielding mechanism (`await`, `sleep`, `yield`). This starves the scheduler.

#### 2. LOOP MECHANICS: THE "MULTIPLIER EFFECT"
* **The Principle:** Loops magnify the cost of operations. O(1) becomes O(N).
* **What to Look For (Generalize):**
    * **The N+1 Anti-Pattern:** Initiating a request (DB, HTTP, Disk) *inside* a loop iteration.
    * **Object Thrashing:** Instantiating heavy objects (Connections, Parsers) *inside* the loop instead of reusing them.
        * *Examples:* `re.compile()`, `json.Decoder()`, Database Connections, HTTP Clients.
    * **Unbounded Growth:** Accumulating data in a list/dict inside a `while` loop without a clear exit or memory limit (Memory Leak).

#### 3. ARCHITECTURE: COHESION & INTENT
* **The Principle:** A class should have a Single Responsibility.
* **What to Look For (Generalize):**
    * **Semantic Coupling:** Does one class import `SQL` drivers, `HTTP` clients, AND `GUI` libraries? (God Object).
    * **Arrow Code:** Deep nesting (>4 levels) often implies mixed levels of abstraction or poor state management.

---

### ⚙️ EXECUTION PROTOCOL (The Reasoning Loop)
Follow this process for every file.

1.  **PHASE 1: MAP THE TERRITORY (Run `scan_structure`)**
    * Analyze the topology. Note the `is_async` flags and `dependencies`.
    * **Self-Correction:** If you see imports/dependencies that sound like IO (e.g., `pyserial`, `boto3`, `pandas`) but the tool didn't flag them, trust your intuition.

2.  **PHASE 2: INVESTIGATE HOTSPOTS (Run `scan_loops`)**
    * If Phase 1 showed *any* complexity or data processing, run this tool.
    * **Critical Check:** Look at the `operations_inside`. If the tool missed a blocking call (e.g., `os.path.exists` in a tight loop), but you know it causes CPU burn or IO latency, **FLAG IT**.

3.  **PHASE 3: SYNTHESIS**
    * Generate your verdict based on the *Interaction* of elements (e.g., "Synchronous Call" + "Inside Loop" + "Async Function" = Disaster).

### 📝 OUTPUT FORMAT
Return a SINGLE JSON object.

{
  "issues": [
    {
      "title": "Short title (e.g., 'Implicit Blocking Call', 'Memory Leak Risk')",
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "line_number": <int> (Use 'line_start' from tool),
      "end_line_number": <int> (Use 'line_end' from tool),
      "description": "Technical explanation.",
      "rationale": "Chain of Thought: 1. Identified async function. 2. Spotted 'custom_lib.fetch' called synchronously. 3. Inferred this blocks the loop based on function name.",
      "suggestion": "Refactoring advice."
    }
  ]
}
If no issues are found, return {"issues": []}.
"""

class PerformanceAgent(BaseAgent):
    """The Architect Agent.

    It orchestrates the structural analysis of files using a LangGraph ReAct loop.
    It leverages a 'Two-Pass Protocol' to ensure both structural topology and 
    deep loop mechanics are analyzed before generating a report.
    """

    def __init__(self, name: str, slug: str, llm_provider: LLMProvider):
        """Initializes the Performance Agent.

        Args:
            name (str): Human-readable name (e.g., "The Architect").
            slug (str): Unique machine identifier (e.g., "performance-agent").
            llm_provider (LLMProvider): The centralized AI provider wrapper.
        """
        super().__init__(name=name, slug=slug, llm_provider=llm_provider)
        
        # We use a low temperature (0.1) to ensure the LLM follows the JSON schema
        # strictly and performs deterministic reasoning steps.
        self.model = self.llm.get_chat_model(temperature=0.1)
        #set_debug(True)
        
        # Compile the ReAct graph specific to this agent
        self.graph = build_performance_graph(self.model)
        logger.info(f"Performance Graph compiled for {self.name}")

    def run(self, payload: AgentPayload) -> List[ReviewIssue]:
        """Executes the performance analysis pipeline on the provided files.

        This method:
        1. Wraps the file content into a LangGraph state.
        2. Invokes the ReAct graph to generate a reasoned analysis.
        3. Parses the LLM's JSON output.
        4. Maps the raw findings into standardized `ReviewIssue` objects.

        Args:
            payload (AgentPayload): The input payload containing target files.

        Returns:
            List[ReviewIssue]: A list of detected performance and architectural issues.
        """
        all_issues: List[ReviewIssue] = []

        if not payload.target_files:
            logger.warning("Performance Agent received empty file list.")
            return []

        for file_data in payload.target_files:
            logger.info(f"Performance Agent analyzing: {file_data.file_path}")
            
            initial_state = {
                "messages": [
                    SystemMessage(content=PERFORMANCE_SYSTEM_PROMPT),
                    HumanMessage(content=f"Analyze this file.\nFilename: {file_data.file_path}\n\nCode:\n{file_data.content}")
                ],
                "filename": file_data.file_path,
                "file_content": file_data.content
            }

            try:
                # Execute Graph
                # Recursion limit set to 15 to allow:
                # 1. Thought -> 2. scan_structure -> 3. Output -> 4. Thought -> 5. scan_loops -> 6. Output -> 7. Final JSON
                final_state = self.graph.invoke(initial_state, config={"recursion_limit": 15})
                last_message = final_state["messages"][-1]
                
                # Robust JSON Parsing
                llm_output = self._parse_json(last_message.content)
                found_issues = llm_output.get("issues", [])

                file_lines = file_data.content.split("\n")

                for issue in found_issues:
                    # Extract raw lines from LLM
                    start_raw = issue.get("line_number", 1)
                    end_raw = issue.get("end_line_number", start_raw)

                    # Mathematical Line Snapping (Fixes off-by-one errors)
                    final_start = self._snap_line(start_raw, file_lines)
                    final_end = max(final_start, end_raw)

                    # Map to Domain Object
                    mapped_issue = ReviewIssue(
                        id=str(uuid.uuid4())[:8],
                        file_path=file_data.file_path,
                        line_start=final_start,
                        line_end=final_end,
                        category=Category.PERFORMANCE,
                        severity=self._map_severity(issue.get("severity", "MEDIUM")),
                        title=issue.get("title", "Performance Notice"),
                        body=issue.get("description", "No description provided."),
                        suggestion=issue.get("suggestion", "Consider refactoring."),
                        # Capture the CoT reasoning
                        rationale=issue.get("rationale", "Automated Structural Analysis"),
                        policy_violated="performance.scalability_standards"
                    )
                    
                    # Refine Category based on finding type
                    if any(x in mapped_issue.title for x in ["Monolithic Class", "Coupling", "Complexity"]):
                        mapped_issue.category = Category.ARCHITECTURE
                    
                    all_issues.append(mapped_issue)

            except Exception as e:
                logger.error(f"Performance Agent failed on {file_data.file_path}: {e}")

        return all_issues

    def _snap_line(self, raw_line: int, file_lines: List[str]) -> int:
        """Adjusts the line number to ensure it points to code, not whitespace.

        Args:
            raw_line (int): The 1-based line number returned by the LLM.
            file_lines (List[str]): The source code split by newlines.

        Returns:
            int: The adjusted 1-based line number.
        """
        idx = raw_line - 1
        # Clamp to valid range
        idx = max(0, min(idx, len(file_lines) - 1))
        
        # Walk upwards if the line is empty/whitespace
        while idx > 0 and not file_lines[idx].strip():
            idx -= 1
            
        return idx + 1

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Robustly extracts JSON from LLM responses, handling Markdown formatting.

        Args:
            text (str): The raw string response from the LLM.

        Returns:
            Dict[str, Any]: The parsed JSON object, or an empty issues dict on failure.
        """
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try Regex extraction for JSON block
        try:
            match = re.search(r"(\{.*\})", text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
            
        # Try stripping Markdown code fences
        cleaned = text.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
             return {"issues": []}

    def get_tools(self) -> List[Any]:
        """Retrieves the list of tools available to this agent.

        Returns:
            List[Any]: A list of callable tool objects (e.g., scan_structure).
        """
        return PERFORMANCE_TOOLS

    def _map_severity(self, severity_str: str) -> Severity:
        """Maps an LLM string severity to the system Enum.

        Args:
            severity_str (str): The severity string (e.g., "CRITICAL", "HIGH").

        Returns:
            Severity: The corresponding Severity Enum value.
        """
        try:
            return Severity[severity_str.upper()]
        except KeyError:
            return Severity.MEDIUM