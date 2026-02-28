"""
LLM Adapter - Unified interface for multiple LLM providers
Supports OpenAI (GPT-4) and Anthropic (Claude)
"""
import os
import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import httpx
from datetime import datetime


class LLMAdapter(ABC):
    """Abstract base class for LLM providers"""

    def __init__(self, api_key: str, model: str, temperature: float = 0.3, max_tokens: int = 2000):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """Generate response from LLM"""
        pass

    @abstractmethod
    async def validate_connection(self) -> bool:
        """Test connection to LLM provider"""
        pass


class OpenAIAdapter(LLMAdapter):
    """OpenAI GPT-4 adapter"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4-turbo",
        temperature: float = 0.3,
        max_tokens: int = 2000
    ):
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
        super().__init__(api_key, model, temperature, max_tokens)
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    async def generate(self, prompt: str) -> str:
        """Generate response using OpenAI API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a professional trading AI. Always respond with valid JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )

                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"].strip()
                else:
                    raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")

        except Exception as e:
            raise Exception(f"OpenAI generation failed: {str(e)}")

    async def validate_connection(self) -> bool:
        """Test OpenAI connection"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=headers
                )

                return response.status_code == 200

        except Exception:
            return False


class ClaudeAdapter(LLMAdapter):
    """Anthropic Claude adapter"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-opus-20240229",
        temperature: float = 0.3,
        max_tokens: int = 2000
    ):
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        super().__init__(api_key, model, temperature, max_tokens)
        self.base_url = "https://api.anthropic.com/v1"

    async def generate(self, prompt: str) -> str:
        """Generate response using Claude API"""
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "system": "You are a professional trading AI. Always respond with valid JSON only.",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=headers,
                    json=payload
                )

                if response.status_code == 200:
                    data = response.json()
                    return data["content"][0]["text"].strip()
                else:
                    raise Exception(f"Claude API error: {response.status_code} - {response.text}")

        except Exception as e:
            raise Exception(f"Claude generation failed: {str(e)}")

    async def validate_connection(self) -> bool:
        """Test Claude connection"""
        try:
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }

            payload = {
                "model": self.model,
                "max_tokens": 10,
                "messages": [{"role": "user", "content": "test"}]
            }

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=headers,
                    json=payload
                )

                return response.status_code == 200

        except Exception:
            return False


class GroqAdapter(OpenAIAdapter):
    """Groq API adapter (OpenAI compatible)"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "llama-3.1-8b-instant",
        temperature: float = 0.3,
        max_tokens: int = 2000
    ):
        api_key = api_key or os.getenv("GROQ_API_KEY")
        if not api_key:
            # Fallback to OpenAI key if starts with gsk_
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key and openai_key.startswith("gsk_"):
                api_key = openai_key
            else:
                raise ValueError("GROQ_API_KEY not set")
        
        super().__init__(api_key, model, temperature, max_tokens)
        self.base_url = "https://api.groq.com/openai/v1"


class LocalLLMAdapter(OpenAIAdapter):
    """Local LLM adapter (OpenAI compatible, e.g. Ollama, LM Studio)"""

    def __init__(
        self,
        api_key: str = "not-needed",
        model: str = "local-model",
        temperature: float = 0.3,
        max_tokens: int = 2000,
        base_url: str = "http://localhost:1234/v1"
    ):
        super().__init__(api_key, model, temperature, max_tokens)
        self.base_url = os.getenv("LOCAL_LLM_BASE_URL", base_url)


class MockLLMAdapter(LLMAdapter):
    """Mock adapter for testing (always returns valid decision JSON)"""

    def __init__(self):
        super().__init__("mock", "mock-model", 0.3, 2000)

    async def generate(self, prompt: str) -> str:
        """Return mock trading decision"""
        mock_decision = {
            "decision_type": "ENTRY",
            "confidence": 0.75,
            "rationale": "Mock decision for testing - price broke above EMA20 with volume",
            "market_regime": "Trending Up",
            "timeframe_analysis": {
                "15m": "Entry signal on pullback",
                "1h": "Strong uptrend",
                "4h": "Higher low pattern"
            },
            "order_spec": {
                "symbol": "ETHUSDT",
                "side": "BUY",
                "quantity": 10.0,
                "entry_price": 2500.0,
                "stop_loss_price": 2450.0,
                "take_profit_prices": [2550.0, 2600.0],
                "leverage": 5.0
            },
            "checklist_results": [
                {"name": "Position size check", "passed": True, "reason": "Within limits"},
                {"name": "Risk ratio check", "passed": True, "reason": "2.5:1 ratio acceptable"}
            ],
            "risk_assessment": {
                "risk_reward_ratio": 2.5,
                "position_pct": 3.5,
                "daily_loss_pct": 0.8
            }
        }
        return json.dumps(mock_decision)

    async def validate_connection(self) -> bool:
        """Mock always connected"""
        return True


def get_llm_adapter(
    provider: str = "openai",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 2000
) -> LLMAdapter:
    """Factory function to get LLM adapter"""

    provider = provider.lower()

    if provider == "openai":
        if api_key and api_key.startswith("gsk_"):
            # Auto-correct model name if it's an OpenAI default
            effective_model = model if model and "gpt" not in model.lower() else "llama-3.1-8b-instant"
            return GroqAdapter(api_key, effective_model, temperature, max_tokens)
        return OpenAIAdapter(api_key, model or "gpt-4-turbo", temperature, max_tokens)
    elif provider == "claude" or provider == "anthropic":
        return ClaudeAdapter(api_key, model or "claude-3-opus-20240229", temperature, max_tokens)
    elif provider == "groq":
        return GroqAdapter(api_key, model or "llama-3.1-8b-instant", temperature, max_tokens)
    elif provider == "local":
        return LocalLLMAdapter(api_key or "not-needed", model or "local-model", temperature, max_tokens)
    elif provider == "mock":
        return MockLLMAdapter()
    else:
        # Auto-detect Groq key
        if api_key and api_key.startswith("gsk_"):
            return GroqAdapter(api_key, model or "mixtral-8x7b-32768", temperature, max_tokens)
        raise ValueError(f"Unknown LLM provider: {provider}")
