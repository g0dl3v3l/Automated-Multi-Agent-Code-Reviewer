"""Security Agent Tools.

This module implements deterministic security analysis engines.
It includes:
1. Multi-ecosystem CVE Lookup (via OSV.dev).
2. Hybrid Secret Scanning (Regex + Shannon Entropy).
3. SAST Pattern Matching (AST-based).
4. Route Permission Auditing (Framework agnostic).
"""

import ast
import math
import re
import json
import requests
from typing import List, Dict, Any

from src.agents.security.schemas import (
    CVELookupResult,
    VulnerablePackage,
    CVEInfo,
    SecuritySeverity,
    SecretScanResult,
    SecretMatch,
    ASTAnalysisResult,
    SASTPattern,
    RouteAuditResult,
    RouteInfo,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


# --- TOOL 1: ROBUST CVE LOOKUP ---
def cve_lookup(file_content: str, ecosystem: str = "PyPI") -> Dict[str, Any]:
    """Scans a dependency file for known vulnerabilities using OSV.dev.

    Args:
        file_content (str): The raw content of the manifest (e.g., requirements.txt).
        ecosystem (str): The target ecosystem (e.g., 'PyPI', 'npm').

    Returns:
        Dict[str, Any]: A serialized CVELookupResult object.
    """
    url = "https://api.osv.dev/v1/querybatch"
    queries = []
    
    # 1. Parse Dependencies (Simple parser for requirements.txt style)
    # Note: In a real prod env, we would need specific parsers for package.json, etc.
    lines = file_content.split('\n')
    parsed_packages = []
    
    for line in lines:
        # Regex to capture "package==version"
        match = re.match(r'^([a-zA-Z0-9_\-]+)==([0-9\.]+)$', line.strip())
        if match:
            name, version = match.groups()
            queries.append({
                "package": {"name": name, "ecosystem": ecosystem},
                "version": version
            })
            parsed_packages.append((name, version))

    if not queries:
        return CVELookupResult(status="SAFE", error_msg="No valid dependencies found").model_dump()

    try:
        # 2. Batch Query OSV API
        response = requests.post(url, json={"queries": queries}, timeout=10)
        
        if response.status_code != 200:
            return CVELookupResult(status="ERROR", error_msg="OSV API failed").model_dump()

        results = response.json().get("results", [])
        vulnerable_packages = []

        # 3. Map Results
        for i, res in enumerate(results):
            vulns = res.get("vulns", [])
            if vulns:
                pkg_name, pkg_version = parsed_packages[i]
                cve_list = []
                for v in vulns[:3]: # Limit to top 3
                    cve_list.append(CVEInfo(
                        id=v.get("id"),
                        severity="HIGH", # OSV severity mapping is complex; default HIGH for safety
                        summary=v.get("summary") or "No description",
                        fix_version="Check OSV"
                    ))
                
                vulnerable_packages.append(VulnerablePackage(
                    name=pkg_name,
                    version=pkg_version,
                    ecosystem=ecosystem,
                    severity=SecuritySeverity.HIGH,
                    cves=cve_list
                ))

        if vulnerable_packages:
            return CVELookupResult(status="VULNERABLE", packages=vulnerable_packages).model_dump()
            
        return CVELookupResult(status="SAFE").model_dump()

    except Exception as e:
        logger.error(f"CVE Lookup failed: {e}")
        return CVELookupResult(status="ERROR", error_msg=str(e)).model_dump()


# --- TOOL 2: HYBRID SECRET SCANNING ---
def _calculate_entropy(text: str) -> float:
    """Calculates Shannon Entropy for a given string."""
    if not text:
        return 0.0
    entropy = 0
    for x in range(256):
        p_x = float(text.count(chr(x))) / len(text)
        if p_x > 0:
            entropy += - p_x * math.log(p_x, 2)
    return entropy

def scan_secrets(file_content: str) -> Dict[str, Any]:
    """Scans code for secrets using Regex and Entropy analysis.

    Args:
        file_content (str): The raw code to scan.

    Returns:
        Dict[str, Any]: A serialized SecretScanResult object.
    """
    matches = []
    lines = file_content.split('\n')

    # A. Regex Patterns (Subset of common providers)
    regex_db = {
        "AWS_Access_Key": r"(?<![A-Z0-9])[A-Z0-9]{20}(?![A-Z0-9])",
        "Generic_API_Key": r"(api_key|access_token|secret_key)\s*=\s*['\"][a-zA-Z0-9_\-]{20,}['\"]",
        "Private_Key": r"-----BEGIN PRIVATE KEY-----",
    }

    for i, line in enumerate(lines):
        line_num = i + 1
        line_stripped = line.strip()

        # 1. Check Regex
        for type_name, pattern in regex_db.items():
            if re.search(pattern, line):
                matches.append(SecretMatch(
                    line_number=line_num,
                    type=type_name,
                    method="REGEX_MATCH",
                    snippet=line_stripped[:20] + "...",
                    confidence="High"
                ))

        # 2. Check Entropy (for potential secrets missed by Regex)
        # Heuristic: Strings > 20 chars with Entropy > 4.5 usually indicate randomness
        # We look for quoted strings to avoid flagging code logic.
        string_literals = re.findall(r"['\"](.*?)['\"]", line)
        for s in string_literals:
            if len(s) > 20:
                entropy = _calculate_entropy(s)
                if entropy > 4.5:
                    matches.append(SecretMatch(
                        line_number=line_num,
                        type="High_Entropy_String",
                        method="HIGH_ENTROPY",
                        snippet=s[:10] + "...",
                        confidence="Medium"
                    ))

    return SecretScanResult(
        found_secrets=len(matches) > 0,
        matches=matches
    ).model_dump()


# --- TOOL 3: SAST PATTERN ENGINE ---
class SASTVisitor(ast.NodeVisitor):
    def __init__(self):
        self.findings = []

    def visit_Call(self, node):
        # Rule 1: Dangerous Sinks (Command Injection / RCE)
        dangerous_funcs = {
            'eval': 'Code_Injection',
            'exec': 'Code_Injection',
            'subprocess.call': 'Command_Injection',
            'os.system': 'Command_Injection',
            'pickle.load': 'Insecure_Deserialization'
        }
        
        func_name = self._get_func_name(node.func)
        if func_name in dangerous_funcs:
            # Taint Analysis Lite: Check if arg is a variable (Name) or literal (Constant)
            arg_type = "Literal"
            arg_var = None
            if node.args:
                if isinstance(node.args[0], ast.Name):
                    arg_type = "Variable"
                    arg_var = node.args[0].id
            
            # Only flag if it's not a literal (reduce false positives) or if it's eval/exec
            if arg_type == "Variable" or func_name in ['eval', 'exec']:
                self.findings.append(SASTPattern(
                    line=node.lineno,
                    type="Dangerous_Sink",
                    risk=dangerous_funcs[func_name],
                    severity=SecuritySeverity.HIGH if func_name != 'eval' else SecuritySeverity.CRITICAL,
                    function=func_name,
                    argument_var=arg_var,
                    details=f"Usage of {func_name} with {arg_type} argument."
                ))

        self.generic_visit(node)

    def _get_func_name(self, func_node):
        """Helper to extract 'module.func' or 'func' name."""
        if isinstance(func_node, ast.Name):
            return func_node.id
        elif isinstance(func_node, ast.Attribute):
            return f"{self._get_func_name(func_node.value)}.{func_node.attr}"
        return "unknown"

def analyze_ast_patterns(code_content: str) -> Dict[str, Any]:
    """Parses code to detect dangerous structural patterns.

    Args:
        code_content (str): The raw Python code.

    Returns:
        Dict[str, Any]: A serialized ASTAnalysisResult object.
    """
    try:
        tree = ast.parse(code_content)
        visitor = SASTVisitor()
        visitor.visit(tree)
        return ASTAnalysisResult(risk_found=len(visitor.findings) > 0, patterns=visitor.findings).model_dump()
    except SyntaxError:
        return ASTAnalysisResult(risk_found=False, error_msg="SyntaxError: Could not parse code").model_dump()


# --- TOOL 4: ROUTE AUDIT ---
class RouteVisitor(ast.NodeVisitor):
    def __init__(self):
        self.routes = []

    def visit_FunctionDef(self, node):
        # Heuristic: Look for decorators containing 'route', 'get', 'post'
        # This covers Flask (@app.route), FastAPI (@app.get), etc.
        route_decorator = None
        decorators = []
        
        for d in node.decorator_list:
            dec_name = self._get_decorator_name(d)
            decorators.append(f"@{dec_name}")
            if any(x in dec_name.lower() for x in ['route', 'get', 'post', 'put', 'delete', 'patch']):
                route_decorator = dec_name

        if route_decorator:
            # Check for Standard Auth keywords
            has_auth = any(
                keyword in d.lower() 
                for d in decorators 
                for keyword in ['login', 'auth', 'jwt', 'permission', 'role']
            )
            
            # Extract path if possible (lite effort)
            path = "unknown"
            # (Parsing args from decorator is complex, leaving as unknown/inferred for now)

            self.routes.append(RouteInfo(
                path=path,
                method="INFERRED",
                line=node.lineno,
                decorators=decorators,
                standard_auth_found=has_auth
            ))
            
        self.generic_visit(node)

    def _get_decorator_name(self, node):
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Call):
            return self._get_decorator_name(node.func)
        elif isinstance(node, ast.Attribute):
            return f"{self._get_decorator_name(node.value)}.{node.attr}"
        return "unknown"

def audit_route_permissions(code_content: str) -> Dict[str, Any]:
    """Scans for API routes and reports their decoration stack.

    Args:
        code_content (str): The raw Python code.

    Returns:
        Dict[str, Any]: A serialized RouteAuditResult object.
    """
    try:
        tree = ast.parse(code_content)
        visitor = RouteVisitor()
        visitor.visit(tree)
        return RouteAuditResult(routes_found=visitor.routes).model_dump()
    except SyntaxError:
        return RouteAuditResult(error_msg="SyntaxError").model_dump()