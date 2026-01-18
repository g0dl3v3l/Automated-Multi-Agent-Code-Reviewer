"""
Defines the abstract base class for all analysis agents.

This module provides the `BaseAgent` interface, which enforces a consistent 
structure (inputs, outputs, execution method) for all specialized agents 
(Security, Performance, Maintainability) in the system.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Dict

from src.core.llm import LLMProvider
from src.schemas.common import AgentPayload, ReviewIssue
from src.utils.logger import get_logger

logger = get_logger(__name__)

class BaseAgent(ABC):
    """
    Abstract Base Class that defines the contract for all specialized agents.
    
    Attributes:
        name (str): The human-readable name of the agent.
        llm (LLMProvider): The abstract LLM interface.
    """

    def __init__(self, name: str, llm_provider: LLMProvider):
        """
        Initializes the agent with a name and an LLM provider.

        Args:
            name (str): The human-readable name of the agent.
            llm_provider (LLMProvider): Configured LLM abstraction.
        """
        self.name = name
        self.llm = llm_provider
        logger.info(f"Initialized agent: {self.name}")

    @abstractmethod
    def run(self, payload: AgentPayload) -> List[ReviewIssue]:
        """
        Executes the agent's main logic pipeline.

        Args:
            payload (AgentPayload): The input data containing filtered files 
                and context.

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