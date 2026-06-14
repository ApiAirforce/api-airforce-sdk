"""Inference resources: chat completions, Anthropic messages, OpenAI responses."""

from __future__ import annotations

from typing import Any, List

from ._base import AsyncAPIResource, SyncAPIResource, clean, enc

_CHAT = "/v1/chat/completions"
_MESSAGES = "/v1/messages"
_COUNT_TOKENS = "/v1/messages/count_tokens"
_RESPONSES = "/v1/responses"


def _gemini_path(model: str, stream: bool) -> str:
    method = "streamGenerateContent" if stream else "generateContent"
    return f"/v1beta/models/{enc(model)}:{method}"


class Chat(SyncAPIResource):
    def create(self, *, model: str, messages: List[Any], stream: bool = False, **params: Any) -> Any:
        """Create a chat completion.

        Optional params: max_tokens, temperature, top_p, stop, tools, tool_choice,
        response_format, reasoning_effort, thinking, thinking_budget, ``models``
        (fallback array), skill, skills, transforms, ignore_defaults.
        """
        body = {"model": model, "messages": messages, "stream": stream, **clean(**params)}
        if stream:
            return self._transport.stream("POST", _CHAT, json=body)
        return self._transport.request("POST", _CHAT, json=body)


class AsyncChat(AsyncAPIResource):
    async def create(self, *, model: str, messages: List[Any], stream: bool = False, **params: Any) -> Any:
        body = {"model": model, "messages": messages, "stream": stream, **clean(**params)}
        if stream:
            return await self._transport.stream("POST", _CHAT, json=body)
        return await self._transport.request("POST", _CHAT, json=body)


class Messages(SyncAPIResource):
    def create(self, *, model: str, messages: List[Any], max_tokens: int, stream: bool = False, **params: Any) -> Any:
        """Create an Anthropic-style message. Optional: system, temperature, top_p,
        top_k, stop_sequences, tools, tool_choice, thinking, fallbacks, ``models``."""
        body = {"model": model, "messages": messages, "max_tokens": max_tokens, "stream": stream, **clean(**params)}
        if stream:
            return self._transport.stream("POST", _MESSAGES, json=body)
        return self._transport.request("POST", _MESSAGES, json=body)

    def count_tokens(self, *, messages: List[Any], **params: Any) -> Any:
        return self._transport.request("POST", _COUNT_TOKENS, json={"messages": messages, **clean(**params)})


class AsyncMessages(AsyncAPIResource):
    async def create(self, *, model: str, messages: List[Any], max_tokens: int, stream: bool = False, **params: Any) -> Any:
        body = {"model": model, "messages": messages, "max_tokens": max_tokens, "stream": stream, **clean(**params)}
        if stream:
            return await self._transport.stream("POST", _MESSAGES, json=body)
        return await self._transport.request("POST", _MESSAGES, json=body)

    async def count_tokens(self, *, messages: List[Any], **params: Any) -> Any:
        return await self._transport.request("POST", _COUNT_TOKENS, json={"messages": messages, **clean(**params)})


class Responses(SyncAPIResource):
    def create(self, *, model: str, input: Any, stream: bool = False, **params: Any) -> Any:
        body = {"model": model, "input": input, "stream": stream, **clean(**params)}
        if stream:
            return self._transport.stream("POST", _RESPONSES, json=body)
        return self._transport.request("POST", _RESPONSES, json=body)


class AsyncResponses(AsyncAPIResource):
    async def create(self, *, model: str, input: Any, stream: bool = False, **params: Any) -> Any:
        body = {"model": model, "input": input, "stream": stream, **clean(**params)}
        if stream:
            return await self._transport.stream("POST", _RESPONSES, json=body)
        return await self._transport.request("POST", _RESPONSES, json=body)


class Gemini(SyncAPIResource):
    def generate_content(self, model: str, *, contents: List[Any], **params: Any) -> Any:
        """Gemini-format ``generateContent``. Optional: systemInstruction, tools,
        toolConfig, generationConfig."""
        return self._transport.request("POST", _gemini_path(model, False),
                                       json={"contents": contents, **clean(**params)})

    def stream_generate_content(self, model: str, *, contents: List[Any], **params: Any) -> Any:
        return self._transport.stream("POST", _gemini_path(model, True),
                                      json={"contents": contents, **clean(**params)})


class AsyncGemini(AsyncAPIResource):
    async def generate_content(self, model: str, *, contents: List[Any], **params: Any) -> Any:
        return await self._transport.request("POST", _gemini_path(model, False),
                                             json={"contents": contents, **clean(**params)})

    async def stream_generate_content(self, model: str, *, contents: List[Any], **params: Any) -> Any:
        return await self._transport.stream("POST", _gemini_path(model, True),
                                            json={"contents": contents, **clean(**params)})
