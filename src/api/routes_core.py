"""
Core Orchestration APIs: Health, Config, and Full Scan.
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import uuid
from src.schemas.common import ReviewResponse, ReviewMeta, ReviewIssue, Severity, Category, FinalVerdict
from src.utils.logger import get_logger
from src.utils.file_parser import parse_uploaded_files
from src.core.controller import ReviewController


logger = get_logger(__name__)
core_bp = Blueprint('core', __name__)
controller = ReviewController()
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
async def full_scan():
    """The Main Orchestrator Endpoint.

    Accepts file uploads, triggers the `ReviewController` to run a full scan
    across all registered agents, and returns the aggregated results.

    Args:
        files (Multipart): A list of files uploaded via form-data.

    Returns:
        Response: A JSON representation of the `ReviewResponse` object.
    """

    if 'files' not in request.files:
        return jsonify({"error": "No files uploaded"}), 400

    files = parse_uploaded_files(request.files.getlist('files'))
    #main_file = files[0].file_path if files else "unknown.py"
    review_id = f"rev_{uuid.uuid4().hex[:8]}"

    # Delegate to Controller
    response = await controller.run_full_scan(files, review_id)

    return jsonify(response.model_dump())
    