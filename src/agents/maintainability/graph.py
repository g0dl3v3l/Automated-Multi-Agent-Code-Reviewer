"""
Maintainability Graph Factory.

This module defines the ReAct workflow for Agent C (The Tech Lead).
It provides a builder function `build_maintainability_graph` that constructs
a StateGraph using the injected LLM model.
"""

from typing import Annotated, List, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage
from langchain_core.tools import tool
from langgraph.graph.message import add_messages 

from src.agents.maintainability.tools import analyze_naming_conventions

# --- 1. Define Tools Wrappers ---

@tool
def scan_naming(code: str):
    """
    Naming Convention Analyzer.
    Scans the code for strict naming violations (e.g., camelCase in Python, snake_case in JS).
    Returns a list of violations with line numbers and fix suggestions.
    Use this to enforce 'Clean Code' naming standards objectively.
    """
    return analyze_naming_conventions(code)

# Consolidated Toolset
# Note: Complexity, Duplication, and Docstring checks are handled 
# semantically by the LLM, so they are not included as tools here.
MAINTAINABILITY_TOOLS = [scan_naming]

# --- 2. Define State ---
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    filename: str
    file_content: str

# --- 3. Graph Builder Function ---
def build_maintainability_graph(model):
    """
    Constructs the ReAct graph for the Maintainability Agent.
    
    Args:
        model: The LLM instance to bind tools to.
        
    Returns:
        CompiledStateGraph: The executable LangGraph workflow.
    """
    
    # Bind tools to the LLM
    model_with_tools = model.bind_tools(MAINTAINABILITY_TOOLS)

    def call_model(state: AgentState):
        """The reasoning node."""
        messages = state["messages"]
        response = model_with_tools.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: AgentState):
        """Determines if the agent is requesting a tool or is done."""
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            return "tools"
        return END

    # Build the Graph
    workflow = StateGraph(AgentState)

    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(MAINTAINABILITY_TOOLS))

    workflow.set_entry_point("agent")

    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            END: END
        }
    )

    workflow.add_edge("tools", "agent")

    return workflow.compile()