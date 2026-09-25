"""DEVX-311: an MCP server over a fixed, read-only set of git and rg commands.

Spec: openspec/changes/add-cli-mcp/specs/cli-mcp/spec.md

    claude mcp add cli-tools -- python /abs/path/server.py --root /abs/path/to/repo

Stdlib only. The MCP Python SDK (``FastMCP``) is the usual way to write
this; the exercise README shows that version. This one hand-rolls the four
methods it needs so the repository's grading stays install-free.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TextIO

PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {"name": "cli-tools", "version": "0.1.0"}
TIMEOUT_SECONDS = 10
MAX_OUTPUT = 8000
TRUNCATED = "\n[truncated]"

PARSE_ERROR = -32700
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602


class ToolError(Exception):
    """A failure the model should read: returned as ``isError``, never raised
    as a protocol error, because clients do not show those to the model."""


@dataclass(frozen=True, slots=True)
class Completed:
    returncode: int
    stdout: str
    stderr: str


Runner = Callable[[list[str], Path], Completed]


def run_command(argv: list[str], cwd: Path, timeout: float = TIMEOUT_SECONDS) -> Completed:
    exe = shutil.which(argv[0])
    if exe is None:
        raise ToolError(f"{argv[0]} is not installed on this machine")
    try:
        # An argument list and no shell: nothing the model sends is ever
        # parsed by a shell, so there is nothing to quote or escape.
        proc = subprocess.run(
            [exe, *argv[1:]],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise ToolError(f"{argv[0]} timed out after {timeout:g} s") from None
    return Completed(proc.returncode, proc.stdout, proc.stderr)


# --------------------------------------------------------------------------
# Tools: each validates its own arguments and returns a fixed argv.


def _no_args(args: dict) -> None:
    if args:
        raise ToolError(f"unexpected argument(s): {', '.join(sorted(args))}")


def _only(args: dict, allowed: set[str]) -> None:
    extra = set(args) - allowed
    if extra:
        raise ToolError(f"unexpected argument(s): {', '.join(sorted(extra))}")


def _inside(root: Path, path: str) -> str:
    resolved = (root / path).resolve()
    if resolved != root and root not in resolved.parents:
        raise ToolError(f"path {path!r} escapes the root {root}")
    return path


def build_git_status(args: dict, root: Path) -> list[str]:
    _no_args(args)
    return ["git", "status", "--porcelain=v1", "--branch"]


def build_git_diff_stat(args: dict, root: Path) -> list[str]:
    _no_args(args)
    return ["git", "diff", "--stat"]


def build_git_log(args: dict, root: Path) -> list[str]:
    _only(args, {"limit"})
    limit = args.get("limit", 10)
    # bool is an int subclass; `true` must not become `-n 1`.
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50:
        raise ToolError("limit must be an integer from 1 to 50")
    return ["git", "log", "--oneline", "-n", str(limit)]


def build_rg_search(args: dict, root: Path) -> list[str]:
    _only(args, {"pattern", "path"})
    pattern = args.get("pattern")
    if not isinstance(pattern, str) or not pattern:
        raise ToolError("pattern must be a non-empty string")
    path = args.get("path", ".")
    if not isinstance(path, str):
        raise ToolError("path must be a string")
    # -e and -- keep a pattern like "--files" from being read as a flag.
    return [
        "rg", "--line-number", "--no-heading", "--color", "never", "--max-count", "50",
        "-e", pattern, "--", _inside(root, path),
    ]


@dataclass(frozen=True, slots=True)
class Tool:
    name: str
    description: str
    schema: dict
    build: Callable[[dict, Path], list[str]]
    ok_codes: frozenset[int] = frozenset({0})

    def describe(self) -> dict:
        return {"name": self.name, "description": self.description, "inputSchema": self.schema}


def _schema(properties: dict | None = None, required: list[str] | None = None) -> dict:
    schema = {"type": "object", "properties": properties or {}, "additionalProperties": False}
    if required:
        schema["required"] = required
    return schema


TOOLS: dict[str, Tool] = {
    t.name: t
    for t in (
        Tool(
            "git_status",
            "Working-tree status of the repository (porcelain v1, with branch line).",
            _schema(),
            build_git_status,
        ),
        Tool(
            "git_log",
            "Recent commits, one line each.",
            _schema({"limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10}}),
            build_git_log,
        ),
        Tool(
            "git_diff_stat",
            "Files changed in the working tree and how many lines, without the diff itself.",
            _schema(),
            build_git_diff_stat,
        ),
        Tool(
            "rg_search",
            "Search file contents with ripgrep. Returns path:line:text, at most 50 matches per file.",
            _schema(
                {
                    "pattern": {"type": "string", "minLength": 1, "description": "Regex to search for."},
                    "path": {"type": "string", "default": ".", "description": "File or folder, relative to the root."},
                },
                required=["pattern"],
            ),
            build_rg_search,
            # rg exits 1 when nothing matched. That is an answer, not a failure.
            ok_codes=frozenset({0, 1}),
        ),
    )
}


# --------------------------------------------------------------------------
# JSON-RPC


class Server:
    def __init__(self, root: Path, runner: Runner = run_command):
        self.root = root.resolve()
        self.runner = runner

    def handle(self, message: dict) -> dict | None:
        if "id" not in message:
            return None  # a notification; JSON-RPC forbids answering it
        mid, method = message["id"], message.get("method")
        params = message.get("params") or {}
        if method == "initialize":
            return _result(mid, {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
            })
        if method == "ping":
            return _result(mid, {})
        if method == "tools/list":
            return _result(mid, {"tools": [t.describe() for t in TOOLS.values()]})
        if method == "tools/call":
            tool = TOOLS.get(params.get("name"))
            if tool is None:
                return _error(mid, INVALID_PARAMS, f"Unknown tool: {params.get('name')}")
            return _result(mid, self._call(tool, params.get("arguments") or {}))
        return _error(mid, METHOD_NOT_FOUND, f"Method not found: {method}")

    def _call(self, tool: Tool, args: dict) -> dict:
        try:
            if not isinstance(args, dict):
                raise ToolError("arguments must be an object")
            argv = tool.build(args, self.root)
            done = self.runner(argv, self.root)
            if done.returncode not in tool.ok_codes:
                detail = (done.stderr or done.stdout).strip() or "no output"
                raise ToolError(f"{argv[0]} exited {done.returncode}: {detail}")
            text = done.stdout if done.stdout.strip() else "no matches" if tool.name == "rg_search" else "(no output)"
            return _text(truncate(text), is_error=False)
        except ToolError as exc:
            return _text(str(exc), is_error=True)

    def serve(self, stdin: TextIO, stdout: TextIO) -> int:
        for line in stdin:
            if not line.strip():
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError as exc:
                response = _error(None, PARSE_ERROR, f"Parse error: {exc.msg}")
            else:
                response = self.handle(message) if isinstance(message, dict) else None
            if response is not None:
                # One message per line: stdio MCP framing has no other delimiter.
                stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
                stdout.flush()
        return 0


def truncate(text: str) -> str:
    return text if len(text) <= MAX_OUTPUT else text[:MAX_OUTPUT] + TRUNCATED


def _text(text: str, is_error: bool) -> dict:
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def _result(mid, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def _error(mid, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MCP server for git and rg (stdio).")
    parser.add_argument("--root", type=Path, required=True, help="directory every command runs in")
    args = parser.parse_args(argv)
    if not args.root.is_dir():
        parser.error(f"--root {args.root} is not a directory")
    # stdout is the protocol channel; anything else written there corrupts it.
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    return Server(args.root).serve(sys.stdin, sys.stdout)


if __name__ == "__main__":
    sys.exit(main())
