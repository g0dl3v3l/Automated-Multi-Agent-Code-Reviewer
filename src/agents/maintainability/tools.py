"""Maintainability Analysis Tools (Tree-sitter Edition).

This module implements the "Senses" for Agent C ("The Tech Lead").
It focuses on enforcing strict naming conventions across multiple languages
using Universal Tree-sitter.

Note: Logic for complexity, duplication, and docstring quality is handled
semantically by the Agent's LLM, not by static tools in this module.
"""

import re
import tree_sitter_languages
from typing import Dict, Any, List, Optional, Tuple
from src.utils.logger import get_logger
from src.agents.maintainability.schemas import NamingConvention

logger = get_logger(__name__)

# --- 1. CONFIGURATION ---

PARSERS = {}
LANGUAGES = {}

# Regex patterns for strict naming validation
NAMING_PATTERNS = {
    NamingConvention.SNAKE_CASE: re.compile(r"^[a-z0-9_]+$"),
    NamingConvention.CAMEL_CASE: re.compile(r"^[a-z][a-zA-Z0-9]*$"),
    NamingConvention.PASCAL_CASE: re.compile(r"^[A-Z][a-zA-Z0-9]*$"),
    NamingConvention.UPPER_CASE: re.compile(r"^[A-Z0-9_]+$"),
}

# The "Org Policy" Defaults for Naming
STYLE_GUIDES = {
    "python": {
        "function": NamingConvention.SNAKE_CASE,
        "variable": NamingConvention.SNAKE_CASE,
        "class": NamingConvention.PASCAL_CASE,
        "constant": NamingConvention.UPPER_CASE
    },
    "javascript": {
        "function": NamingConvention.CAMEL_CASE,
        "variable": NamingConvention.CAMEL_CASE,
        "class": NamingConvention.PASCAL_CASE,
        "constant": NamingConvention.UPPER_CASE
    },
    "typescript": {
        "function": NamingConvention.CAMEL_CASE,
        "variable": NamingConvention.CAMEL_CASE,
        "class": NamingConvention.PASCAL_CASE,
        "constant": NamingConvention.UPPER_CASE
    },
    "go": {
        # Go is nuanced: Exported=Pascal, Unexported=Camel. 
        # We enforce "Not Snake Case" for both.
        "function": NamingConvention.CAMEL_CASE, 
        "variable": NamingConvention.CAMEL_CASE,
        "class": NamingConvention.PASCAL_CASE, 
    },
    "rust": {
        "function": NamingConvention.SNAKE_CASE,
        "variable": NamingConvention.SNAKE_CASE,
        "class": NamingConvention.PASCAL_CASE, # Structs/Enums
        "constant": NamingConvention.UPPER_CASE
    }
}

# Tree-sitter Queries to locate identifiers
QUERIES = {
    "python": {
        "functions": """(function_definition name: (identifier) @name) @def""",
        "classes": """(class_definition name: (identifier) @name) @def""",
        "variables": """(assignment left: (identifier) @name) @def""",
    },
    "javascript": {
        "functions": """
            (function_declaration name: (identifier) @name) @def
            (method_definition name: (property_identifier) @name) @def
        """,
        "classes": """(class_declaration name: (identifier) @name) @def""",
        "variables": """(variable_declarator name: (identifier) @name) @def""",
    },
    "typescript": {
        "functions": """
            (function_declaration name: (identifier) @name) @def
            (method_definition name: (property_identifier) @name) @def
        """,
        "classes": """(class_declaration name: (type_identifier) @name) @def""",
        "variables": """(variable_declarator name: (identifier) @name) @def""",
    },
    "go": {
        "functions": """(function_declaration name: (identifier) @name) @def""",
        "classes": """(type_spec name: (type_identifier) @name) @def""", # Structs
        "variables": """(short_var_declaration left: (expression_list (identifier) @name)) @def""",
    },
    "rust": {
        "functions": """(function_item name: (identifier) @name) @def""",
        "classes": """(struct_item name: (type_identifier) @name) @def""",
        "variables": """(let_declaration pattern: (identifier) @name) @def""",
    }
}


def _get_parser(lang: str) -> Tuple[Any, Any]:
    """Lazy loads the Tree-sitter parser for the specified language.

    Args:
        lang (str): The language identifier (e.g., 'python', 'go').

    Returns:
        Tuple[Any, Any]: A tuple containing (Parser, Language). 
                         Returns (None, None) if loading fails.
    """
    if lang not in PARSERS:
        try:
            PARSERS[lang] = tree_sitter_languages.get_parser(lang)
            LANGUAGES[lang] = tree_sitter_languages.get_language(lang)
        except Exception as e:
            logger.warning(f"Failed to load parser for {lang}: {e}")
            return None, None
    return PARSERS[lang], LANGUAGES[lang]


