"""Security Agent Graph Definition.

This module defines the LangGraph state machine for the Security Agent.
It orchestrates the ReAct loop:
1. Agent analyzes context.
2. Agent selects tools (Scan Secrets, AST, CVE).
3. Tools execute and return evidence.
4. Agent synthesizes findings into a final verdict.
"""

"""Security Agent Graph Definition.

Defines the State Machine factory for the Security Agent.
"""
import json
from typing import Annotated, TypedDict, List, Any
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage
from langchain_core.tools import tool

from src.agents.security.tools import (
    scan_secrets,
    analyze_ast_patterns,
    audit_route_permissions,
    cve_lookup
)

# --- State Definition ---
class SecurityState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    filename: str
    file_content: str

# --- Tool Definitions (Same as before) ---
@tool("scan_secrets")
def tool_scan_secrets(file_content: str) -> str:
    """Scans code for hardcoded secrets (AWS keys, passwords) and high-entropy strings."""
    return json.dumps(scan_secrets(file_content))

@tool("analyze_ast")
def tool_analyze_ast(code_content: str) -> str:
    """Parses Python code to find structural vulnerabilities like Command Injection or eval()."""
    return json.dumps(analyze_ast_patterns(code_content))

@tool("audit_routes")
def tool_audit_routes(code_content: str) -> str:
    """Audits API routes (Flask/FastAPI) to check for missing authentication decorators."""
    return json.dumps(audit_route_permissions(code_content))

@tool("cve_lookup")
def tool_cve_lookup(file_content: str, ecosystem: str = "PyPI") -> str:
    """Checks dependency files (requirements.txt, package.json) for known CVEs."""
    return json.dumps(cve_lookup(file_content, ecosystem))

SECURITY_TOOLS = [tool_scan_secrets, tool_analyze_ast, tool_audit_routes, tool_cve_lookup]

# --- Graph Factory ---
def build_security_graph(llm: Any):
    """
    Constructs the ReAct State Graph using the provided LLM instance.
    
    Args:
        llm: The LangChain compatible chat model (e.g., ChatMistralAI).
    """
    
    # Define the agent node locally so it captures the 'llm' variable
    def agent_node(state: SecurityState):
        """The Brain: Decides what to do next using the injected LLM."""
        # Bind tools to the specific LLM instance passed in
        llm_with_tools = llm.bind_tools(SECURITY_TOOLS)
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    # Build the Workflow
    workflow = StateGraph(SecurityState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(SECURITY_TOOLS))

    workflow.set_entry_point("agent")
    
    # Logic: Agent -> (Tools or End)
    workflow.add_conditional_edges(
        "agent",
        tools_condition
    )
    # Logic: Tools -> Agent
    workflow.add_edge("tools", "agent")

    return workflow.compile()