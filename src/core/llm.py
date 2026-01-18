"""
Defines the abstract interface for LLM providers.

This allows the application to be model-agnostic. Agents interact with 
the `LLMProvider` interface, not specific SDKs.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Dict
import os
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage

from config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

class LLMProvider(ABC):
    """
    Abstract interface for Language Model Providers.
    """
    
    @abstractmethod
    def generate_response(self, system_prompt: str, user_content: str) -> str:
        """
        Generates a text response from the LLM.
        """
        pass

class MistralProvider(LLMProvider):
    """
    Concrete implementation for Mistral AI.
    """
    
    def __init__(self):
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            logger.error("MISTRAL_API_KEY not found in environment variables.")
            raise ValueError("MISTRAL_API_KEY is missing.")
            
        self.client = MistralClient(api_key=api_key)
        self.model = "codestral-latest" # Using the specific code model

    def generate_response(self, system_prompt: str, user_content: str) -> str:
        try:
            messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=user_content)
            ]
            
            response = self.client.chat(
                model=self.model,
                messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Mistral generation failed: {e}")
            raise e

# Factory function to get the configured provider
def get_llm_client() -> LLMProvider:
    # Future: logic to switch providers based on settings.ENV
    return MistralProvider()