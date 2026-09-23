"""Backend protocol and a content-addressed response cache.

Every agent in this package talks to the model through one narrow shape: a
system prompt plus a single fully-rendered prompt string, in; text, out.

That is a deliberate constraint rather than a simplification. The default
backend shells out to ``claude -p``, which is single-shot and cannot be handed
custom tool schemas, so a tool-use loop expressed through the API's native
``tool_use`` blocks would work on one backend and not the others. Instead the
ReAct loops here are a *text protocol* the harness parses, which behaves
identically under ``mock``, ``claude-cli`` and ``anthropic``. Multi-turn state
is carried by re-rendering the transcript into the prompt each turn.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from ..util import canonical_json, content_sha, read_json, write_json


@dataclass(frozen=True, slots=True)
class LLMRequest:
    role: str
    """One of inference / maintainer / proposer. The mock backend dispatches
    on it; the real backends use it only for logging."""
    model: str
    system: str
    prompt: str
    max_tokens: int = 8000
    effort: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    """Out-of-band data for the mock backend. Never sent to a real model."""

    def cache_key(self) -> str:
        return content_sha(
            canonical_json(
                {
                    "role": self.role,
                    "model": self.model,
                    "system": self.system,
                    "prompt": self.prompt,
                    "max_tokens": self.max_tokens,
                    "effort": self.effort,
                }
            )
        )


@dataclass(frozen=True, slots=True)
class LLMResponse:
    text: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)


class Backend(Protocol):
    name: str

    def describe(self) -> dict[str, Any]: ...

    def complete(self, req: LLMRequest) -> LLMResponse: ...


class CachingBackend:
    """Wraps a backend with an on-disk, content-addressed response cache.

    This is what makes ``--resume`` cheap and debugging tractable: replaying a
    workspace re-issues zero model calls for work that already completed.

    It is not a determinism guarantee for a cold run. ``temperature`` is
    removed on Opus 5 and Sonnet 5 (it returns HTTP 400), so sampling cannot
    be pinned; the cache makes runs *reproducible on replay*, and only the
    mock backend is deterministic cold.
    """

    def __init__(self, inner: Backend, cache_dir: Path, enabled: bool = True) -> None:
        self.inner = inner
        self.cache_dir = cache_dir
        self.enabled = enabled
        self.name = inner.name
        self.hits = 0
        self.misses = 0

    def describe(self) -> dict[str, Any]:
        return {**self.inner.describe(), "cache": self.enabled}

    def complete(self, req: LLMRequest) -> LLMResponse:
        if not self.enabled:
            return self.inner.complete(req)
        path = self.cache_dir / f"{req.cache_key()}.json"
        if path.exists():
            self.hits += 1
            d = read_json(path)
            return LLMResponse(text=d["text"], model=d["model"], usage=d.get("usage", {}))
        self.misses += 1
        resp = self.inner.complete(req)
        write_json(path, {"text": resp.text, "model": resp.model, "usage": resp.usage})
        return resp
