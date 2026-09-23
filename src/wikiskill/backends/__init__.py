"""Model backends: mock (offline), claude-cli (default), anthropic (SDK)."""

from __future__ import annotations

from pathlib import Path

from .base import Backend, CachingBackend, LLMRequest, LLMResponse

BACKENDS = ("claude-cli", "mock", "anthropic")


def get_backend(name: str, *, cache_dir: Path | None = None, cache: bool = True) -> Backend:
    if name == "mock":
        from .mock import MockBackend

        inner: Backend = MockBackend()
    elif name == "claude-cli":
        from .claude_cli import ClaudeCliBackend

        inner = ClaudeCliBackend()
    elif name == "anthropic":
        from .anthropic_api import AnthropicBackend

        inner = AnthropicBackend()
    else:
        raise ValueError(f"unknown backend {name!r}; expected one of {BACKENDS}")

    if cache_dir is None:
        return inner
    return CachingBackend(inner, cache_dir, enabled=cache)


__all__ = ["BACKENDS", "Backend", "CachingBackend", "LLMRequest", "LLMResponse", "get_backend"]
