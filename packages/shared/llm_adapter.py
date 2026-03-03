"""
LLM Adapter - Unified interface for multiple LLM providers
Supports OpenAI (GPT-4) and Anthropic (Claude)
"""
import os
import json
import asyncio
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
            "market_regime": "trend",
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


class GeminiAdapter(LLMAdapter):
    """Google Gemini adapter using native Generative Language API"""
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.5-flash",
        temperature: float = 0.3,
        max_tokens: int = 2000,
        base_url: Optional[str] = None
    ):
        api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set")
        super().__init__(api_key, model, temperature, max_tokens)
        # Ensure model name starts with 'models/' for Gemini API v1beta
        if not model.startswith("models/"):
            model = f"models/{model}"
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def generate(self, prompt: str) -> str:
        """Generate response using Google Gemini API (native format, not OpenAI)"""
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ],
                    "role": "user"
                }
            ],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
            }
        }

        max_attempts = 3
        async with httpx.AsyncClient(timeout=60.0) as client:
            for attempt in range(1, max_attempts + 1):
                try:
                    response = await client.post(
                        f"{self.base_url}/{self.model}:generateContent",
                        params={"key": self.api_key},
                        json=payload
                    )

                    if response.status_code >= 500 and attempt < max_attempts:
                        await asyncio.sleep(0.5 * (2 ** (attempt - 1)))
                        continue

                    # Never fall back to Mock in live flows: quota errors must be explicit
                    if response.status_code == 429:
                        raise RuntimeError("Gemini API quota exceeded (429)")

                    if response.status_code != 200:
                        snippet = (response.text or "")[:300]
                        raise RuntimeError(
                            f"Gemini API error: {response.status_code} - {snippet}"
                        )

                    result = response.json()
                    # Extract text from Gemini API response format
                    if "candidates" in result and len(result["candidates"]) > 0:
                        candidate = result["candidates"][0]
                        if "content" in candidate and "parts" in candidate["content"]:
                            return candidate["content"]["parts"][0]["text"]
                    raise RuntimeError("Invalid Gemini response format")
                    
                except (httpx.TimeoutException, httpx.TransportError) as e:
                    if attempt < max_attempts:
                        await asyncio.sleep(0.5 * (2 ** (attempt - 1)))
                        continue
                    raise RuntimeError(f"Gemini request failed after retries: {e}") from e
                except Exception as e:
                    raise RuntimeError(f"Gemini generation failed: {e}") from e

    async def validate_connection(self) -> bool:
        """Test Gemini connection - verify API key works"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # List models endpoint to verify API key
                response = await client.get(
                    f"{self.base_url}/models",
                    params={"key": self.api_key}
                )
                return response.status_code == 200
        except Exception:
            return False


def get_llm_adapter(
    provider: str = "openai",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 2000,
    custom_endpoint: Optional[str] = None
) -> LLMAdapter:
    """Factory function to get LLM adapter with custom user settings"""

    provider = provider.lower()

    if provider == "openai":
        return OpenAIAdapter(api_key, model or "gpt-4o-mini", temperature, max_tokens)
    elif provider == "claude" or provider == "anthropic":
        return ClaudeAdapter(api_key, model or "claude-3.5-sonnet", temperature, max_tokens)
    elif provider == "gemini" or provider == "google":
        return GeminiAdapter(api_key, model or "gemini-2.0-flash", temperature, max_tokens, custom_endpoint)
    elif provider == "groq":
        return GroqAdapter(api_key, model or "llama3-70b-8192", temperature, max_tokens)
    elif provider == "local" or provider == "manual":
        return LocalLLMAdapter(api_key or "not-needed", model or "local-model", temperature, max_tokens, custom_endpoint or "http://localhost:1234/v1")
    elif provider == "mock":
        return MockLLMAdapter()
    else:
        # Fallback to OpenAI-compatible for any other provider if custom_endpoint is given
        if custom_endpoint:
            return LocalLLMAdapter(api_key or "not-needed", model or "custom-model", temperature, max_tokens, custom_endpoint)
        raise ValueError(f"Unknown LLM provider: {provider}")
