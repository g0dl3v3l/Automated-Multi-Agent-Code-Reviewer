"""
Defines the abstract base class for all analysis agents.

This module provides the `BaseAgent` interface, which enforces a consistent 
structure (inputs, outputs, execution method) for all specialized agents 
(Security, Performance, Maintainability) in the system.
"""

"""Core System Interfaces.

Defines the immutable contracts for Agents and core components.
"""
from abc import ABC, abstractmethod
from typing import List, Any
from src.core.llm import LLMProvider
from src.schemas.common import AgentPayload, ReviewIssue
from src.utils.logger import get_logger

logger = get_logger(__name__)

class BaseAgent(ABC):
    """
    The Contract: All agents (Security, Performance, etc.) MUST inherit from this.
    """

    def __init__(self, name: str, slug: str, llm_provider: LLMProvider):
        """
        Initializes the agent.

        Args:
            name (str): Human readable name (e.g., "Security Hawk")
            slug (str): Unique machine key (e.g., "security-agent")
            llm_provider (LLMProvider): The AI engine to use.
        """
        self.name = name
        self.slug = slug  # <--- THIS WAS MISSING
        self.llm = llm_provider
        logger.info(f"Initialized Agent: {self.name} [{self.slug}]")

    @abstractmethod
    def run(self, payload: AgentPayload) -> List[ReviewIssue]:
        """
        The Main Event.
        Executes the agent's logic pipeline (Tool usage + LLM analysis).
        
        Args:
            payload (AgentPayload): The input data containing files and context.

        Returns:
            List[ReviewIssue]: The identified issues.
        """
        pass

    @abstractmethod
    def get_tools(self) -> List[Any]:
        """
        Retrieves the specific Python tools available to this agent.
        """
        pass