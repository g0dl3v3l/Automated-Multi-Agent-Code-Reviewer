"""
Security Agent API Routes.

This module defines the specific endpoints for the Security Hawk agent,
responsible for detecting vulnerabilities, injections, and secret leaks.
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import uuid
from src.schemas.common import ReviewResponse, ReviewMeta, ReviewIssue, Severity, Category, FinalVerdict
from src.utils.file_parser import parse_uploaded_files

# Define Blueprint
security_bp = Blueprint('security_agent', __name__)

@security_bp.route('/scan', methods=['POST'])
def scan():
    """
    Specific Endpoint for Security Hawk.
    Scans for Injection, Auth flaws, and Data exposure.
    """
    files = parse_uploaded_files(request.files.getlist('files'))
    target_file = files[0].file_path if files else "unknown.py"
    
    # --- MOCK DATA: SQL INJECTION ---
    issues = [
        ReviewIssue(
            id="sec_sql_1", 
            file_path=target_file, 
            line_start=15, 
            line_end=15,
            category=Category.SECURITY, 
            severity=Severity.CRITICAL,
            title="SQL Injection Vulnerability",
            body="Detected raw string concatenation in SQL query construction. This allows attackers to manipulate the query.",
            suggestion="Use parameterized queries: cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))",
            rationale="User input is not sanitized before being sent to the database.",
            policy_violated="sec.injection_prevention"
        ),
        ReviewIssue(
            id="sec_hardcoded_1", 
            file_path=target_file, 
            line_start=4, 
            line_end=4,
            category=Category.SECURITY, 
            severity=Severity.HIGH,
            title="Hardcoded AWS Credential",
            body="Found a potential AWS Access Key ID in plain text.",
            suggestion="Use environment variables or a secrets manager.",
            rationale="Secrets in source code can be leaked via version control.",
            policy_violated="sec.secrets_management"
        )
    ]
    
    return jsonify(ReviewResponse(
        review_id=f"sec_{uuid.uuid4().hex[:6]}",
        timestamp=datetime.now().isoformat(),
        meta=ReviewMeta(
            final_verdict=FinalVerdict.REJECT, 
            quality_score=35, 
            risk_level="CRITICAL",
            total_vulnerabilities=len(issues)
        ),
        summary="Security scan failed. Critical injection vulnerability and hardcoded secrets found.",
        praise=[],
        comments=issues
    ).model_dump())