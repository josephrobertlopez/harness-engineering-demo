"""MCP server for git and ripgrep (rg) commands."""

import json
import sys
import subprocess
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


class CLIMCPServer:
    """MCP server exposing git and ripgrep tools."""

    PROTOCOL_VERSION = "2025-06-18"
    AVAILABLE_TOOLS = {"git_status", "git_log", "git_diff_stat", "rg_search"}

    def __init__(self, root: str):
        """Initialize server with root directory."""
        self.root = Path(root).resolve()
        self.request_id = None

    def validate_path(self, path: str) -> Tuple[bool, Optional[str]]:
        """Validate that a path is within root directory."""
        try:
            full_path = (self.root / path).resolve()
            # Check if the resolved path is within root
            full_path.relative_to(self.root)
            return True, None
        except (ValueError, RuntimeError):
            return False, "path escapes the root"

    def execute_command(self, args: list, timeout: int = 10) -> Tuple[int, str]:
        """Execute a command with timeout."""
        try:
            result = subprocess.run(
                args,
                cwd=str(self.root),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout
        except subprocess.TimeoutExpired:
            return -1, ""  # Timeout
        except Exception as e:
            return -1, str(e)

    def tool_git_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute git status."""
        returncode, output = self.execute_command(["git", "status"])
        if returncode != 0:
            return {"isError": True, "reason": output or "git status failed"}
        return {"output": output}

    def tool_git_log(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute git log with limit parameter."""
        limit = params.get("limit", 10)

        # Validate limit
        if not isinstance(limit, int) or limit < 1 or limit > 50:
            return {"isError": True, "reason": "limit must be an integer between 1 and 50"}

        returncode, output = self.execute_command(["git", "log", "--oneline", "-n", str(limit)])
        if returncode != 0:
            return {"isError": True, "reason": output or "git log failed"}
        return {"output": output}

    def tool_git_diff_stat(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute git diff --stat."""
        returncode, output = self.execute_command(["git", "diff", "--stat"])
        if returncode != 0:
            return {"isError": True, "reason": output or "git diff --stat failed"}
        return {"output": output}

    def tool_rg_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute ripgrep search."""
        pattern = params.get("pattern")
        path = params.get("path", ".")

        # Validate pattern
        if not pattern or not isinstance(pattern, str) or len(pattern) == 0:
            return {"isError": True, "reason": "pattern is required and must be a non-empty string"}

        # Validate path
        if not isinstance(path, str):
            return {"isError": True, "reason": "path must be a string"}

        # Check if path escapes root
        valid, error = self.validate_path(path)
        if not valid:
            return {"isError": True, "reason": error}

        returncode, output = self.execute_command(
            ["rg", "--line-number", "--no-heading", "--color", "never", "--max-count", "50", "-e", pattern, "--", path]
        )

        # ripgrep exit code 1 means no matches found, which is success
        if returncode == 1:
            return {"output": ""}
        elif returncode != 0:
            return {"isError": True, "reason": output or "rg search failed"}

        return {"output": output}

    def invoke_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a tool by name."""
        if tool_name not in self.AVAILABLE_TOOLS:
            return {"error": {"code": -32602, "message": f"Unknown tool: {tool_name}"}}

        tool_method = getattr(self, f"tool_{tool_name}", None)
        if tool_method is None:
            return {"error": {"code": -32602, "message": f"Unknown tool: {tool_name}"}}

        result = tool_method(params)

        # Truncate output to 8000 characters
        if "output" in result and result["output"]:
            output = result["output"]
            if len(output) > 8000:
                result["output"] = output[:8000] + "[truncated]"

        return result

    def handle_jsonrpc_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a JSON-RPC 2.0 request."""
        self.request_id = request.get("id")

        method = request.get("method")
        params = request.get("params", {})

        # For now, we only handle tool invocation via a special method
        # In real MCP, this would be tools/call
        if method == "tools/call":
            tool_name = params.get("name")
            tool_params = params.get("arguments", {})

            result = self.invoke_tool(tool_name, tool_params)

            if "error" in result:
                return {
                    "jsonrpc": "2.0",
                    "error": result["error"],
                    "id": self.request_id
                }
            else:
                return {
                    "jsonrpc": "2.0",
                    "result": result,
                    "id": self.request_id
                }

        # Unknown method
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32601, "message": "Method not found"},
            "id": self.request_id
        }

    def process_line(self, line: str) -> Optional[str]:
        """Process a single JSON-RPC line."""
        try:
            request = json.loads(line)
            response = self.handle_jsonrpc_request(request)
            return json.dumps(response)
        except json.JSONDecodeError:
            return json.dumps({
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "Parse error"},
                "id": None
            })

    def run(self):
        """Run the server, reading from stdin and writing to stdout."""
        for line in sys.stdin:
            line = line.rstrip('\n')
            if line:
                response = self.process_line(line)
                if response:
                    print(response)


def main():
    """Entry point for the server."""
    import argparse
    parser = argparse.ArgumentParser(description="MCP server for git and ripgrep")
    parser.add_argument("--root", required=True, help="Root directory for operations")
    args = parser.parse_args()

    server = CLIMCPServer(args.root)
    server.run()


if __name__ == "__main__":
    main()
