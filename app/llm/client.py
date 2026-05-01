"""LLM Client for Research Formation System.

This module provides a unified interface to multiple LLM providers,
with OpenRouter as primary and direct providers as fallback.
"""

import os
import logging
from typing import Optional, AsyncGenerator
from dataclasses import dataclass
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


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
        user_id: Optional[str] = None,
    ) -> LLMResponse:
        """
        Generate completion from LLM.

        Provider priority: configured default first, then cloud fallbacks.
        Pass user_id to automatically track token usage after a successful call.
        """
        provider = self.settings.default_provider

        # 1. Local (Ollama) – preferred when explicitly configured
        if provider == "local" and self.settings.local_base_url:
            try:
                resp = await self._call_local(prompt, system_prompt, model, temperature, max_tokens)
                _log_complete_response(resp)
                await self._track_usage(user_id, resp)
                return resp
            except Exception as e:
                logger.warning("Local LLM failed: %s, falling back to cloud...", e)

        # 2. Google – preferred when explicitly configured
        if provider == "google" and self.settings.google_api_key:
            try:
                resp = await self._call_google(prompt, system_prompt, model, temperature, max_tokens)
                _log_complete_response(resp)
                await self._track_usage(user_id, resp)
                return resp
            except Exception as e:
                logger.warning("Google failed: %s, falling back...", e)

        # 3. OpenRouter
        if self.settings.openrouter_api_key:
            try:
                resp = await self._call_openrouter(prompt, system_prompt, model, temperature, max_tokens)
                _log_complete_response(resp)
                await self._track_usage(user_id, resp)
                return resp
            except Exception as e:
                logger.warning("OpenRouter failed: %s, falling back...", e)

        # 4. Anthropic
        if self.settings.anthropic_api_key:
            try:
                resp = await self._call_anthropic(prompt, system_prompt, model, temperature, max_tokens)
                _log_complete_response(resp)
                await self._track_usage(user_id, resp)
                return resp
            except Exception as e:
                logger.warning("Anthropic failed: %s", e)

        # 5. OpenAI
        if self.settings.openai_api_key:
            try:
                resp = await self._call_openai(prompt, system_prompt, model, temperature, max_tokens)
                _log_complete_response(resp)
                await self._track_usage(user_id, resp)
                return resp
            except Exception as e:
                logger.warning("OpenAI failed: %s", e)

        # 6. Google fallback (if not already tried as primary)
        if provider != "google" and self.settings.google_api_key:
            try:
                resp = await self._call_google(prompt, system_prompt, model, temperature, max_tokens)
                _log_complete_response(resp)
                await self._track_usage(user_id, resp)
                return resp
            except Exception as e:
                logger.warning("Google fallback failed: %s", e)

        raise RuntimeError("No LLM provider available")

    async def _track_usage(self, user_id: Optional[str], resp: LLMResponse) -> None:
        """Track token usage for a user after a successful LLM call."""
        if not user_id or not resp.usage:
            return
        tokens = (resp.usage.get("prompt_tokens") or 0) + (resp.usage.get("completion_tokens") or 0)
        if tokens > 0:
            from app.core.supabase_client import supabase_service
            await supabase_service.increment_token_usage(user_id, tokens)

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
        logger.info(
            "[LLM STREAM] Starting stream — provider=%s max_tokens=%d prompt_chars=%d",
            provider, max_tokens, len(prompt),
        )

        accumulated: list[str] = []

        async def _route() -> AsyncGenerator[str, None]:
            # 1. Local (Ollama)
            if provider == "local" and self.settings.local_base_url:
                async for chunk in self._stream_local(prompt, system_prompt, model, temperature, max_tokens):
                    yield chunk
                return

            # 2. Google (Gemini)
            if provider == "google" and self.settings.google_api_key:
                async for chunk in self._stream_google(prompt, system_prompt, model, temperature, max_tokens):
                    yield chunk
                return

            # 3. Anthropic
            if provider == "anthropic" and self.settings.anthropic_api_key:
                async for chunk in self._stream_anthropic(prompt, system_prompt, model, temperature, max_tokens):
                    yield chunk
                return

            # 4. OpenRouter
            if provider == "openrouter" and self.settings.openrouter_api_key:
                async for chunk in self._stream_openrouter(prompt, system_prompt, model, temperature, max_tokens):
                    yield chunk
                return

            # Fallback: try any available provider
            if self.settings.openrouter_api_key:
                async for chunk in self._stream_openrouter(prompt, system_prompt, model, temperature, max_tokens):
                    yield chunk
                return

            if self.settings.anthropic_api_key:
                async for chunk in self._stream_anthropic(prompt, system_prompt, model, temperature, max_tokens):
                    yield chunk
                return

            if self.settings.google_api_key:
                async for chunk in self._stream_google(prompt, system_prompt, model, temperature, max_tokens):
                    yield chunk
                return

            # Last resort: non-streaming complete()
            response = await self.complete(prompt, system_prompt, model, temperature, max_tokens)
            yield response.content

        async for chunk in _route():
            accumulated.append(chunk)
            yield chunk

        full_text = "".join(accumulated)
        logger.info(
            "[LLM STREAM] Done — provider=%s total_chars=%d chunks=%d preview=%r",
            provider, len(full_text), len(accumulated), full_text[:300],
        )

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

    async def _call_google(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Call Google Gemini API (non-streaming)."""
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.settings.google_api_key)
        model = model or self.settings.google_model or "gemini-2.0-flash"

        config = types.GenerateContentConfig(
            system_instruction=system_prompt if system_prompt else None,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        response = await client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )

        return LLMResponse(
            content=response.text,
            model=model,
            usage={
                "prompt_tokens": response.usage_metadata.prompt_token_count,
                "completion_tokens": response.usage_metadata.candidates_token_count,
            } if response.usage_metadata else None,
            finish_reason=str(response.candidates[0].finish_reason) if response.candidates else None,
        )

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
        logger.info("[LLM STREAM] google model resolved → %s", model)

        config = types.GenerateContentConfig(
            system_instruction=system_prompt if system_prompt else None,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        chunk_index = 0
        async for chunk in await client.aio.models.generate_content_stream(
            model=model,
            contents=prompt,
            config=config,
        ):
            finish = chunk.candidates[0].finish_reason if chunk.candidates else None
            logger.debug(
                "[GOOGLE CHUNK %d] finish_reason=%s text=%r",
                chunk_index, finish, chunk.text,
            )
            chunk_index += 1
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


def _log_complete_response(resp: LLMResponse) -> None:
    """Log a completed (non-streaming) LLM response."""
    logger.info(
        "[LLM COMPLETE] model=%s finish_reason=%s usage=%s chars=%d preview=%r",
        resp.model, resp.finish_reason, resp.usage, len(resp.content), resp.content[:300],
    )


# Singleton instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create LLM client singleton."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
