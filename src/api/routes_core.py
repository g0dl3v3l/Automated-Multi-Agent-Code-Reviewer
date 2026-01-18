"""
Core Orchestration APIs: Health, Config, and Full Scan.
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import uuid
from src.schemas.common import ReviewResponse, ReviewMeta, ReviewIssue, Severity, Category, FinalVerdict
from src.utils.logger import get_logger
from src.utils.file_parser import parse_uploaded_files

logger = get_logger(__name__)
core_bp = Blueprint('core', __name__)

@core_bp.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "version": "0.6.0", "timestamp": datetime.now().isoformat()})

@core_bp.route('/config', methods=['GET'])
def get_config():
    """Returns frontend configuration options."""
    return jsonify({
        "max_file_size_mb": 200,
        "allowed_extensions": [".py", ".js", ".ts", ".java", ".go"],
        "risk_levels": ["Strict", "Standard", "Loose"],
        "active_agents": ["Security Hawk", "Performance Optimizer", "Code Architect"]
    })

@core_bp.route('/review/full', methods=['POST'])
def full_scan():
    """
    The Main Orchestrator. 
    Currently returns RICH MOCK DATA for all agents.
    """
    if 'files' not in request.files:
        return jsonify({"error": "No files uploaded"}), 400

    files = parse_uploaded_files(request.files.getlist('files'))
    main_file = files[0].file_path if files else "unknown.py"
    
    # --- MOCK DATA GENERATION ---
    issues = [
        # Security Issue
        ReviewIssue(
            id="sec_1", file_path=main_file, line_start=10, line_end=10,
            category=Category.SECURITY, severity=Severity.HIGH,
            title="Hardcoded API Key",
            body="An API key was detected in plain text. This poses a significant security risk.",
            suggestion="os.getenv('API_KEY')",
            rationale="Secrets should never be committed to source control.",
            policy_violated="sec.secrets_management"
        ),
        # Performance Issue
        ReviewIssue(
            id="perf_1", file_path=main_file, line_start=25, line_end=28,
            category=Category.PERFORMANCE, severity=Severity.MEDIUM,
            title="O(N^2) Nested Loop",
            body="Detected a nested loop iterating over the same large dataset.",
            suggestion="Use a hash map lookup instead.",
            rationale="Quadratic time complexity will scale poorly.",
            policy_violated="perf.complexity_limits" # <--- FIXED
        ),
        # Maintainability Issue
        ReviewIssue(
            id="maint_1", file_path=main_file, line_start=45, line_end=45,
            category=Category.MAINTAINABILITY, severity=Severity.NITPICK,
            title="Missing Docstring",
            body="Public function lacks documentation.",
            suggestion='"""\nSummary of function.\n"""',
            rationale="Documentation ensures long-term maintainability.",
            policy_violated="style.docstrings" # <--- FIXED
        )
    ]

    response = ReviewResponse(
        review_id=f"rev_{uuid.uuid4().hex[:8]}",
        timestamp=datetime.now().isoformat(),
        meta=ReviewMeta(
            final_verdict=FinalVerdict.REQUEST_CHANGES,
            quality_score=68,
            risk_level="HIGH",
            total_vulnerabilities=len(issues),
            scan_duration_ms=1250.5
        ),
        summary="The submission contains critical security vulnerabilities and several performance bottlenecks. Immediate refactoring of the authentication layer is required.",
        praise=[
            "Good modular separation of database logic.",
            "Consistent naming conventions used throughout."
        ],
        comments=issues
    )
    
    return jsonify(response.model_dump())