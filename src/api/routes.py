"""
Defines the API endpoints for the Code Reviewer service.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import uuid

from src.utils.logger import get_logger
from src.utils.file_parser import parse_uploaded_files
from src.schemas.common import ReviewResponse, ReviewMeta, FinalVerdict, ReviewIssue, Severity, Category

logger = get_logger(__name__)
api_bp = Blueprint('api', __name__)

@api_bp.route('/health', methods=['GET'])
def health_check():
    """
    Simple health check endpoint to verify the API is running.
    """
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@api_bp.route('/review', methods=['POST'])
def review_code():
    """
    Main endpoint to trigger a code review.
    
    Accepts multipart/form-data with file uploads.
    Currently returns a MOCKED response for integration testing.
    """
    logger.info("Received review request")
    
    if 'files' not in request.files:
        return jsonify({"error": "No files provided"}), 400
        
    files = request.files.getlist('files')
    source_files = parse_uploaded_files(files)
    
    logger.info(f"Processing {len(source_files)} files...")

    # --- MOCK RESPONSE (Simulating the Judge's output) ---
    mock_response = ReviewResponse(
        review_id=f"rev_{uuid.uuid4().hex[:8]}",
        timestamp=datetime.now().isoformat(),
        meta=ReviewMeta(
            final_verdict=FinalVerdict.REQUEST_CHANGES,
            quality_score=75,
            risk_level="HIGH"
        ),
        summary="This is a MOCK response to test the UI connection. The system received your files successfully.",
        praise=[
            "Great job connecting the frontend to the backend!",
            "File upload mechanism is working correctly."
        ],
        comments=[
            ReviewIssue(
                id="c_1",
                file_path=source_files[0].file_path if source_files else "unknown.py",
                line_start=10,
                line_end=12,
                category=Category.SECURITY,
                severity=Severity.HIGH,
                title="Mock Security Issue",
                body="This is a test issue to verify the UI renders cards correctly.",
                suggestion="Fix the mock issue.",
                rationale="We need to verify the pipeline.",
                references=["https://example.com"],
                policy_violated="security.banned_patterns: [mock_violation]"
            )
        ]
    )
    
    return jsonify(mock_response.model_dump())