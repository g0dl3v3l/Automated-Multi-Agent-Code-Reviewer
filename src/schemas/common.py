"""
Defines the shared data models and schemas used across the Multi-Agent Code Reviewer.

This module contains the global Pydantic models (ReviewIssue, SourceFile) and 
Enums (Severity, Category) that act as the standard "contract" for communication 
between the specialized Agents, the Orchestrator, and the Frontend.
"""

"""
Defines the shared data models and schemas used across the Multi-Agent Code Reviewer.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# --- Enums (Vocabulary) ---
class Severity(str, Enum):
    """Defines the criticality of a finding."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NITPICK = "NITPICK"

class Category(str, Enum):
    """Categorizes the type of issue found."""
    SECURITY = "SECURITY"
    PERFORMANCE = "PERFORMANCE"
    MAINTAINABILITY = "MAINTAINABILITY"
    ARCHITECTURE = "ARCHITECTURE"
    BEST_PRACTICE= "BEST_PRACTICE"
    
class FinalVerdict(str, Enum):
    """The high-level decision on the Pull Request."""
    APPROVE = "APPROVE"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    COMMENT_ONLY = "COMMENT_ONLY"

# --- Input Models (Data Flowing IN to Agents) ---
class SourceFile(BaseModel):
    """Represents a single file submitted for review."""
    file_path: str
    content: str

class ReviewContext(BaseModel):
    """Shared context for the review (metadata, config, extra docs)."""
    project_name: str = "Unknown Project"
    config: Dict[str, Any] = {}
    readme_content: Optional[str] = None
    manifest_content: Optional[str] = None

class AgentPayload(BaseModel):
    """The input package sent to an Agent by the Router."""
    target_files: List[SourceFile]
    context: ReviewContext

# --- Output Models (Data Flowing OUT of Agents) ---

class ReviewIssue(BaseModel):
    """
    Standardized object representing a SINGLE specific issue found by an agent.
    This corresponds to one item in the 'comments' list of the final JSON.
    """
    id: str = Field(description="Unique ID for the comment, e.g., 'c_1'")
    file_path: str
    line_start: int
    line_end: int
    category: Category
    severity: Severity
    title: str = Field(max_length=150, description="Short headline summary")
    body: str = Field(description="Detailed explanation of the error")
    suggestion: Optional[str] = Field(None, description="Code snippet fix")
    rationale: str = Field(description="Educational explanation of 'why'")
    references: List[str] = Field(default_factory=list, description="URLs to docs")
    policy_violated: Optional[str] = Field(None, description="Link to org_policy rule")

# --- Final System Output Models (The Contract) ---

class ReviewMeta(BaseModel):
    """Calculated metrics for UI Badges and Gamification."""
    final_verdict: FinalVerdict
    quality_score: int = Field(..., ge=0, le=100, description="0-100 score")
    risk_level: str = Field(..., description="CRITICAL, HIGH, or SAFE")
    total_vulnerabilities: int = Field(..., description="Total count of issues detected") 
    scan_duration_ms: float = 0.0
class ReviewResponse(BaseModel):
    """
    The Root Level Output Object.
    This exactly matches the 'Final JSON Example' in your specs.
    """
    review_id: str
    timestamp: str
    meta: ReviewMeta
    summary: str
    praise: List[str]
    comments: List[ReviewIssue]