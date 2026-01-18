"""
Agent-Specific APIs: Direct access to individual experts.
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import uuid
from src.schemas.common import ReviewResponse, ReviewMeta, ReviewIssue, Severity, Category, FinalVerdict
from src.utils.file_parser import parse_uploaded_files

agents_bp = Blueprint('agents', __name__)

@agents_bp.route('/security', methods=['POST'])
def scan_security():
    """Mock endpoint for the Security Hawk agent."""
    files = parse_uploaded_files(request.files.getlist('files'))
    target_file = files[0].file_path if files else "main.py"
    
    issues = [
        ReviewIssue(
            id="sec_sql", file_path=target_file, line_start=15, line_end=15,
            category=Category.SECURITY, severity=Severity.CRITICAL,
            title="SQL Injection Vulnerability",
            body="Raw SQL query concatenation detected.",
            suggestion="cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))",
            rationale="User input is not sanitized.",
            policy_violated="sec.injection_prevention" # <--- FIXED
        )
    ]
    
    return jsonify(ReviewResponse(
        review_id=f"sec_{uuid.uuid4().hex[:6]}",
        timestamp=datetime.now().isoformat(),
        meta=ReviewMeta(
            final_verdict=FinalVerdict.REJECT, 
            quality_score=40, 
            risk_level="CRITICAL",
            total_vulnerabilities=len(issues)
        ),
        summary="Security scan failed. Critical injection vulnerability found.",
        praise=[],
        comments=issues
    ).model_dump())

@agents_bp.route('/performance', methods=['POST'])
def scan_performance():
    return jsonify({"message": "Performance Agent Mock Data Placeholder"})

@agents_bp.route('/maintainability', methods=['POST'])
def scan_maintainability():
    return jsonify({"message": "Maintainability Agent Mock Data Placeholder"})