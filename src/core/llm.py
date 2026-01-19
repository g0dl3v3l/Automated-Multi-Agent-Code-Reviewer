"""
Defines the abstract interface for LLM providers.

This allows the application to be model-agnostic. Agents interact with 
the `LLMProvider` interface, not specific SDKs.
"""

"""
Defines the abstract interface for LLM providers.

This allows the application to be model-agnostic. Agents interact with 
the `LLMProvider` interface, not specific SDKs.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Dict
import os
import json
from mistralai import Mistral
from langchain_mistralai import ChatMistralAI

from config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

class LLMProvider(ABC):
    """
    Abstract interface for Language Model Providers.
    Any new provider (OpenAI, Anthropic) MUST implement these methods.
    """
    
    @abstractmethod
    def generate_response(self, system_prompt: str, user_content: str) -> str:
        """Generates a simple text response."""
        pass

    @abstractmethod
    def generate_json_response(self, system_prompt: str, user_content: str) -> dict:
        """Generates a structured JSON response."""
        pass

    @abstractmethod
    def get_chat_model(self, temperature: float = 0.2) -> Any:
        """
        Returns a LangChain-compatible chat model object.
        Required for LangGraph agents.
        """
        pass

class MistralProvider(LLMProvider):
    """
    Concrete implementation for Mistral AI.
    """
    
    def __init__(self):
        # use settings, consistent with rest of app
        self.api_key = settings.MISTRAL_API_KEY
        if not self.api_key:
            logger.error("MISTRAL_API_KEY not found in settings.")
            raise ValueError("MISTRAL_API_KEY is missing.")
            
        self.client = Mistral(api_key=self.api_key)
        self.model = settings.MISTRAL_AGENT_MODEL # Optimized for code generation

    def generate_response(self, system_prompt: str, user_content: str) -> str:
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
            
            response = self.client.chat.complete(
                model=self.model,
                messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Mistral text generation failed: {e}")
            raise e

    def generate_json_response(self, system_prompt: str, user_content: str) -> dict:
        try:
            json_system_prompt = f"{system_prompt}\n\nIMPORTANT: Output ONLY valid JSON."
            
            messages = [
                {"role": "system", "content": json_system_prompt},
                {"role": "user", "content": user_content}
            ]
            
            response = self.client.chat.complete(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"} 
            )
            
            raw_content = response.choices[0].message.content
            return json.loads(raw_content)
            
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from LLM response.")
            raise ValueError("LLM did not return valid JSON.")
        except Exception as e:
            logger.error(f"Mistral JSON generation failed: {e}")
            raise e

    def get_chat_model(self, temperature: float = 0.2) -> ChatMistralAI:
        """
        Returns the LangChain wrapper for Mistral.
        Used by the ReAct Graph Agents.
        """
        return ChatMistralAI(
            api_key=self.api_key,
            model=self.model, # 'large' is better for reasoning/tools than 'codestral'
            temperature=temperature
        )

# Factory function to get the configured provider
def get_llm_client() -> LLMProvider:
    """Returns the singleton instance of the configured LLM Provider."""
    # In the future, you can add logic here: if settings.PROVIDER == "OPENAI": return OpenAIProvider()
    return MistralProvider()