"""Universal Performance & Architecture Analysis Tools (Hybrid Edition).

This module implements a robust "Fallback Architecture" for code analysis.
It prioritizes the Universal Tree-sitter engine for cross-language support
(Python, JS, Go, Java, Rust, C++) but includes a native Python AST fallback
to prevent system crashes when binary bindings fail to load.
"""

import ast
import tree_sitter_languages
from tree_sitter import Node
from typing import Dict, Any, List, Set, Tuple

from src.utils.logger import get_logger
from src.agents.performance.schemas import (
    StructureOutput, ClassAnalysis, FunctionAnalysis,
    LoopMechanicsOutput, LoopInfo, LoopOperation
)

import logging
# Initialize Logger
logger = get_logger(__name__)
logger.setLevel(logging.INFO)

# --- 1. LANGUAGE CONFIGURATION ---
PARSERS = {}
LANGUAGES = {}

def _get_parser(lang_name: str) -> Tuple[Any, Any]:
    """Lazy loads the Tree-sitter parser with error handling.

    Args:
        lang_name (str): The standard name of the language (e.g., 'python', 'go').

    Returns:
        Tuple[Any, Any]: A tuple of (Parser, Language). Returns (None, None) on failure.
    """
    if lang_name not in PARSERS:
        try:
            language = tree_sitter_languages.get_language(lang_name)
            parser = tree_sitter_languages.get_parser(lang_name)
            PARSERS[lang_name] = parser
            LANGUAGES[lang_name] = language
        except TypeError:
            # Silently handle tree-sitter v0.22+ vs v0.21 wrapper conflict
            return None, None
        except Exception as e:
            print(f"[Tool:Parser] Failed to load Tree-sitter for {lang_name}: {e}", flush=True)
            return None, None
    return PARSERS[lang_name], LANGUAGES[lang_name]

def _detect_language(content: str) -> str:
    """Heuristically detects the programming language from source content.

    Args:
        content (str): The raw source code.

    Returns:
        str: The detected language key ('python', 'javascript', etc.) or 'unknown'.
    """
    if "def " in content and ("import " in content or "class " in content): return "python"
    if "import React" in content or "const " in content or "function " in content:
        if "export default" in content or "=>" in content: return "javascript"
    if "package " in content and "func " in content: return "go"
    if "public class " in content or "System.out.println" in content: return "java"
    if "fn " in content and ("let mut" in content or "impl " in content): return "rust"
    if "#include" in content and ("std::" in content or "int main" in content): return "cpp"
    return "unknown"

QUERIES = {
    "python": {
        "structure": """
            (class_definition name: (identifier) @name body: (block) @body) @class 
            (function_definition name: (identifier) @name body: (block) @body) @function
        """,
        "calls": """(call function: (_) @func_name) @call""",
        "loops": """(for_statement) @loop (while_statement) @loop""",
        "nesting_nodes": {"if_statement", "for_statement", "while_statement", "try_statement", "function_definition"}
    },
    "javascript": {
        "structure": """(class_declaration name: (identifier) @name body: (class_body) @body) @class (function_declaration name: (identifier) @name body: (statement_block) @body) @function (arrow_function body: (statement_block) @body) @arrow_func (method_definition name: (property_identifier) @name body: (statement_block) @body) @method""",
        "calls": """(call_expression function: (_) @func_name) @call""",
        "loops": """(for_statement) @loop (while_statement) @loop (do_statement) @loop""",
        "nesting_nodes": {"if_statement", "for_statement", "while_statement", "try_statement", "arrow_function", "function_declaration"}
    },
    "go": {
        "structure": """(function_declaration name: (identifier) @name body: (block) @body) @function (method_declaration name: (field_identifier) @name body: (block) @body) @method""",
        "calls": """(call_expression function: (identifier) @func_name) @call""",
        "loops": """(for_statement) @loop""",
        "nesting_nodes": {"if_statement", "for_statement", "func_literal"}
    },
    "java": {
        "structure": """(class_declaration name: (identifier) @name body: (class_body) @body) @class (method_declaration name: (identifier) @name body: (block) @body) @function""",
        "calls": """(method_invocation name: (identifier) @func_name) @call""",
        "loops": """(for_statement) @loop (while_statement) @loop""",
        "nesting_nodes": {"if_statement", "for_statement", "while_statement", "try_statement"}
    },
    "rust": {
        "structure": """(function_item name: (identifier) @name body: (block) @body) @function""",
        "calls": """(call_expression function: (_) @func_name) @call""",
        "loops": """(for_expression) @loop (loop_expression) @loop""",
        "nesting_nodes": {"if_expression", "for_expression", "match_expression"}
    },
    "cpp": {
        "structure": """(function_definition declarator: (function_declarator declarator: (identifier) @name) body: (compound_statement) @body) @function""",
        "calls": """(call_expression function: (_) @func_name) @call""",
        "loops": """(for_statement) @loop (while_statement) @loop""",
        "nesting_nodes": {"if_statement", "for_statement", "while_statement"}
    }
}

