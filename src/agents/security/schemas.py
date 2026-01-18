"""Security Agent Tool Schemas.

This module defines the strict Pydantic models for the deterministic output 
of security tools. It ensures that the Agent receives structured, validatable 
data rather than raw strings.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class SecuritySeverity(str, Enum):
    """Standardized severity levels for security findings."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


# --- Tool 1: CVE Lookup Schemas ---
class CVEInfo(BaseModel):
    """Details about a specific Common Vulnerabilities and Exposures (CVE) entry."""
    id: str
    severity: str = "UNKNOWN"
    summary: str
    fix_version: Optional[str] = None


class VulnerablePackage(BaseModel):
    """Represents a third-party package containing known vulnerabilities."""
    name: str
    version: str
    ecosystem: str
    severity: SecuritySeverity
    cves: List[CVEInfo]


class CVELookupResult(BaseModel):
    """Output schema for the dependency vulnerability scanner."""
    status: str  # "VULNERABLE", "SAFE", "ERROR"
    packages: List[VulnerablePackage] = []
    error_msg: Optional[str] = None


# --- Tool 2: Secret Scanning Schemas ---
class SecretMatch(BaseModel):
    """Details of a potential secret discovered in the code."""
    line_number: int
    type: str  # e.g., "AWS_ACCESS_KEY", "High_Entropy_String"
    method: str  # "REGEX_MATCH" or "HIGH_ENTROPY"
    snippet: str
    confidence: str  # "High", "Medium", "Low"


class SecretScanResult(BaseModel):
    """Output schema for the secret scanner."""
    found_secrets: bool
    matches: List[SecretMatch] = []


# --- Tool 3: AST / SAST Schemas ---
class SASTPattern(BaseModel):
    """A specific structural security flaw found via AST analysis."""
    line: int
    type: str  # e.g., "Dangerous_Sink", "SQL_Injection"
    risk: str  # e.g., "Command_Injection"
    severity: SecuritySeverity
    function: Optional[str] = None
    argument_var: Optional[str] = None
    details: str


class ASTAnalysisResult(BaseModel):
    """Output schema for the Static Application Security Testing engine."""
    risk_found: bool
    patterns: List[SASTPattern] = []
    error_msg: Optional[str] = None


# --- Tool 4: Route Audit Schemas ---
class RouteInfo(BaseModel):
    """Configuration details of a discovered web endpoint."""
    path: str
    method: str
    line: int
    decorators: List[str]
    standard_auth_found: bool


class RouteAuditResult(BaseModel):
    """Output schema for the API route permission auditor."""
    routes_found: List[RouteInfo] = []
    error_msg: Optional[str] = None