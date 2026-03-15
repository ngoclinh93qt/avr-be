"""LLM Client for Research Formation System.

This module provides a unified interface to multiple LLM providers,
with OpenRouter as primary and direct providers as fallback.
"""

import os
from typing import Optional, AsyncGenerator
from dataclasses import dataclass
import httpx

from app.config import get_settings


@dataclass
class LLMResponse:
    """Response from LLM."""
    content: str
    model: str
    usage: Optional[dict] = None
    finish_reason: Optional[str] = None


class LLMClient:
    """Unified LLM client with multiple provider support."""

    def __init__(self):
        self.settings = get_settings()
        self._http_client = None

    @property
    def http_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=60.0)
        return self._http_client

    async def close(self):
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """
        Generate completion from LLM.

        Provider priority:
          1. local  - Ollama / local OpenAI-compatible server (if DEFAULT_PROVIDER=local)
          2. openrouter - cloud fallback
          3. anthropic  - direct
          4. openai     - direct
        """
        # 1. Local (Ollama) – preferred when explicitly configured
        if self.settings.default_provider == "local" and self.settings.local_base_url:
            try:
                return await self._call_local(
                    prompt, system_prompt, model, temperature, max_tokens
                )
            except Exception as e:
                print(f"Local LLM failed: {e}, falling back to cloud...")

        # 2. OpenRouter
        if self.settings.openrouter_api_key:
            try:
                return await self._call_openrouter(
                    prompt, system_prompt, model, temperature, max_tokens
                )
            except Exception as e:
                print(f"OpenRouter failed: {e}, falling back...")

        # 3. Anthropic
        if self.settings.anthropic_api_key:
            try:
                return await self._call_anthropic(
                    prompt, system_prompt, model, temperature, max_tokens
                )
            except Exception as e:
                print(f"Anthropic failed: {e}")

        # 4. OpenAI
        if self.settings.openai_api_key:
            try:
                return await self._call_openai(
                    prompt, system_prompt, model, temperature, max_tokens
                )
            except Exception as e:
                print(f"OpenAI failed: {e}")

        raise RuntimeError("No LLM provider available")

    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> AsyncGenerator[str, None]:
        """
        Stream completion from LLM.

        Routes to provider based on default_provider setting.
        """
        provider = self.settings.default_provider

        # 1. Local (Ollama)
        if provider == "local" and self.settings.local_base_url:
            async for chunk in self._stream_local(
                prompt, system_prompt, model, temperature, max_tokens
            ):
                yield chunk
            return

        # 2. Google (Gemini)
        if provider == "google" and self.settings.google_api_key:
            async for chunk in self._stream_google(
                prompt, system_prompt, model, temperature, max_tokens
            ):
                yield chunk
            return

        # 3. Anthropic
        if provider == "anthropic" and self.settings.anthropic_api_key:
            async for chunk in self._stream_anthropic(
                prompt, system_prompt, model, temperature, max_tokens
            ):
                yield chunk
            return

        # 4. OpenRouter
        if provider == "openrouter" and self.settings.openrouter_api_key:
            async for chunk in self._stream_openrouter(
                prompt, system_prompt, model, temperature, max_tokens
            ):
                yield chunk
            return

        # Fallback: try any available provider
        if self.settings.openrouter_api_key:
            async for chunk in self._stream_openrouter(
                prompt, system_prompt, model, temperature, max_tokens
            ):
                yield chunk
            return

        if self.settings.anthropic_api_key:
            async for chunk in self._stream_anthropic(
                prompt, system_prompt, model, temperature, max_tokens
            ):
                yield chunk
            return

        if self.settings.google_api_key:
            async for chunk in self._stream_google(
                prompt, system_prompt, model, temperature, max_tokens
            ):
                yield chunk
            return

        # Last resort: non-streaming complete()
        response = await self.complete(
            prompt, system_prompt, model, temperature, max_tokens
        )
        yield response.content

    async def _call_local(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Call local Ollama / OpenAI-compatible server."""
        import json

        model = model or self.settings.local_model or "gemma3:4b"
        base_url = self.settings.local_base_url.rstrip("/")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.http_client.post(
            f"{base_url}/chat/completions",
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
            },
        )
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model=model,
            usage=data.get("usage"),
            finish_reason=data["choices"][0].get("finish_reason"),
        )

    async def _stream_local(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        """Stream from local Ollama / OpenAI-compatible server."""
        import json

        model = model or self.settings.local_model or "gemma3:4b"
        base_url = self.settings.local_base_url.rstrip("/")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with self.http_client.stream(
            "POST",
            f"{base_url}/chat/completions",
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
            },
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        if delta.get("content"):
                            yield delta["content"]
                    except json.JSONDecodeError:
                        continue

    async def _call_openrouter(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Call OpenRouter API."""
        model = model or "anthropic/claude-3.5-sonnet"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.http_client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.settings.openrouter_api_key}",
                "HTTP-Referer": "https://avr.app",
                "X-Title": "AVR Research Formation",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model=model,
            usage=data.get("usage"),
            finish_reason=data["choices"][0].get("finish_reason"),
        )

    async def _stream_openrouter(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        """Stream from OpenRouter API."""
        import json

        model = model or "anthropic/claude-3.5-sonnet"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with self.http_client.stream(
            "POST",
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.settings.openrouter_api_key}",
                "HTTP-Referer": "https://avr.app",
                "X-Title": "AVR Research Formation",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
            },
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        if data["choices"][0].get("delta", {}).get("content"):
                            yield data["choices"][0]["delta"]["content"]
                    except json.JSONDecodeError:
                        continue

    async def _call_anthropic(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Call Anthropic API directly."""
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        model = model or "claude-3-5-sonnet-20241022"

        response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )

        return LLMResponse(
            content=response.content[0].text,
            model=model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
            },
            finish_reason=response.stop_reason,
        )

    async def _stream_anthropic(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        """Stream from Anthropic API."""
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        model = model or "claude-3-5-sonnet-20241022"

        async with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def _stream_google(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        """Stream from Google Gemini API."""
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.settings.google_api_key)
        model = model or self.settings.google_model or "gemini-2.0-flash"

        config = types.GenerateContentConfig(
            system_instruction=system_prompt if system_prompt else None,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        for chunk in client.models.generate_content_stream(
            model=model,
            contents=prompt,
            config=config,
        ):
            if chunk.text:
                yield chunk.text

    async def _call_openai(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Call OpenAI API directly."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        model = model or "gpt-4o"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return LLMResponse(
            content=response.choices[0].message.content,
            model=model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            },
            finish_reason=response.choices[0].finish_reason,
        )


# Singleton instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create LLM client singleton."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