# --- 2. FALLBACK ENGINES (The Safety Net) ---

def _resolve_ast_name(node: ast.AST) -> str:
    """Recursively resolves AST names (e.g., 'self.db.query')."""
    if isinstance(node, ast.Name): return node.id
    if isinstance(node, ast.Attribute): return f"{_resolve_ast_name(node.value)}.{node.attr}"
    return ""

def _analyze_python_fallback(code: str) -> StructureOutput:
    """Performs structural analysis using Python's native AST module.

    This is triggered automatically if Tree-sitter binaries fail to load.

    Args:
        code (str): The raw Python source code.

    Returns:
        StructureOutput: The mapped structure via standard AST.
    """
    print("[Fallback] Engaging Python Native AST Parser.", flush=True)
    
    # [FIX] Initialize lists BEFORE the try block to guarantee definition scope
    classes = []
    functions = []
    
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        print(f"[Fallback] Syntax Error in user code: {e}", flush=True)
        return StructureOutput(language_detected="python", summary={"total_classes": 0, "total_functions": 0}, classes=[], functions=[])

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes.append(ClassAnalysis(
                name=node.name,
                start_line=node.lineno,
                end_line=getattr(node, 'end_lineno', node.lineno),
                method_count=len([n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]),
                attribute_count=0,
                patterns=["visitor_pattern"] if "Visitor" in node.name else [],
                docstring_present=ast.get_docstring(node) is not None
            ))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            complexity = 0
            nesting = 0
            calls = set()
            for sub in ast.walk(node):
                if isinstance(sub, (ast.For, ast.While, ast.If, ast.AsyncFor)):
                    complexity += 1
                    nesting = max(nesting, sub.col_offset // 4)
                if isinstance(sub, ast.Call):
                    name = _resolve_ast_name(sub.func)
                    if name: calls.add(name)
            
            functions.append(FunctionAnalysis(
                name=node.name,
                start_line=node.lineno,
                end_line=getattr(node, 'end_lineno', node.lineno),
                loc=getattr(node, 'end_lineno', node.lineno) - node.lineno,
                arg_count=len(node.args.args),
                complexity=complexity,
                nesting_depth=nesting,
                patterns=["magic_method"] if node.name.startswith("__") else [],
                dependencies=list(calls)[:20],
                is_async=isinstance(node, ast.AsyncFunctionDef)
            ))
            
    print(f"[Fallback] Success. Found {len(classes)} classes, {len(functions)} functions.", flush=True)
    return StructureOutput(
        language_detected="python",
        summary={"total_classes": len(classes), "total_functions": len(functions)},
        classes=classes, functions=functions
    )

def _inspect_loop_python_fallback(code: str) -> LoopMechanicsOutput:
    """Performs loop analysis using Python's native AST module.

    Args:
        code (str): The raw Python source code.

    Returns:
        LoopMechanicsOutput: The loop risks found via standard AST.
    """
    print("[Fallback] Engaging Python AST Loop Inspector.", flush=True)
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return LoopMechanicsOutput(loops_analyzed=0, risky_loops=[])
        
    risky = []
    HEAVY_OPS = {"get", "post", "put", "delete", "execute", "query", "fetch", "read", "write", "socket", "open", "connect"}
    MITIGATIONS = {"sleep", "wait", "yield", "await", "break", "return"}

    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            ops = []
            loop_body_nodes = list(ast.walk(node))
            
            # Check for Heavy IO
            for sub in loop_body_nodes:
                if isinstance(sub, ast.Call):
                    name = _resolve_ast_name(sub.func)
                    if any(op in name.lower() for op in HEAVY_OPS):
                        ops.append(LoopOperation(call=name, type="Potential IO/DB", line=sub.lineno))
            
            # Check for Infinite Loop / CPU Burn
            is_infinite = False
            if isinstance(node, ast.While):
                if (isinstance(node.test, ast.Constant) and node.test.value is True) or \
                   (isinstance(node.test, ast.NameConstant) and node.test.value is True):
                    is_infinite = True
            
            if is_infinite:
                # Scan for mitigations
                has_mitigation = False
                for sub in loop_body_nodes:
                    if isinstance(sub, (ast.Break, ast.Return, ast.Yield, ast.YieldFrom, ast.Await)):
                        has_mitigation = True
                        break
                    if isinstance(sub, ast.Call):
                        name = _resolve_ast_name(sub.func)
                        if any(m in name.lower() for m in MITIGATIONS):
                            has_mitigation = True
                            break
                
                if not has_mitigation:
                    ops.append(LoopOperation(call="infinite_loop", type="CPU_BURN", line=node.lineno))

            if ops:
                risky.append(LoopInfo(
                    line_start=node.lineno,
                    line_end=getattr(node, 'end_lineno', node.lineno),
                    loop_variable="inferred",
                    operations_inside=ops
                ))
    return LoopMechanicsOutput(loops_analyzed=1, risky_loops=risky)

# --- 3. MAIN TOOLS (With Hybrid Logic) ---

def _get_node_text(node: Node, code_bytes: bytes) -> str:
    """Extracts text from a Tree-sitter node."""
    return code_bytes[node.start_byte:node.end_byte].decode('utf-8')

def _calculate_nesting(node: Node, nesting_types: Set[str]) -> int:
    """Calculates nesting depth via iterative DFS."""
    max_depth = 0
    stack = [(node, 0)]
    while stack:
        current, depth = stack.pop()
        if current.type in nesting_types: depth += 1
        max_depth = max(max_depth, depth)
        for child in current.children: stack.append((child, depth))
    return max_depth if max_depth == 0 else max_depth - 1

def _extract_patterns(node: Node, lang: str) -> List[str]:
    """Extracts design patterns from node text."""
    patterns = []
    text = node.text.decode('utf-8', errors='ignore')
    if "Visitor" in text: patterns.append("visitor_pattern")
    if "Singleton" in text: patterns.append("singleton_pattern")
    if lang == "javascript" and "useEffect" in text: patterns.append("react_hook")
    return patterns

def analyze_code_structure(code_content: str) -> Dict[str, Any]:
    """Generates a Universal Structure Map of the code.

    Attempts to use Tree-sitter for high-fidelity parsing.
    Falls back to native AST if binary bindings fail for Python.

    Args:
        code_content (str): The raw source code.

    Returns:
        Dict[str, Any]: The `StructureOutput` JSON dictionary.
    """
    print(">>> STARTING analyze_code_structure", flush=True)
    print(f"\n\n>>> DEBUG: analyze_code_structure CALLED with {len(code_content)} bytes <<<\n\n", flush=True)
    lang = _detect_language(code_content)
    print(f"Detected language: {lang}", flush=True)
    
    parser, language = _get_parser(lang)
    
    # 1. Fallback Trigger (Parser missing)
    if not parser or lang not in QUERIES:
        if lang == "python": return _analyze_python_fallback(code_content).dict()
        return StructureOutput(language_detected=lang, summary={"total_classes": 0, "total_functions": 0}, classes=[], functions=[]).dict()

    # 2. Tree-sitter Execution
    try:
        tree = parser.parse(bytes(code_content, "utf8"))
        query = language.query(QUERIES[lang]["structure"])
        captures = query.captures(tree.root_node)
        print(f"Tree-sitter captures: {len(captures)}", flush=True)
    except Exception as e:
        # Fallback Trigger (Query/Runtime Error)
        print(f"Tree-sitter crashed: {e}. Attempting Fallback.", flush=True)
        if lang == "python": return _analyze_python_fallback(code_content).dict()
        return StructureOutput(language_detected=lang, summary={"total_classes": 0, "total_functions": 0}, classes=[], functions=[]).dict()

    classes_data = []
    functions_data = []
    
    for node, tag in captures:
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        loc = end_line - start_line
        name_node = node.child_by_field_name("name")
        name = _get_node_text(name_node, bytes(code_content, "utf8")) if name_node else "anonymous"
        
        if tag == "class":
            classes_data.append(ClassAnalysis(
                name=name, start_line=start_line, end_line=end_line,
                method_count=0, attribute_count=0,
                patterns=_extract_patterns(node, lang), docstring_present=False
            ))
        elif "function" in tag or "method" in tag or "arrow" in tag:
            nesting_nodes = QUERIES[lang].get("nesting_nodes", set())
            
            calls = set()
            if "calls" in QUERIES[lang]:
                try:
                    call_query = language.query(QUERIES[lang]["calls"])
                    for call_node, _ in call_query.captures(node):
                        calls.add(_get_node_text(call_node, bytes(code_content, "utf8")))
                except: pass

            functions_data.append(FunctionAnalysis(
                name=name, start_line=start_line, end_line=end_line, loc=loc,
                arg_count=0, complexity=0, 
                nesting_depth=_calculate_nesting(node, nesting_nodes),
                patterns=_extract_patterns(node, lang),
                dependencies=list(calls)[:20],
                is_async="async" in tag or "async" in name
            ))

    print(f"<<< FINISHED analyze_code_structure. Found {len(classes_data)} classes.", flush=True)
    return StructureOutput(
        language_detected=lang,
        summary={"total_classes": len(classes_data), "total_functions": len(functions_data)},
        classes=classes_data, functions=functions_data
    ).dict()


def inspect_loop_mechanics(code_content: str) -> Dict[str, Any]:
    """Performs deep loop analysis for N+1 detection and CPU burns.

    Uses Tree-sitter with a Python AST fallback.

    Args:
        code_content (str): The raw source code.

    Returns:
        Dict[str, Any]: The `LoopMechanicsOutput` JSON dictionary.
    """
    print(">>> STARTING inspect_loop_mechanics", flush=True)
    lang = _detect_language(code_content)
    parser, language = _get_parser(lang)
    
    # 1. Fallback Trigger
    if not parser or lang not in QUERIES:
        if lang == "python": return _inspect_loop_python_fallback(code_content).dict()
        return LoopMechanicsOutput(loops_analyzed=0, risky_loops=[]).dict()

    # 2. Tree-sitter Execution
    try:
        tree = parser.parse(bytes(code_content, "utf8"))
        query = language.query(QUERIES[lang]["loops"])
        loop_captures = query.captures(tree.root_node)
    except Exception:
        if lang == "python": return _inspect_loop_python_fallback(code_content).dict()
        return LoopMechanicsOutput(loops_analyzed=0, risky_loops=[]).dict()
    
    risky_loops = []
    HEAVY_OPS = ["fetch", "query", "execute", "db.", "http", "request", "sql", "write", "read", "send", "socket", "open", "connect"]
    MITIGATIONS = ["sleep", "wait", "yield", "await", "break", "return"]

    for node, _ in loop_captures:
        loop_text = _get_node_text(node, bytes(code_content, "utf8"))
        operations = []
        lines = loop_text.split('\n')
        
        # Check for Infinite Loop / CPU Burn
        # Simple heuristic for "while True" or "while(true)" or "for(;;)"
        is_infinite = "while True" in loop_text or "while(true)" in loop_text or "for(;;)" in loop_text or "loop {" in loop_text
        
        has_mitigation = False
        
        for i, line in enumerate(lines):
            # Check for Heavy IO
            for op in HEAVY_OPS:
                if op in line.lower():
                    operations.append(LoopOperation(call=op, type="Potential IO/DB", line=node.start_point[0] + 1 + i))
            
            # Check for mitigations if infinite
            if is_infinite:
                if any(m in line.lower() for m in MITIGATIONS):
                    has_mitigation = True

        if is_infinite and not has_mitigation:
             operations.append(LoopOperation(call="infinite_loop", type="CPU_BURN", line=node.start_point[0] + 1))

        if operations:
            risky_loops.append(LoopInfo(
                line_start=node.start_point[0] + 1,
                line_end=node.end_point[0] + 1,
                loop_variable="inferred",
                operations_inside=operations
            ))

    return LoopMechanicsOutput(loops_analyzed=len(loop_captures), risky_loops=risky_loops).dict()