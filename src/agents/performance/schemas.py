"""
Schemas for the Performance Agent Tools.

This module defines the strict Pydantic models used to structure the output
of the static analysis tools. These schemas provide the "Structural Map"
that enables the LLM to diagnose architectural and performance issues.
"""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

# --- Tool 1: Code Structure (The Blueprint) ---

class FunctionAnalysis(BaseModel):
    """Structural metrics for a single function."""
    name: str = Field(..., description="Name of the function")
    start_line: int
    loc: int = Field(..., description="Lines of Code count")
    arg_count: int = Field(..., description="Number of arguments")
    complexity: int = Field(..., description="Cognitive Complexity score")
    external_calls: List[str] = Field(..., description="List of external dependencies called")
    is_async: bool

class ClassAnalysis(BaseModel):
    """Structural metrics for a single class."""
    name: str
    start_line: int
    method_count: int = Field(..., description="Number of methods (indicator of God Class)")
    attribute_count: int = Field(..., description="Number of attributes inferred from __init__")
    docstring_present: bool

class StructureOutput(BaseModel):
    """Output model for the analyze_code_structure tool."""
    summary: Dict[str, int] = Field(..., description="Counts of classes and functions")
    classes: List[ClassAnalysis]
    functions: List[FunctionAnalysis]


# --- Tool 2: Loop Mechanics (N+1 Vision) ---

class LoopOperation(BaseModel):
    """Details of a function call occurring inside a loop."""
    call: str = Field(..., description="The function being called (e.g. User.objects.get)")
    type: str = Field(..., description="Category (ORM, External, Generic)")
    line: int

class LoopInfo(BaseModel):
    """Analysis of a specific iteration block."""
    line_start: int
    line_end: int
    loop_variable: str = Field(..., description="The variable being iterated over")
    operations_inside: List[LoopOperation] = Field(..., description="List of potential side-effects")

class LoopMechanicsOutput(BaseModel):
    """Output model for the inspect_loop_mechanics tool."""
    loops_analyzed: int
    risky_loops: List[LoopInfo]


# --- Tool 3: Async Map (Concurrency) ---

class Blocker(BaseModel):
    """A detected synchronous blocking call within an async scope."""
    line: int
    function: str = Field(..., description="The async function containing the block")
    blocking_call: str = Field(..., description="The detected synchronous call")
    suggestion: str

class AsyncMapOutput(BaseModel):
    """Output model for the map_async_execution tool."""
    async_functions_scanned: List[str]
    violations: List[Blocker]


# --- Tool 4: Resource Trace (Memory/CPU) ---

class ResourceHotspot(BaseModel):
    """A detected pattern indicating resource mismanagement."""
    line: int
    type: str = Field(..., description="e.g. Unbounded Read, Infinite Loop")
    pattern: str = Field(..., description="The specific code pattern matched")
    description: str

class ResourceOutput(BaseModel):
    """Output model for the trace_data_flow tool."""
    resource_hotspots: List[ResourceHotspot]