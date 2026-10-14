"""LLM access. Any callable `chat(messages, system) -> str` can be plugged into the pipeline."""
from __future__ import annotations

import os
from typing import Callable

Chat = Callable[[list[dict], str], str]

DEFAULT_MODEL = "claude-sonnet-5-5"


def anthropic_chat(model: str = DEFAULT_MODEL, max_tokens: int = 8000, temperature: float = 0.2) -> Chat:
    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError("pip install anthropic") from e
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    client = anthropic.Anthropic()

    def chat(messages: list[dict], system: str) -> str:
        resp = client.messages.create(model=model, max_tokens=max_tokens, temperature=temperature,
                                      system=system, messages=messages)
        return "".join(b.text for b in resp.content if b.type == "text").strip()

    return chat
