"""
Dynamic LLM Router with multiple provider support.

Supports:
- Anthropic (Claude)
- OpenAI (GPT-4)
- Google (Gemini)
- OpenRouter (multiple models)

Usage:
    from app.core.llm_router import llm_router
    
    # Use default provider
    result = await llm_router.call(prompt="Hello", json_output=True)
    
    # Override provider for specific call
    result = await llm_router.call(prompt="Hello", provider="google")
    
    # Override model for specific call
    result = await llm_router.call(prompt="Hello", model="gpt-4o-mini")
"""

from abc import ABC, abstractmethod
from typing import Optional
import json

from app.config import get_settings

settings = get_settings()


def _clean_json_response(text: str) -> str:
    """Clean LLM response to extract valid JSON.

    Handles:
    - Markdown code blocks (```json ... ```)
    - DeepSeek R1 thinking tags (<think>...</think>)
    - Prefixed text before JSON object/array
    - Trailing commas before ] or } (common LLM mistake)
    - Unterminated strings (try to close them)
    """
    import re

    text = text.strip()

    # Strip DeepSeek R1 <think>...</think> tags (complete or truncated)
    # First try complete tags
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    # Then strip truncated thinking (no closing tag - model ran out of tokens)
    if "<think>" in text:
        text = re.sub(r"<think>.*", "", text, flags=re.DOTALL).strip()

    # Strip markdown code blocks
    if "```" in text:
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()

    # If still not starting with { or [, find the first JSON object/array
    if text and text[0] not in ("{", "["):
        for i, ch in enumerate(text):
            if ch in ("{", "["):
                text = text[i:]
                break

    # Remove trailing commas before ] or } (invalid JSON but common LLM output)
    text = re.sub(r",\s*]", "]", text)
    text = re.sub(r",\s*}", "}", text)

    # Fix unterminated strings: count unescaped quotes
    # If odd, the last string is unterminated - try to close it
    quote_positions = []
    i = 0
    while i < len(text):
        if text[i] == '"' and (i == 0 or text[i - 1] != "\\"):
            quote_positions.append(i)
        i += 1

    if len(quote_positions) % 2 == 1:
        # Odd quotes = unterminated string
        # Find position to insert closing quote (before next structural char)
        last_quote = quote_positions[-1]
        for j in range(last_quote + 1, len(text)):
            if text[j] in (",", "}", "]", "\n"):
                text = text[:j] + '"' + text[j:]
                break
        else:
            # No structural char found, append quote at end
            text = text.rstrip() + '"'
            # Also try to close brackets
            if text.startswith("[") and not text.rstrip().endswith("]"):
                text = text.rstrip() + "]"
            elif text.startswith("{") and not text.rstrip().endswith("}"):
                text = text.rstrip() + "}"

    return text


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    name: str = "base"
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: str = "",
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        """Generate a response from the LLM."""
        pass
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is configured and available."""
        pass
    
    @property
    @abstractmethod
    def default_model(self) -> str:
        """Get the default model for this provider."""
        pass


class AnthropicProvider(LLMProvider):
    """Anthropic (Claude) provider."""
    
    name = "anthropic"
    
    def __init__(self):
        self._client = None
    
    @property
    def client(self):
        if self._client is None:
            from anthropic import Anthropic
            self._client = Anthropic(api_key=settings.anthropic_api_key)
        return self._client
    
    @property
    def is_available(self) -> bool:
        return bool(settings.anthropic_api_key)
    
    @property
    def default_model(self) -> str:
        return settings.anthropic_model or "claude-sonnet-4-20250514"
    
    async def generate(
        self,
        prompt: str,
        system: str = "",
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        response = self.client.messages.create(
            model=model or self.default_model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text


class OpenAIProvider(LLMProvider):
    """OpenAI provider."""
    
    name = "openai"
    
    def __init__(self):
        self._client = None
    
    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=settings.openai_api_key)
        return self._client
    
    @property
    def is_available(self) -> bool:
        return bool(settings.openai_api_key)
    
    @property
    def default_model(self) -> str:
        return settings.openai_model or "gpt-4o"
    
    async def generate(
        self,
        prompt: str,
        system: str = "",
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        response = self.client.chat.completions.create(
            model=model or self.default_model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content


class GoogleProvider(LLMProvider):
    """Google Gemini provider."""
    
    name = "google"
    
    def __init__(self):
        self._client = None
    
    @property
    def client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=settings.google_api_key)
        return self._client
    
    @property
    def is_available(self) -> bool:
        return bool(settings.google_api_key)
    
    @property
    def default_model(self) -> str:
        return settings.google_model or "gemini-2.0-flash"
    
    async def generate(
        self,
        prompt: str,
        system: str = "",
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        from google.genai import types
        
        response = self.client.models.generate_content(
            model=model or self.default_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system if system else None,
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
        )
        return response.text


class LocalProvider(LLMProvider):
    """Local LLM server (OpenAI-compatible API, e.g. LM Studio, Ollama)."""

    name = "local"

    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(
                api_key="local",  # Local servers typically don't need a key
                base_url=settings.local_base_url or "http://localhost:1234/v1",
            )
        return self._client

    @property
    def is_available(self) -> bool:
        return bool(settings.local_base_url)

    @property
    def default_model(self) -> str:
        return settings.local_model or "glm-4.7-flash-mlx"

    async def generate(
        self,
        prompt: str,
        system: str = "",
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=model or self.default_model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=messages,
        )

        content = response.choices[0].message.content
        if content is None:
            raise ValueError(
                f"Local model '{model or self.default_model}' returned None. "
                "Model may not be fully loaded or ran out of context."
            )
        return content


class OpenRouterProvider(LLMProvider):
    """OpenRouter provider - access to multiple models via single API."""

    name = "openrouter"
    
    def __init__(self):
        self._client = None
    
    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=settings.openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "AVR Backend"
                }
            )
        return self._client
    
    @property
    def is_available(self) -> bool:
        return bool(settings.openrouter_api_key)
    
    @property
    def default_model(self) -> str:
        return settings.openrouter_model or "google/gemma-2-9b-it:free"
    
    async def generate(
        self,
        prompt: str,
        system: str = "",
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        response = self.client.chat.completions.create(
            model=model or self.default_model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content


class LLMRouter:
    """
    Dynamic LLM Router that supports multiple providers.
    
    Providers are lazy-loaded and only initialized when first used.
    """
    
    def __init__(self):
        self._providers: dict[str, LLMProvider] = {}
        self._provider_classes = {
            "local": LocalProvider,
            "anthropic": AnthropicProvider,
            "openai": OpenAIProvider,
            "google": GoogleProvider,
            "openrouter": OpenRouterProvider,
        }
    
    def _get_provider(self, name: str) -> LLMProvider:
        """Get or create a provider instance."""
        if name not in self._providers:
            if name not in self._provider_classes:
                raise ValueError(f"Unknown provider: {name}. Available: {list(self._provider_classes.keys())}")
            self._providers[name] = self._provider_classes[name]()
        return self._providers[name]
    
    def register_provider(self, name: str, provider_class: type[LLMProvider]):
        """Register a custom provider class."""
        self._provider_classes[name] = provider_class
    
    @property
    def available_providers(self) -> list[str]:
        """List all providers that have API keys configured."""
        return [
            name for name, cls in self._provider_classes.items()
            if self._get_provider(name).is_available
        ]
    
    def get_default_provider(self) -> str:
        """Get the default provider, falling back if not available."""
        default = settings.default_provider
        if self._get_provider(default).is_available:
            return default
        
        # Fallback to first available provider
        for name in self._provider_classes:
            if self._get_provider(name).is_available:
                return name
        
        raise RuntimeError("No LLM providers are configured. Please set at least one API key.")
    
    async def call(
        self,
        prompt: str,
        system: str = "",
        json_output: bool = False,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> dict | str:
        """
        Call an LLM with the given prompt.
        
        Args:
            prompt: The user prompt to send.
            system: Optional system prompt.
            json_output: If True, parse the response as JSON.
            temperature: Sampling temperature (0.0 to 1.0).
            max_tokens: Maximum tokens in the response.
            provider: Override the default provider (anthropic, openai, google, openrouter).
            model: Override the default model for the provider.
        
        Returns:
            The LLM response as a string or parsed JSON dict.
        """
        provider_name = provider or self.get_default_provider()
        llm_provider = self._get_provider(provider_name)
        
        if not llm_provider.is_available:
            raise ValueError(f"Provider '{provider_name}' is not configured. Please set the API key.")
        
        text = await llm_provider.generate(
            prompt=prompt,
            system=system,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        if not text:
            raise ValueError(
                f"Provider '{provider_name}' returned empty response. "
                "Check model is loaded and server is ready."
            )

        if json_output:
            cleaned = _clean_json_response(text)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError as e:
                # Wrap in ValueError to avoid confusion with client JSON errors
                raise ValueError(
                    f"LLM returned invalid JSON: {e}. "
                    f"Raw response (first 500 chars): {text[:500]}"
                ) from e

        return text
    
    # Convenience methods for backward compatibility
    async def call_claude(
        self,
        prompt: str,
        system: str = "",
        json_output: bool = False,
        temperature: float = 0.3,
    ) -> dict | str:
        """Call Claude (Anthropic). Kept for backward compatibility."""
        return await self.call(
            prompt=prompt,
            system=system,
            json_output=json_output,
            temperature=temperature,
            provider="anthropic",
        )
    
    async def call_gpt4(
        self,
        prompt: str,
        system: str = "",
        json_output: bool = False,
    ) -> dict | str:
        """Call GPT-4 (OpenAI). Kept for backward compatibility."""
        return await self.call(
            prompt=prompt,
            system=system,
            json_output=json_output,
            provider="openai",
        )
    
    async def call_gemini(
        self,
        prompt: str,
        system: str = "",
        json_output: bool = False,
        temperature: float = 0.3,
    ) -> dict | str:
        """Call Gemini (Google)."""
        return await self.call(
            prompt=prompt,
            system=system,
            json_output=json_output,
            temperature=temperature,
            provider="google",
        )
    
    async def call_openrouter(
        self,
        prompt: str,
        system: str = "",
        json_output: bool = False,
        temperature: float = 0.3,
        model: Optional[str] = None,
    ) -> dict | str:
        """Call OpenRouter with any supported model."""
        return await self.call(
            prompt=prompt,
            system=system,
            json_output=json_output,
            temperature=temperature,
            provider="openrouter",
            model=model,
        )


# Global instance
llm_router = LLMRouter()
