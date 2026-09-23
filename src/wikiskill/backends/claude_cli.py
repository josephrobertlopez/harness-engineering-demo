"""Backend that shells out to the Claude Code CLI.

This is the default because it needs no ``ANTHROPIC_API_KEY``: it reuses the
Claude Code login already on the machine. The cost is that ``claude -p`` is
single-shot and accepts no custom tool schemas, which is why the agents in
this package use a parsed text protocol instead of native tool-use blocks.

Tools are explicitly disabled (``--allowed-tools ''``): the model being
evaluated must solve tasks through the harness's simulated environment, not
by reaching into the real filesystem.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

from .base import LLMRequest, LLMResponse


class ClaudeCliBackend:
    name = "claude-cli"

    def __init__(self, executable: str | None = None, timeout: int = 600) -> None:
        self.executable = executable or shutil.which("claude") or "claude"
        self.timeout = timeout

    def describe(self) -> dict[str, Any]:
        return {"backend": self.name, "executable": self.executable}

    def complete(self, req: LLMRequest) -> LLMResponse:
        cmd = [
            self.executable,
            "-p",
            req.prompt,
            "--output-format",
            "json",
            "--model",
            req.model,
            "--allowed-tools",
            "",
        ]
        if req.system:
            cmd += ["--append-system-prompt", req.system]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"claude CLI not found at {self.executable!r}. Install Claude Code, "
                "or run with --backend mock."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"claude CLI timed out after {self.timeout}s") from exc

        if proc.returncode != 0:
            raise RuntimeError(
                f"claude CLI exited {proc.returncode}: {(proc.stderr or proc.stdout).strip()[:800]}"
            )

        text, usage = _parse(proc.stdout)
        return LLMResponse(text=text, model=req.model, usage=usage)


def _parse(stdout: str) -> tuple[str, dict[str, int]]:
    """Pull the result text out of ``--output-format json``.

    Non-JSON stdout is treated as a failure, not as a reply. The CLI prints
    prose when it cannot start -- an expired login, an org policy that blocks
    it -- and returning that prose as if the model had said it would feed an
    error message straight into the agent loop, where it becomes a wrong
    answer, a wrong trace, and a wrong wiki pattern. Fail here instead.
    """
    stripped = stdout.strip()
    if not stripped:
        raise RuntimeError("claude CLI produced no output")
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"claude CLI did not return JSON. First 300 chars: {stripped[:300]}"
        ) from exc

    if isinstance(payload, list):
        payload = next(
            (m for m in reversed(payload) if isinstance(m, dict) and m.get("type") == "result"),
            payload[-1] if payload else {},
        )
    if not isinstance(payload, dict):
        raise RuntimeError(f"unexpected claude CLI payload type: {type(payload).__name__}")

    text = payload.get("result") or payload.get("text") or ""
    if not text and isinstance(payload.get("content"), list):
        text = "".join(
            b.get("text", "") for b in payload["content"] if isinstance(b, dict)
        )
    raw_usage = payload.get("usage") or {}
    usage = {k: v for k, v in raw_usage.items() if isinstance(v, int)}
    return str(text), usage
