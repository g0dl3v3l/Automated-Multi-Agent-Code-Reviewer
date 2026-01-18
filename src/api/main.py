"""
Entry point for the Flask Backend API.
Updated to allow CORS for the React Frontend.
"""

from flask import Flask
from flask_cors import CORS
from config.settings import settings
from src.utils.logger import get_logger

# Import the new blueprints
from src.api.routes_core import core_bp
from src.api.routes_agents import agents_bp

logger = get_logger(__name__)

def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Register Blueprints
    app.register_blueprint(core_bp, url_prefix='/api')        # /api/review/full, /api/config
    app.register_blueprint(agents_bp, url_prefix='/api/agents') # /api/agents/security
    
    return app

if __name__ == "__main__":
    app = create_app()
    logger.info(f"Starting API on port {settings.API_PORT}")
    app.run(host=settings.API_HOST, port=settings.API_PORT, debug=settings.DEBUG)