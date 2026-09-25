#!/usr/bin/env python3
"""
MCP server exposing git and ripgrep commands.

Implements JSON-RPC 2.0 protocol over stdin/stdout with four safe CLI tools:
- git_status: git status
- git_log: git log with limit parameter
- git_diff_stat: git diff --stat
- rg_search: ripgrep search with pattern and path
"""

import json
import sys
import subprocess
import signal
import shlex
from pathlib import Path
from typing import Any, Dict, Optional


class MCPServer:
    """MCP server for CLI tools."""

    PROTOCOL_VERSION = "2025-06-18"
    TIMEOUT = 10
    MAX_OUTPUT = 8000

    TOOLS = {
        "git_status": {
            "description": "Get the status of a git repository",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        "git_log": {
            "description": "Get git log entries",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of entries to return (1-50)",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 10,
                    }
                },
                "required": [],
            },
        },
        "git_diff_stat": {
            "description": "Get git diff statistics",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        "rg_search": {
            "description": "Search files using ripgrep",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Search pattern (required, non-empty)",
                    },
                    "path": {
                        "type": "string",
                        "description": "Path to search in (optional, defaults to '.')",
                    },
                },
                "required": ["pattern"],
            },
        },
    }

    def __init__(self, root_dir: Optional[str] = None):
        """Initialize the server with an optional root directory."""
        self.root_dir = Path(root_dir) if root_dir else Path(".")
        self.request_id = None

    def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle a single JSON-RPC 2.0 request."""
        self.request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if method == "initialize":
            return self.initialize()
        elif method == "tools/list":
            return self.list_tools()
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            return self.call_tool(tool_name, arguments)
        else:
            return self.json_rpc_error(-32601, "Unknown method")

    def initialize(self) -> Dict[str, Any]:
        """Handle initialize request."""
        return {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "result": {
                "protocolVersion": self.PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "cli-tools",
                    "version": "1.0",
                },
            },
        }

    def list_tools(self) -> Dict[str, Any]:
        """Handle tools/list request."""
        tools = []
        for name, spec in self.TOOLS.items():
            tools.append({
                "name": name,
                "description": spec["description"],
                "inputSchema": spec["inputSchema"],
            })

        return {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "result": {
                "tools": tools,
            },
        }

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        if tool_name not in self.TOOLS:
            return self.json_rpc_error(-32602, f"Unknown tool: {tool_name}")

        if tool_name == "git_status":
            return self.git_status()
        elif tool_name == "git_log":
            limit = arguments.get("limit", 10)
            return self.git_log(limit)
        elif tool_name == "git_diff_stat":
            return self.git_diff_stat()
        elif tool_name == "rg_search":
            pattern = arguments.get("pattern", "")
            path = arguments.get("path", ".")
            return self.rg_search(pattern, path)
        else:
            return self.json_rpc_error(-32602, f"Unknown tool: {tool_name}")

    def git_status(self) -> Dict[str, Any]:
        """Execute git status."""
        try:
            output = self.run_command(["git", "status"], cwd=self.root_dir)
            return self.tool_result(output)
        except Exception as e:
            return self.tool_error(str(e))

    def git_log(self, limit: int) -> Dict[str, Any]:
        """Execute git log with limit."""
        try:
            cmd = ["git", "log", f"-{limit}"]
            output = self.run_command(cmd, cwd=self.root_dir)
            return self.tool_result(output)
        except Exception as e:
            return self.tool_error(str(e))

    def git_diff_stat(self) -> Dict[str, Any]:
        """Execute git diff --stat."""
        try:
            output = self.run_command(["git", "diff", "--stat"], cwd=self.root_dir)
            return self.tool_result(output)
        except Exception as e:
            return self.tool_error(str(e))

    def rg_search(self, pattern: str, path: str) -> Dict[str, Any]:
        """Execute ripgrep search."""
        if not pattern:
            return self.tool_error("Pattern is required and cannot be empty")

        # Resolve path relative to root
        try:
            resolved_path = self.resolve_path(path)
        except ValueError as e:
            return self.tool_error(str(e))

        try:
            cmd = [
                "rg",
                "--line-number",
                "--no-heading",
                "--color", "never",
                "--max-count", "50",
                "-e", pattern,
                "--", str(resolved_path),
            ]
            output = self.run_command(cmd, cwd=self.root_dir)
            return self.tool_result(output)
        except subprocess.CalledProcessError as e:
            if e.returncode == 1:
                # rg exit code 1 means no matches, which is success
                return self.tool_result("")
            return self.tool_error(f"Command failed: {e.stderr}")
        except Exception as e:
            return self.tool_error(str(e))

    def resolve_path(self, path: str) -> Path:
        """Resolve a path and ensure it's within root."""
        path_obj = Path(path)

        # If it's an absolute path, check if it's within root
        if path_obj.is_absolute():
            if not self.is_within_root(path_obj):
                raise ValueError(f"Path escapes root: {path}")
            return path_obj

        # For relative paths, resolve relative to root
        resolved = (self.root_dir / path_obj).resolve()

        # Check if resolved path is within root
        if not self.is_within_root(resolved):
            raise ValueError(f"Path escapes root: {path}")

        return resolved

    def is_within_root(self, path: Path) -> bool:
        """Check if a path is within the root directory."""
        try:
            path.resolve().relative_to(self.root_dir.resolve())
            return True
        except ValueError:
            return False

    def run_command(self, cmd: list, cwd: Optional[Path] = None, timeout: int = TIMEOUT) -> str:
        """Run a command and return output, with timeout and truncation."""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            output = result.stdout or result.stderr

            # Truncate output at MAX_OUTPUT characters
            if len(output) > self.MAX_OUTPUT:
                output = output[:self.MAX_OUTPUT] + "[truncated]"

            if result.returncode != 0 and result.returncode != 1:
                raise subprocess.CalledProcessError(
                    result.returncode, cmd, output=output, stderr=result.stderr
                )

            return output
        except subprocess.TimeoutExpired:
            raise Exception("Command timed out")

    def tool_result(self, output: str) -> Dict[str, Any]:
        """Format a successful tool result."""
        return {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": output,
                    }
                ],
            },
        }

    def tool_error(self, message: str) -> Dict[str, Any]:
        """Format a tool error."""
        return {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "result": {
                "isError": True,
                "content": [
                    {
                        "type": "text",
                        "text": message,
                    }
                ],
            },
        }

    def json_rpc_error(self, code: int, message: str) -> Dict[str, Any]:
        """Format a JSON-RPC error response."""
        return {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "error": {
                "code": code,
                "message": message,
            },
        }


def main():
    """Main entry point for the server."""
    import argparse

    parser = argparse.ArgumentParser(description="MCP server for CLI tools")
    parser.add_argument("--root", default=".", help="Root directory for commands")
    args = parser.parse_args()

    server = MCPServer(root_dir=args.root)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
            # Only send a response if the request has an id (not a notification)
            if "id" in request:
                response = server.handle_request(request)
                if response:
                    print(json.dumps(response))
                    sys.stdout.flush()
            else:
                # Notification - handle it but don't send a response
                server.handle_request(request)
        except json.JSONDecodeError:
            # Parse error - skip invalid JSON without responding
            pass


if __name__ == "__main__":
    main()
