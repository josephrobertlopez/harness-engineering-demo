"""Backend using the official Anthropic Python SDK.

Requires credentials: ``ANTHROPIC_API_KEY``, ``ANTHROPIC_AUTH_TOKEN``, or an
``ant auth login`` profile. The zero-argument client resolves all three, so an
unset API key does not by itself mean there are no credentials.

The per-model request shape matters and is handled here rather than in the
agents:

* Opus 5 / Sonnet 5 -- ``thinking={"type": "adaptive"}`` with depth set by
  ``output_config.effort``. ``temperature`` / ``top_p`` / ``top_k`` are
  **removed** on these models and return HTTP 400.
* Haiku 4.5 -- ``thinking={"type": "enabled", "budget_tokens": N}``; passing
  ``effort`` errors. Sampling parameters are still accepted.
"""

from __future__ import annotations

from typing import Any

from ..config import caps_for
from .base import LLMRequest, LLMResponse


class AnthropicBackend:
    name = "anthropic"

    def __init__(self, client: Any | None = None) -> None:
        if client is None:
            try:
                import anthropic
            except ImportError as exc:  # pragma: no cover - depends on install
                raise RuntimeError(
                    "the anthropic backend needs the SDK: pip install 'wikiskill[api]'"
                ) from exc
            client = anthropic.Anthropic()
        self.client = client

    def describe(self) -> dict[str, Any]:
        return {"backend": self.name}

    def complete(self, req: LLMRequest) -> LLMResponse:
        caps = caps_for(req.model)
        kwargs: dict[str, Any] = {
            "model": req.model,
            "max_tokens": req.max_tokens,
            "system": req.system,
            "messages": [{"role": "user", "content": req.prompt}],
        }

        if caps.thinking == "adaptive":
            kwargs["thinking"] = {"type": "adaptive"}
            if caps.supports_effort and req.effort:
                kwargs["output_config"] = {"effort": req.effort}
        else:
            # Budget must be strictly less than max_tokens, minimum 1024.
            budget = max(1024, min(req.max_tokens - 1024, req.max_tokens // 2))
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget}

        message = self.client.messages.create(**kwargs)

        if getattr(message, "stop_reason", None) == "refusal":
            details = getattr(message, "stop_details", None)
            category = getattr(details, "category", None)
            raise RuntimeError(f"model declined the request (category={category})")

        text = "".join(
            block.text for block in message.content if getattr(block, "type", "") == "text"
        )
        usage = {}
        raw = getattr(message, "usage", None)
        for key in ("input_tokens", "output_tokens", "cache_read_input_tokens"):
            value = getattr(raw, key, None)
            if isinstance(value, int):
                usage[key] = value
        return LLMResponse(text=text, model=req.model, usage=usage)
