"""Backend that shells out to the Claude Code CLI.

This is the default because it needs no ``ANTHROPIC_API_KEY``: it reuses the
Claude Code login already on the machine. The cost is that ``claude -p`` is
single-shot and accepts no custom tool schemas, which is why the agents in
this package use a parsed text protocol instead of native tool-use blocks.

Getting a *clean* evaluation out of it takes four deliberate flags. Without
them you are not measuring the model against your benchmark -- you are
measuring Claude Code, with its coding-agent identity, your repo's CLAUDE.md,
your MCP servers and a filesystem it can actually read.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any

from .base import LLMRequest, LLMResponse

#: Where the npm global install keeps the real binary, relative to the shims.
_REAL_EXE = Path("node_modules/@anthropic-ai/claude-code/bin/claude.exe")


def resolve_executable(explicit: str | None = None) -> str:
    """Find the real ``claude`` binary, skipping the Windows shims.

    ``shutil.which("claude")`` returns ``claude.CMD`` on Windows. Running a
    batch shim mangles any argument containing ``{``, ``%``, quotes or
    newlines -- which is every system prompt this package sends. The symptom
    is not an error: the model receives corrupted instructions and answers in
    prose, and you are left debugging the prompt instead of the launcher.
    """
    if explicit:
        return explicit
    found = shutil.which("claude")
    if not found:
        return "claude"
    path = Path(found)
    if path.suffix.lower() in (".cmd", ".bat", ".ps1"):
        real = path.parent / _REAL_EXE
        if real.exists():
            return str(real)
    return str(path)


class ClaudeCliBackend:
    name = "claude-cli"

    def __init__(self, executable: str | None = None, timeout: int = 600) -> None:
        self.executable = resolve_executable(executable)
        self.timeout = timeout
        self.total_cost_usd = 0.0
        self._lock = threading.Lock()  # rollouts run concurrently

    def describe(self) -> dict[str, Any]:
        return {"backend": self.name, "executable": self.executable}

    def build_command(self, req: LLMRequest) -> list[str]:
        return [
            self.executable,
            "-p",
            req.prompt,
            "--output-format",
            "json",
            "--model",
            req.model,
            # Replace, never append. Appending leaves Claude Code's own
            # coding-agent identity in front of ours, and it wins -- the model
            # goes looking for a real records service in the repo instead of
            # using the simulated one. Replacing also cuts ~25k tokens of
            # default prompt per call, which is a ~30x cost difference.
            "--system-prompt",
            req.system,
            # Disable every built-in tool. The benchmark environment is
            # simulated; a model that can really Read and Bash will solve --
            # or appear to solve -- tasks by other means, and the trace stops
            # being evidence about the skill set.
            "--tools",
            "",
            # Ignore user/project/local settings, so a CLAUDE.md or a stray
            # hook cannot leak into the measurement.
            "--restricted",
            # ...and no MCP servers either.
            "--strict-mcp-config",
        ]

    def complete(self, req: LLMRequest) -> LLMResponse:
        try:
            proc = subprocess.run(
                self.build_command(req),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
                env={**os.environ, "CLAUDE_CODE_DISABLE_TERMINAL_TITLE": "1"},
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

        text, usage, cost = _parse(proc.stdout)
        with self._lock:
            self.total_cost_usd += cost
        return LLMResponse(text=text, model=req.model, usage=usage)


def _parse(stdout: str) -> tuple[str, dict[str, int], float]:
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

    if payload.get("is_error"):
        raise RuntimeError(f"claude CLI reported an error: {str(payload.get('result'))[:300]}")

    text = payload.get("result") or payload.get("text") or ""
    if not text and isinstance(payload.get("content"), list):
        text = "".join(b.get("text", "") for b in payload["content"] if isinstance(b, dict))

    raw_usage = payload.get("usage") or {}
    usage = {k: v for k, v in raw_usage.items() if isinstance(v, int)}
    cost = payload.get("total_cost_usd")
    return str(text), usage, float(cost) if isinstance(cost, (int, float)) else 0.0
