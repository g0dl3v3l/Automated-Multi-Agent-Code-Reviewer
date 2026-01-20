"""
Performance & Architecture Analysis Tools.

This module contains the AST-based static analysis engines for Agent B.
Unlike simple linters, these tools extract behavioral maps (topology,
execution flow, and resource usage) to allow the LLM to reason about
system design and performance bottlenecks.
"""

import ast
from typing import Dict, Any, List, Set, Optional

# --- Helper for Recursive Attribute Parsing ---
def _resolve_call_name(node: ast.AST) -> str:
    """Recursively resolves names like 'User.objects.get' from AST nodes."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return f"{_resolve_call_name(node.value)}.{node.attr}"
    return ""

def analyze_code_structure(code_content: str) -> Dict[str, Any]:
    """
    Extracts the structural topology of the code.

    This tool maps classes and functions to identify "God Objects",
    tight coupling (excessive external calls), and complexity hotspots.

    Args:
        code_content (str): The raw source code to analyze.

    Returns:
        Dict[str, Any]: A dictionary matching the `StructureOutput` schema,
        containing lists of class and function metrics.
    """
    try:
        tree = ast.parse(code_content)
    except SyntaxError:
        return {"summary": {"total_classes": 0, "total_functions": 0}, "classes": [], "functions": []}

    classes_analysis = []
    functions_analysis = []

    class StructureVisitor(ast.NodeVisitor):
        def visit_ClassDef(self, node):
            # Analyze Class Weight
            methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            
            # Heuristic: Count attributes defined in __init__
            attributes = set()
            for subnode in ast.walk(node):
                if isinstance(subnode, ast.Attribute) and isinstance(subnode.ctx, ast.Store):
                    if isinstance(subnode.value, ast.Name) and subnode.value.id == 'self':
                        attributes.add(subnode.attr)

            classes_analysis.append({
                "name": node.name,
                "start_line": node.lineno,
                "method_count": len(methods),
                "attribute_count": len(attributes),
                "docstring_present": ast.get_docstring(node) is not None
            })
            self.generic_visit(node)

        def visit_FunctionDef(self, node):
            self._analyze_function(node)

        def visit_AsyncFunctionDef(self, node):
            self._analyze_function(node)

        def _analyze_function(self, node):
            # Calculate Lines of Code
            loc = (node.end_lineno - node.lineno) if hasattr(node, 'end_lineno') else 0
            
            # Calculate "Coupling" (External Calls)
            external_calls = set()
            for subnode in ast.walk(node):
                if isinstance(subnode, ast.Call):
                    name = _resolve_call_name(subnode.func) # Use robust helper
                    if name: external_calls.add(name)

            # Calculate "Complexity" (Simple Nesting Score)
            complexity = 0
            for subnode in ast.walk(node):
                if isinstance(subnode, (ast.For, ast.While, ast.If, ast.AsyncFor)):
                    complexity += 1

            functions_analysis.append({
                "name": node.name,
                "start_line": node.lineno,
                "loc": loc,
                "arg_count": len(node.args.args),
                "complexity": complexity,
                "external_calls": list(external_calls)[:15], # Cap to avoid context overflow
                "is_async": isinstance(node, ast.AsyncFunctionDef)
            })

    visitor = StructureVisitor()
    visitor.visit(tree)

    return {
        "summary": {
            "total_classes": len(classes_analysis),
            "total_functions": len(functions_analysis)
        },
        "classes": classes_analysis,
        "functions": functions_analysis
    }


def inspect_loop_mechanics(code_content: str) -> Dict[str, Any]:
    """
    X-Rays iteration blocks to identify expensive operations inside loops.

    Instead of just checking for SQL, this returns a map of *all* operations
    inside loops, allowing the LLM to decide if 'api.fetch' or 'db.save'
    is an N+1 problem.

    Args:
        code_content (str): The raw source code.

    Returns:
        Dict[str, Any]: Matching `LoopMechanicsOutput`, listing loops and
        their internal operations.
    """
    try:
        tree = ast.parse(code_content)
    except SyntaxError:
        return {"loops_analyzed": 0, "risky_loops": []}

    loops = []
    
    # Signatures that often imply database/network IO
    IO_INDICATORS = {"get", "filter", "all", "create", "query", "add", "commit", "execute", "fetch", "request", "send"}

    class LoopVisitor(ast.NodeVisitor):
        def visit_For(self, node):
            self._analyze_loop(node, "for")

        def visit_AsyncFor(self, node):
            self._analyze_loop(node, "async for")

        def visit_While(self, node):
            self._analyze_loop(node, "while")

        def _analyze_loop(self, node, loop_type):
            operations = []
            loop_var = "unknown"
            
            # Extract loop variable if simple assignment
            if hasattr(node, 'target') and isinstance(node.target, ast.Name):
                loop_var = node.target.id

            # Walk ONLY the body of the loop
            for child in node.body:
                for subnode in ast.walk(child):
                    if isinstance(subnode, ast.Call):
                        # Use recursive helper to catch User.objects.get
                        call_name = _resolve_call_name(subnode.func)
                        if call_name:
                            # Categorize the call
                            cat = "Generic"
                            if any(ind in call_name.lower() for ind in IO_INDICATORS):
                                cat = "Potential IO/DB"
                            
                            operations.append({
                                "call": call_name,
                                "type": cat,
                                "line": subnode.lineno
                            })
            
            # Only report loops that actually do something interesting
            if operations:
                loops.append({
                    "line_start": node.lineno,
                    "line_end": getattr(node, 'end_lineno', node.lineno),
                    "loop_variable": loop_var,
                    "operations_inside": operations
                })
            
            # Continue visiting recursively (nested loops)
            self.generic_visit(node)

    visitor = LoopVisitor()
    visitor.visit(tree)

    return {
        "loops_analyzed": len(loops),
        "risky_loops": loops
    }


def map_async_execution(code_content: str) -> Dict[str, Any]:
    """
    Maps the async execution flow to detect synchronous blocking calls.

    Scans functions defined with `async def` and checks for known blocking
    patterns (time.sleep, requests, etc.).

    Args:
        code_content (str): The raw source code.

    Returns:
        Dict[str, Any]: Matching `AsyncMapOutput`, containing violations.
    """
    try:
        tree = ast.parse(code_content)
    except SyntaxError:
        return {"async_functions_scanned": [], "violations": []}

    violations = []
    scanned_funcs = []
    
    BLOCKING_CALLS = {
        "time.sleep": "Use 'await asyncio.sleep()' to yield control.",
        "requests.get": "Use 'httpx' or 'aiohttp' for non-blocking HTTP.",
        "requests.post": "Use 'httpx' or 'aiohttp'.",
        "urllib.request.urlopen": "Use async network libraries.",
        "open": "Use 'aiofiles' or run in a thread executor."
    }

    class AsyncVisitor(ast.NodeVisitor):
        def __init__(self):
            self.in_async = False
            self.current_func = ""

        def visit_AsyncFunctionDef(self, node):
            self.in_async = True
            self.current_func = node.name
            scanned_funcs.append(node.name)
            self.generic_visit(node)
            self.in_async = False

        def visit_FunctionDef(self, node):
            # Standard functions break the async context
            was_async = self.in_async
            self.in_async = False 
            self.generic_visit(node)
            self.in_async = was_async

        def visit_Call(self, node):
            if not self.in_async:
                return

            # Use recursive helper on node.func (not node itself)
            func_name = _resolve_call_name(node.func)
            suggestion = BLOCKING_CALLS.get(func_name)
            
            # Special check for 'open' as it is often a bare name
            if not suggestion and func_name == "open":
                suggestion = BLOCKING_CALLS["open"]

            if suggestion:
                violations.append({
                    "line": node.lineno,
                    "function": self.current_func,
                    "blocking_call": func_name,
                    "suggestion": suggestion
                })

    visitor = AsyncVisitor()
    visitor.visit(tree)

    return {
        "async_functions_scanned": scanned_funcs,
        "violations": violations
    }


def trace_data_flow(code_content: str) -> Dict[str, Any]:
    """
    Traces resource usage to detect memory leaks and CPU hogs.

    Identifies pattern like unbounded file reads and infinite loops without
    mitigation strategies (sleep/break).

    Args:
        code_content (str): The raw source code.

    Returns:
        Dict[str, Any]: Matching `ResourceOutput`.
    """
    try:
        tree = ast.parse(code_content)
    except SyntaxError:
        return {"resource_hotspots": []}
    
    hotspots = []

    class ResourceVisitor(ast.NodeVisitor):
        def visit_Call(self, node):
            # Check for .read() / .readlines() with NO arguments
            if isinstance(node.func, ast.Attribute) and node.func.attr in {"read", "readlines"}:
                if not node.args: 
                    hotspots.append({
                        "line": node.lineno,
                        "type": "Unbounded Read",
                        "pattern": f".{node.func.attr}()",
                        "description": "Reading a file without size limit can cause Out-Of-Memory errors."
                    })

        def visit_While(self, node):
            # Check for 'while True'
            if isinstance(node.test, ast.Constant) and node.test.value is True:
                if not self._has_mitigation(node):
                    hotspots.append({
                        "line": node.lineno,
                        "type": "Infinite Loop Risk",
                        "pattern": "while True",
                        "description": "Detected 'while True' loop with no obvious 'break', 'return', or 'sleep'."
                    })

        def _has_mitigation(self, node):
            # Naive scan for break, return, or sleep inside the loop
            for child in ast.walk(node):
                if isinstance(child, (ast.Break, ast.Return)):
                    return True
                if isinstance(child, ast.Call):
                    func_name = _resolve_call_name(child.func)
                    if "sleep" in func_name:
                        return True
            return False

    visitor = ResourceVisitor()
    visitor.visit(tree)

    return {
        "resource_hotspots": hotspots
    }