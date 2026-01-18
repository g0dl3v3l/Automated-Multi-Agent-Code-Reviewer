"""
Entry point for the Flask Backend API.
Updated to allow CORS for the React Frontend.
"""

from flask import Flask
from flask_cors import CORS  # <--- NEW IMPORT
from config.settings import settings
from src.utils.logger import get_logger
from src.api.routes import api_bp

logger = get_logger(__name__)

def create_app() -> Flask:
    """
    Factory function to create and configure the Flask application.
    """
    app = Flask(__name__)
    
    # Enable CORS for all routes (Allow React to talk to Flask)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Register Routes
    app.register_blueprint(api_bp, url_prefix='/api')
    
    return app

if __name__ == "__main__":
    app = create_app()
    logger.info(f"Starting API on port {settings.API_PORT}")
    app.run(host=settings.API_HOST, port=settings.API_PORT, debug=settings.DEBUG)