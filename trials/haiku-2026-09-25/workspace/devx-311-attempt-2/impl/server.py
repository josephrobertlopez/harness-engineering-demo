#!/usr/bin/env python3
"""MCP server for CLI tools (git and ripgrep)."""

import json
import sys
import argparse
import subprocess
import os
import signal
from pathlib import Path
from typing import Any, Dict, Optional


class TimeoutError(Exception):
    """Command execution timeout."""
    pass


class CommandRunner:
    """Runs commands with timeout and output limits."""

    TIMEOUT_SECONDS = 10
    OUTPUT_LIMIT = 8000

    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir).resolve()

    def validate_path(self, path: str) -> Path:
        """Validate path stays within root directory."""
        if not path:
            path = "."

        # Resolve path relative to root
        full_path = (self.root_dir / path).resolve()

        # Check if resolved path is within root
        try:
            full_path.relative_to(self.root_dir)
        except ValueError:
            raise ValueError(f"Path escapes root directory: {path}")

        return full_path

    def run_command(self, args: list, cwd: Optional[Path] = None) -> Dict[str, Any]:
        """Run command with timeout and output limit."""
        if cwd is None:
            cwd = self.root_dir

        try:
            result = subprocess.run(
                args,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=self.TIMEOUT_SECONDS,
            )

            output = result.stdout
            if len(output) > self.OUTPUT_LIMIT:
                output = output[:self.OUTPUT_LIMIT] + "[truncated]"

            # Special case: rg exit code 1 means no matches, which is success
            if result.returncode == 0 or (args[0] == "rg" and result.returncode == 1):
                return {"isError": False, "output": output}
            else:
                reason = result.stderr or f"Command failed with exit code {result.returncode}"
                return {"isError": True, "reason": reason}

        except subprocess.TimeoutExpired:
            return {"isError": True, "reason": "Command timeout after 10 seconds"}
        except FileNotFoundError as e:
            return {"isError": True, "reason": f"Binary not found: {e}"}
        except Exception as e:
            return {"isError": True, "reason": str(e)}


class MCPServer:
    """MCP server implementation."""

    PROTOCOL_VERSION = "2025-06-18"

    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.runner = CommandRunner(root_dir)
        self.tools = {
            "git_status": self.git_status,
            "git_log": self.git_log,
            "git_diff_stat": self.git_diff_stat,
            "rg_search": self.rg_search,
        }

    def git_status(self, **kwargs) -> Dict[str, Any]:
        """git status --porcelain=v1 --branch"""
        if kwargs:
            return {"isError": True, "reason": "git_status accepts no arguments"}

        result = self.runner.run_command(["git", "status", "--porcelain=v1", "--branch"])
        return result

    def git_log(self, limit: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        """git log --oneline -n <limit>"""
        if kwargs:
            return {"isError": True, "reason": "git_log accepts only limit argument"}

        if limit is None:
            limit = 10

        # Validate limit
        if not isinstance(limit, int):
            return {"isError": True, "reason": "limit must be an integer"}
        if limit < 1 or limit > 50:
            return {"isError": True, "reason": "limit must be between 1 and 50"}

        result = self.runner.run_command(["git", "log", "--oneline", "-n", str(limit)])
        return result

    def git_diff_stat(self, **kwargs) -> Dict[str, Any]:
        """git diff --stat"""
        if kwargs:
            return {"isError": True, "reason": "git_diff_stat accepts no arguments"}

        result = self.runner.run_command(["git", "diff", "--stat"])
        return result

    def rg_search(self, pattern: Optional[str] = None, path: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """ripgrep search with -e pattern -- path"""
        if kwargs:
            return {"isError": True, "reason": "rg_search accepts only pattern and path arguments"}

        if not pattern:
            return {"isError": True, "reason": "pattern argument is required"}

        # Validate path
        if path is None:
            path = "."

        try:
            validated_path = self.runner.validate_path(path)
        except ValueError as e:
            return {"isError": True, "reason": str(e)}

        # Build ripgrep command with fixed flags
        args = [
            "rg",
            "--line-number",
            "--no-heading",
            "--color", "never",
            "--max-count", "50",
            "-e", pattern,
            "--",
            str(validated_path),
        ]

        result = self.runner.run_command(args, cwd=self.runner.root_dir)
        return result

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP request."""
        method = request.get("method")

        if method == "initialize":
            return {
                "protocolVersion": self.PROTOCOL_VERSION,
                "capabilities": {
                    "tools": [
                        {"name": tool, "description": f"Tool: {tool}"}
                        for tool in self.tools
                    ]
                }
            }

        elif method == "tools/call":
            tool_name = request.get("params", {}).get("name")
            tool_args = request.get("params", {}).get("arguments", {})

            if tool_name not in self.tools:
                return {"error": {"code": -32602, "message": f"Unknown tool: {tool_name}"}}

            tool = self.tools[tool_name]
            result = tool(**tool_args)
            return {"result": result}

        else:
            return {"error": {"code": -32601, "message": f"Unknown method: {method}"}}


def main():
    parser = argparse.ArgumentParser(description="MCP server for CLI tools")
    parser.add_argument("--root", required=True, help="Root directory for command execution")
    args = parser.parse_args()

    server = MCPServer(args.root)

    # Simple JSON-RPC server over stdio
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = server.handle_request(request)
            print(json.dumps(response))
            sys.stdout.flush()
        except json.JSONDecodeError:
            error_response = {"error": {"code": -32700, "message": "Parse error"}}
            print(json.dumps(error_response))
            sys.stdout.flush()


if __name__ == "__main__":
    main()
