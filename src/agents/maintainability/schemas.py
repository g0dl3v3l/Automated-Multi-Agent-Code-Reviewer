"""Maintainability Analysis Schemas.

This module defines the data structures for "The Tech Lead" (Agent C).
It captures metrics related to code hygiene, cognitive complexity, and
adherence to Clean Code principles (DRY, SRP, Naming Conventions).
"""

from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class SmellType(str, Enum):
    """Categories of code smells detected by the Maintainability Agent."""
    COMPLEXITY = "Complexity"            # High Cyclomatic Complexity / Deep Nesting
    NAMING = "Naming Convention"         # Snake_case vs CamelCase violations
    DUPLICATION = "Code Duplication"     # DRY violations
    FUNCTION_LENGTH = "Function Length"  # SRP violations (God Functions)
    ARGUMENT_COUNT = "Argument Count"    # Too many parameters
    DOCUMENTATION = "Documentation"      # Missing docstrings on public APIs
    DEAD_CODE = "Dead Code"              # Unused variables/imports

class NamingConvention(str, Enum):
    """Standard naming styles."""
    SNAKE_CASE = "snake_case"
    CAMEL_CASE = "camelCase"
    PASCAL_CASE = "PascalCase"
    UPPER_CASE = "UPPER_CASE"
    UNKNOWN = "unknown"

class FunctionMetrics(BaseModel):
    """Raw metrics extracted from a function definition."""
    name: str
    start_line: int
    end_line: int
    loc: int = Field(..., description="Lines of Code (excluding comments)")
    arg_count: int
    return_count: int
    cyclomatic_complexity: int = Field(..., description="Estimated logical paths")
    docstring_found: bool

class DuplicationBlock(BaseModel):
    """Represents a block of duplicated code."""
    file_path: str
    start_line: int
    end_line: int
    code_hash: str
    duplicate_count: int = Field(..., description="How many times this block appears")

class MaintainabilityOutput(BaseModel):
    """The raw output from the 'scan_maintainability' tool."""
    language: str
    functions_analyzed: List[FunctionMetrics]
    duplications: List[DuplicationBlock]
    naming_violations: List[Dict[str, str]] = Field(
        default_factory=list, 
        description="List of violations. E.g., {'name': 'myVar', 'expected': 'snake_case', 'line': 10}"
    )

class SmellImpact(BaseModel):
    """Quantifies the debt/effort required to fix."""
    effort_minutes: int
    risk_level: str  # LOW, MEDIUM, HIGH