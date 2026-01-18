"""
Agent Registry.
Acts as the central directory for all active analysis agents.
"""
from typing import Dict, List
from src.core.interfaces import BaseAgent
from src.utils.logger import get_logger

logger = get_logger(__name__)

class AgentRegistry:
    """
    Singleton-style registry to manage active agents.
    """
    _agents: Dict[str, BaseAgent] = {}

    @classmethod
    def register(cls, agent: BaseAgent):
        """Adds an agent to the system."""
        if agent.slug in cls._agents:
            logger.warning(f"Overwriting existing agent: {agent.slug}")
        
        cls._agents[agent.slug] = agent
        logger.info(f"Registered Agent: {agent.name}")

    @classmethod
    def get_all(cls) -> List[BaseAgent]:
        """Returns list of all registered agents."""
        return list(cls._agents.values())

    @classmethod
    def get(cls, slug: str) -> BaseAgent:
        """Retrieves a specific agent by slug."""
        return cls._agents.get(slug)