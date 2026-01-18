"""
Performance Agent API Routes.

This module defines the specific endpoints for the Performance Optimizer agent,
focused on detecting time complexity issues, memory leaks, and blocking I/O.
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import uuid
from src.schemas.common import ReviewResponse, ReviewMeta, ReviewIssue, Severity, Category, FinalVerdict
from src.utils.file_parser import parse_uploaded_files

performance_bp = Blueprint('performance_agent', __name__)

@performance_bp.route('/scan', methods=['POST'])
def scan():
    """
    Specific Endpoint for Performance Optimizer.
    Scans for Time Complexity, Memory Leaks, and Inefficiency.
    """
    files = parse_uploaded_files(request.files.getlist('files'))
    target_file = files[0].file_path if files else "unknown.py"
    
    # --- MOCK DATA: QUADRATIC COMPLEXITY ---
    issues = [
        ReviewIssue(
            id="perf_n2_loop", 
            file_path=target_file, 
            line_start=22, 
            line_end=26,
            category=Category.PERFORMANCE, 
            severity=Severity.HIGH,
            title="O(N^2) Nested Loop on Large Dataset",
            body="Detected a nested loop iterating over 'users_list' inside 'transactions_list'. If these lists grow, performance will degrade exponentially.",
            suggestion="Convert 'users_list' to a dictionary for O(1) lookups.",
            rationale="Quadratic time complexity is not scalable for production data sets.",
            policy_violated="perf.complexity_limits"
        ),
        ReviewIssue(
            id="perf_io_1", 
            file_path=target_file, 
            line_start=40, 
            line_end=42,
            category=Category.PERFORMANCE, 
            severity=Severity.MEDIUM,
            title="Blocking I/O in Event Loop",
            body="Synchronous file read detected inside an async function.",
            suggestion="Use 'aiofiles' or run in a thread executor.",
            rationale="Blocking I/O pauses the entire event loop, reducing throughput.",
            policy_violated="perf.async_best_practices"
        )
    ]
    
    return jsonify(ReviewResponse(
        review_id=f"perf_{uuid.uuid4().hex[:6]}",
        timestamp=datetime.now().isoformat(),
        meta=ReviewMeta(
            final_verdict=FinalVerdict.REQUEST_CHANGES, 
            quality_score=65, 
            risk_level="MEDIUM",
            total_vulnerabilities=len(issues)
        ),
        summary="Performance logic contains scaling bottlenecks. Optimizing the nested loop is required.",
        praise=["Good use of generator expressions for memory efficiency in data loading."],
        comments=issues
    ).model_dump())