def _detect_language(content: str) -> str:
    """Heuristically detects the programming language from source content.

    Args:
        content (str): The raw source code.

    Returns:
        str: The detected language ('python', 'javascript', 'go', 'rust', or 'unknown').
    """
    if "def " in content and "import " in content: return "python"
    if "fn " in content and "let " in content: return "rust"
    if "func " in content and "package " in content: return "go"
    if "function " in content or "const " in content: return "javascript"
    return "unknown"


def analyze_naming_conventions(code_content: str, language: str = None) -> Dict[str, Any]:
    """Scans code for variables, functions, and classes that violate strict naming conventions.

    It enforces the 'Org Policy' styles defined in STYLE_GUIDES. It acts as a strict
    syntax policeman, allowing the Agent to focus on higher-level logic.

    Args:
        code_content (str): The raw source code to analyze.
        language (str, optional): The programming language. If None, it is auto-detected.

    Returns:
        Dict[str, Any]: A dictionary containing a list of 'violations'. Each violation
                        includes the invalid name, the expected style, and the line number.
                        
                        Example:
                        {
                            "violations": [
                                {
                                    "name": "calculateTotal",
                                    "expected": "snake_case",
                                    "line": 10,
                                    "type": "Function Naming"
                                }
                            ]
                        }
    """
    lang = language or _detect_language(code_content)
    parser, lang_obj = _get_parser(lang)
    
    # Fail gracefully if language is unsupported
    if not parser or lang not in QUERIES: 
        return {"violations": []}

    violations = []
    tree = parser.parse(bytes(code_content, "utf8"))
    root = tree.root_node
    
    # 1. Analyze Functions
    _check_node_type(
        root, lang, lang_obj, code_content, 
        query_key="functions", 
        style_key="function", 
        violation_list=violations
    )

    # 2. Analyze Classes/Structs
    _check_node_type(
        root, lang, lang_obj, code_content, 
        query_key="classes", 
        style_key="class", 
        violation_list=violations
    )

    # 3. Analyze Variables
    _check_node_type(
        root, lang, lang_obj, code_content, 
        query_key="variables", 
        style_key="variable", 
        violation_list=violations
    )

    return {"violations": violations}


def _check_node_type(
    root: Any, 
    lang: str, 
    lang_obj: Any, 
    content: str, 
    query_key: str, 
    style_key: str, 
    violation_list: List[Dict]
) -> None:
    """Helper to run a Tree-sitter query and validate names against the style guide.

    Args:
        root (Node): The root node of the syntax tree.
        lang (str): The language identifier.
        lang_obj (Language): The Tree-sitter language object.
        content (str): The raw source code.
        query_key (str): The key in QUERIES to look up (e.g., 'functions').
        style_key (str): The key in STYLE_GUIDES to look up (e.g., 'function').
        violation_list (List[Dict]): The mutable list to append violations to.
    """
    query_str = QUERIES[lang].get(query_key)
    if not query_str: return

    try:
        query = lang_obj.query(query_str)
        captures = query.captures(root)
    except Exception:
        return

    expected_style = STYLE_GUIDES.get(lang, {}).get(style_key, NamingConvention.UNKNOWN)
    regex = NAMING_PATTERNS.get(expected_style)

    for node, _ in captures:
        # Extract the name from the 'name' capture
        name_node = node.child_by_field_name("name")
        if not name_node:
            # Fallback: sometimes the capture IS the name node depending on the query
            name_node = node

        name_text = content[name_node.start_byte:name_node.end_byte]
        
        # 1. Strict Style Check
        if regex and not regex.match(name_text):
            # Special exemption for Go "MixedCaps" vs "camelCase" ambiguity
            # For now, we flag anything that looks like snake_case in Go/JS
            if "_" in name_text and expected_style != NamingConvention.SNAKE_CASE:
                 violation_list.append({
                    "line": name_node.start_point[0] + 1,
                    "name": name_text,
                    "issue": f"{style_key.capitalize()} '{name_text}' should be {expected_style.value}",
                    "suggestion": f"Rename to match {expected_style.value} convention."
                })

        # 2. Non-Descriptive Name Check (Universal)
        # We flag single-letter names unless they are standard loop indices
        if len(name_text) == 1 and name_text not in {'i', 'j', 'k', 'x', 'y', 'z', 'e', '_'}:
            violation_list.append({
                "line": name_node.start_point[0] + 1,
                "name": name_text,
                "issue": f"Variable '{name_text}' is non-descriptive.",
                "suggestion": "Rename to a descriptive noun (e.g., 'index', 'item', 'result')."
            })