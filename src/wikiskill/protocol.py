"""The text protocol the agents speak, and its parsers.

Native ``tool_use`` blocks are not usable here: the default backend is
``claude -p``, which is single-shot and takes no custom tool schemas. So tool
calls travel as text the harness parses:

    THOUGHT: <free text>
    ACTION: <tool_name> {"json": "args"}

    THOUGHT: <free text>
    ANSWER: {"json": "payload"}

Structured results (wiki edit batches, skill proposals) travel as a fenced
```json block. The harness validates every parsed object itself, on every
backend -- the transport is never treated as the authority for an invariant.
"""

from __future__ import annotations

import json
import re
from typing import Any

_ACTION_RE = re.compile(r"^\s*ACTION:\s*([a-z_][a-z0-9_]*)\s*(\{.*)$", re.IGNORECASE | re.DOTALL)
_ANSWER_RE = re.compile(r"^\s*ANSWER:\s*(.*)$", re.IGNORECASE | re.DOTALL)
_THOUGHT_RE = re.compile(r"^\s*THOUGHT:\s*(.*)$", re.IGNORECASE)
_FENCE_RE = re.compile(r"```(?:json)?\s*\n(.*?)```", re.DOTALL)


class ProtocolError(Exception):
    """The model's output did not match the protocol."""


def parse_thought(text: str) -> str:
    for line in text.splitlines():
        m = _THOUGHT_RE.match(line)
        if m:
            return m.group(1).strip()
    return ""


def parse_action(text: str) -> tuple[str, dict[str, Any]] | None:
    """Return ``(tool_name, args)`` for the first ACTION line, if any."""
    for idx, line in enumerate(text.splitlines()):
        if not line.strip().upper().startswith("ACTION:"):
            continue
        rest = "\n".join(text.splitlines()[idx:])
        m = _ACTION_RE.match(rest)
        if not m:
            raise ProtocolError(f"malformed ACTION line: {line.strip()[:120]}")
        name = m.group(1).strip()
        args = _first_json_object(m.group(2))
        if not isinstance(args, dict):
            raise ProtocolError(f"ACTION arguments must be a JSON object, got {type(args).__name__}")
        return name, args
    return None


def parse_answer(text: str) -> dict[str, Any] | None:
    """Return the JSON payload of the ANSWER line, if there is one."""
    for idx, line in enumerate(text.splitlines()):
        if not line.strip().upper().startswith("ANSWER:"):
            continue
        rest = "\n".join(text.splitlines()[idx:])
        m = _ANSWER_RE.match(rest)
        payload = (m.group(1) if m else "").strip()
        if not payload:
            return None
        try:
            value = _first_json_object(payload)
        except ProtocolError:
            return None
        return value if isinstance(value, dict) else None
    return None


def parse_json_block(text: str) -> dict[str, Any]:
    """Extract the first fenced JSON object, falling back to a bare object."""
    for match in _FENCE_RE.finditer(text):
        try:
            value = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    value = _first_json_object(text)
    if not isinstance(value, dict):
        raise ProtocolError("expected a JSON object")
    return value


def _first_json_object(text: str) -> Any:
    """Decode the first complete JSON value, ignoring trailing prose.

    Models routinely append a sentence after the JSON. ``raw_decode`` stops at
    the end of the value instead of choking on what follows.
    """
    start = text.find("{")
    if start == -1:
        raise ProtocolError("no JSON object found")
    try:
        value, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError as exc:
        raise ProtocolError(f"invalid JSON: {exc}") from exc
    return value
