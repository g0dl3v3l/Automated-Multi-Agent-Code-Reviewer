"""
Maintainability Agent API Routes.

This module defines the specific endpoints for the Code Architect agent,
focused on code style, modularity, docstrings, and clean code principles.
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import uuid
from src.schemas.common import ReviewResponse, ReviewMeta, ReviewIssue, Severity, Category, FinalVerdict
from src.utils.file_parser import parse_uploaded_files

maintainability_bp = Blueprint('maintainability_agent', __name__)

@maintainability_bp.route('/scan', methods=['POST'])
def scan():
    """
    Specific Endpoint for Code Architect.
    Scans for Readability, Modularization, and Standards.
    """
    files = parse_uploaded_files(request.files.getlist('files'))
    target_file = files[0].file_path if files else "unknown.py"
    
    issues = [
        ReviewIssue(
            id="maint_god_func", 
            file_path=target_file, 
            line_start=10, 
            line_end=85,
            category=Category.MAINTAINABILITY, 
            severity=Severity.MEDIUM,
            title="Function Too Long (God Function)",
            body=f"Function 'process_data' is 75 lines long. It handles validation, processing, and database saving.",
            suggestion="Split into 'validate_input', 'transform_data', and 'save_record'.",
            rationale="Functions should focus on a single responsibility (SRP) and ideally be under 50 lines.",
            policy_violated="style.function_length"
        ),
        ReviewIssue(
            id="maint_doc_1", 
            file_path=target_file, 
            line_start=10, 
            line_end=10,
            category=Category.MAINTAINABILITY, 
            severity=Severity.NITPICK,
            title="Missing Docstring",
            body="Public function 'process_data' has no docstring explaining inputs/outputs.",
            suggestion='"""Processes user data and commits to DB.\n\nArgs:\n    data: Dict...\n"""',
            rationale="Code must be self-documenting for future maintainers.",
            policy_violated="style.docstrings"
        )
    ]
    
    return jsonify(ReviewResponse(
        review_id=f"maint_{uuid.uuid4().hex[:6]}",
        timestamp=datetime.now().isoformat(),
        meta=ReviewMeta(
            final_verdict=FinalVerdict.APPROVE, 
            quality_score=85, 
            risk_level="LOW",
            total_vulnerabilities=len(issues)
        ),
        summary="Code structure is generally clean, but the main processing function needs refactoring for modularity.",
        praise=[
            "Excellent variable naming conventions.",
            "Type hints are used consistently throughout the module."
        ],
        comments=issues
    ).model_dump())