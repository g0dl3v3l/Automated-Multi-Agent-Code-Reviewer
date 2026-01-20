"""
Performance Graph Factory.

This module defines the ReAct workflow for Agent B.
It provides a builder function `build_performance_graph` that constructs
a StateGraph using the injected LLM model.
"""

from typing import Annotated, List, TypedDict, Union
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage
from langchain_core.tools import tool
# 1. IMPORT THIS REDUCER
from langgraph.graph.message import add_messages 

from src.agents.performance.tools import (
    analyze_code_structure,
    inspect_loop_mechanics,
    map_async_execution,
    trace_data_flow
)

# ... (Tools definitions remain the same) ...

@tool
def scan_structure(code: str):
    """Analyzes Class/Function topology. Use this FIRST."""
    return analyze_code_structure(code)

@tool
def scan_loops(code: str):
    """X-Rays loops for N+1 queries."""
    return inspect_loop_mechanics(code)

@tool
def scan_async(code: str):
    """Checks for blocking calls inside async functions."""
    return map_async_execution(code)

@tool
def scan_resources(code: str):
    """Checks for memory leaks and infinite loops."""
    return trace_data_flow(code)

PERFORMANCE_TOOLS = [scan_structure, scan_loops, scan_async, scan_resources]

# --- 2. Define State (FIXED) ---
class AgentState(TypedDict):
    # CHANGED: Use add_messages to APPEND instead of OVERWRITE
    messages: Annotated[List[BaseMessage], add_messages]
    filename: str
    file_content: str

# --- 3. Graph Builder Function ---
def build_performance_graph(model):
    """
    Constructs the ReAct graph for the Performance Agent.
    """
    
    # Bind tools to the LLM
    model_with_tools = model.bind_tools(PERFORMANCE_TOOLS)

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
    workflow.add_node("tools", ToolNode(PERFORMANCE_TOOLS))

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