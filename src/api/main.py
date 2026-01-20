"""
Entry point for the Flask Backend API.
Updated to allow CORS for the React Frontend.
"""

from dotenv import load_dotenv
import os
load_dotenv()
print(f"DEBUG: Tracing Enabled? {os.getenv('LANGSMITH_TRACING')}")
print(f"DEBUG: API Key Present? {bool(os.getenv('LANGSMITH_API_KEY'))}")
from flask import Flask
from flask_cors import CORS
from config.settings import settings
from src.utils.logger import get_logger

# 1. Import Core System Routes
from src.api.routes_core import core_bp

# 2. Import Agent Specific Routes (Modular)
from src.agents.security.routes import security_bp
from src.agents.performance.routes import performance_bp
from src.agents.maintainability.routes import maintainability_bp
from src.core.registry import AgentRegistry
from src.agents.stub_agent import StubAgent
from src.core.llm import get_llm_client
from src.agents.security.agent import SecurityAgent
from src.agents.performance.agent import PerformanceAgent
logger = get_logger(__name__)

def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    llm_provider = get_llm_client()

    # 2. Inject Provider into Agent
    sec_agent = SecurityAgent(
        name="Security Hawk", 
        slug="security-agent", 
        llm_provider=llm_provider # <--- INJECTED HERE
    )

    perf_agent = PerformanceAgent(           # <--- 2. INITIALIZE AGENT B
        name="The Architect",
        slug="performance-agent",
        llm_provider=llm_provider
    )
    stub = StubAgent(name="System Test Agent", slug="stub-agent", llm_provider=llm_provider)
    #AgentRegistry.register(stub)
    AgentRegistry.register(sec_agent)
    AgentRegistry.register(perf_agent)
    # --- REGISTER BLUEPRINTS ---
    
    # Core: /api/review/full, /api/config
    app.register_blueprint(core_bp, url_prefix='/api')
    
    # Agents: /api/agents/security/scan
    app.register_blueprint(security_bp, url_prefix='/api/agents/security')
    
    # Agents: /api/agents/performance/scan
    app.register_blueprint(performance_bp, url_prefix='/api/agents/performance')
    
    # Agents: /api/agents/maintainability/scan
    app.register_blueprint(maintainability_bp, url_prefix='/api/agents/maintainability')
    
    return app

if __name__ == "__main__":
    app = create_app()
    logger.info(f"Starting API on port {settings.API_PORT}")
    app.run(host=settings.API_HOST, port=settings.API_PORT, debug=settings.DEBUG)