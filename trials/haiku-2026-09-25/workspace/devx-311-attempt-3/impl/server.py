"""
MCP server for CLI access (git and ripgrep).
Implements the protocol specified in the DEVX-311 specification.
"""

import subprocess
import json
import sys
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


class ToolRegistry:
    """Registry of available MCP tools."""

    def __init__(self):
        self.tools = {
            'git_status': {
                'name': 'git_status',
                'description': 'Show git repository status',
                'inputSchema': {
                    'type': 'object',
                    'properties': {},
                    'required': []
                }
            },
            'git_log': {
                'name': 'git_log',
                'description': 'Show git commit log',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'limit': {
                            'type': 'integer',
                            'minimum': 1,
                            'maximum': 50,
                            'description': 'Number of commits to return (1-50, default 10)'
                        }
                    },
                    'required': []
                }
            },
            'git_diff_stat': {
                'name': 'git_diff_stat',
                'description': 'Show git diff statistics',
                'inputSchema': {
                    'type': 'object',
                    'properties': {},
                    'required': []
                }
            },
            'rg_search': {
                'name': 'rg_search',
                'description': 'Search files using ripgrep',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'pattern': {
                            'type': 'string',
                            'description': 'Search pattern (required, non-empty)'
                        },
                        'path': {
                            'type': 'string',
                            'description': 'Path to search in (optional, default: .)'
                        }
                    },
                    'required': ['pattern']
                }
            }
        }

    def list_tools(self) -> List[Dict[str, Any]]:
        """Return list of available tools."""
        return list(self.tools.values())

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """Get tool by name."""
        return self.tools.get(name)


class MCPServer:
    """MCP server for CLI tools."""

    PROTOCOL_VERSION = '2025-06-18'
    TIMEOUT = 10  # seconds
    MAX_OUTPUT = 8000  # characters

    def __init__(self, root_dir: str, registry: ToolRegistry):
        """Initialize MCP server.

        Args:
            root_dir: Root directory for all operations
            registry: Tool registry
        """
        self.root_dir = root_dir
        self.registry = registry

    def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools."""
        return self.registry.list_tools()

    def _validate_path(self, path: str) -> bool:
        """Validate that a path stays within root directory.

        Args:
            path: Path to validate

        Returns:
            True if path is within root, False otherwise
        """
        try:
            root_path = Path(self.root_dir).resolve()
            full_path = (root_path / path).resolve()

            # Check if the resolved path is within root
            return str(full_path).startswith(str(root_path))
        except (ValueError, RuntimeError):
            return False

    def _truncate_output(self, output: str, marker: str = '[truncated]') -> str:
        """Truncate output to MAX_OUTPUT characters.

        Args:
            output: Output string to truncate
            marker: Marker to append if truncated

        Returns:
            Truncated output with marker if needed
        """
        if len(output) > self.MAX_OUTPUT:
            return output[:self.MAX_OUTPUT] + marker
        return output

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments

        Returns:
            Tool result or error
        """
        tool = self.registry.get_tool(tool_name)
        if not tool:
            return {
                'error': {
                    'code': -32602,
                    'message': f'Unknown tool: {tool_name}'
                }
            }

        try:
            if tool_name == 'git_status':
                return self._call_git_status(arguments)
            elif tool_name == 'git_log':
                return self._call_git_log(arguments)
            elif tool_name == 'git_diff_stat':
                return self._call_git_diff_stat(arguments)
            elif tool_name == 'rg_search':
                return self._call_rg_search(arguments)
            else:
                return {
                    'error': {
                        'code': -32602,
                        'message': f'Unknown tool: {tool_name}'
                    }
                }
        except Exception as e:
            return {
                'isError': True,
                'reason': str(e)
            }

    def _call_git_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call git status."""
        try:
            result = subprocess.run(
                ['git', '-C', self.root_dir, 'status'],
                capture_output=True,
                text=True,
                timeout=self.TIMEOUT
            )

            if result.returncode != 0:
                return {
                    'isError': True,
                    'reason': self._truncate_output(result.stderr or result.stdout)
                }

            return {
                'result': {
                    'output': self._truncate_output(result.stdout)
                }
            }
        except subprocess.TimeoutExpired:
            return {
                'isError': True,
                'reason': f'Command timed out after {self.TIMEOUT} seconds'
            }

    def _call_git_log(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call git log."""
        limit = arguments.get('limit', 10)

        # Validate limit parameter
        if not isinstance(limit, int) or limit < 1 or limit > 50:
            return {
                'isError': True,
                'reason': 'limit must be an integer between 1 and 50'
            }

        try:
            result = subprocess.run(
                ['git', '-C', self.root_dir, 'log', f'-{limit}'],
                capture_output=True,
                text=True,
                timeout=self.TIMEOUT
            )

            if result.returncode != 0:
                return {
                    'isError': True,
                    'reason': self._truncate_output(result.stderr or result.stdout)
                }

            return {
                'result': {
                    'output': self._truncate_output(result.stdout)
                }
            }
        except subprocess.TimeoutExpired:
            return {
                'isError': True,
                'reason': f'Command timed out after {self.TIMEOUT} seconds'
            }

    def _call_git_diff_stat(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call git diff --stat."""
        try:
            result = subprocess.run(
                ['git', '-C', self.root_dir, 'diff', '--stat'],
                capture_output=True,
                text=True,
                timeout=self.TIMEOUT
            )

            if result.returncode != 0:
                return {
                    'isError': True,
                    'reason': self._truncate_output(result.stderr or result.stdout)
                }

            return {
                'result': {
                    'output': self._truncate_output(result.stdout)
                }
            }
        except subprocess.TimeoutExpired:
            return {
                'isError': True,
                'reason': f'Command timed out after {self.TIMEOUT} seconds'
            }

    def _call_rg_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call ripgrep search."""
        pattern = arguments.get('pattern')
        path = arguments.get('path', '.')

        # Validate pattern
        if not pattern or not isinstance(pattern, str) or pattern.strip() == '':
            return {
                'isError': True,
                'reason': 'pattern must be a non-empty string'
            }

        # Validate path
        if not self._validate_path(path):
            return {
                'isError': True,
                'reason': f'path "{path}" escapes the root directory'
            }

        try:
            # Build command: rg --line-number --no-heading --color never --max-count 50 -e <pattern> -- <path>
            cmd = [
                'rg',
                '--line-number',
                '--no-heading',
                '--color', 'never',
                '--max-count', '50',
                '-e', pattern,
                '--',
                path
            ]

            result = subprocess.run(
                cmd,
                cwd=self.root_dir,
                capture_output=True,
                text=True,
                timeout=self.TIMEOUT
            )

            # Exit code 1 from rg means "no matches found" - this is success
            if result.returncode == 1:
                return {
                    'result': {
                        'output': ''  # No matches
                    }
                }

            if result.returncode != 0:
                return {
                    'isError': True,
                    'reason': self._truncate_output(result.stderr or result.stdout)
                }

            return {
                'result': {
                    'output': self._truncate_output(result.stdout)
                }
            }
        except subprocess.TimeoutExpired:
            return {
                'isError': True,
                'reason': f'Command timed out after {self.TIMEOUT} seconds'
            }


class MCPServerProtocol:
    """MCP protocol handler for stdio communication."""

    def __init__(self, server: MCPServer):
        self.server = server

    def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an incoming MCP message.

        Args:
            message: JSON-RPC message

        Returns:
            JSON-RPC response
        """
        method = message.get('method')
        params = message.get('params', {})
        message_id = message.get('id')

        response = {
            'jsonrpc': '2.0',
        }

        if message_id is not None:
            response['id'] = message_id

        try:
            if method == 'initialize':
                response['result'] = {
                    'protocolVersion': MCPServer.PROTOCOL_VERSION,
                    'implementation': 'cli-tools-mcp',
                    'version': '1.0.0',
                    'serverInfo': {
                        'name': 'CLI Tools MCP',
                        'version': '1.0.0'
                    },
                    'tools': self.server.list_tools()
                }
            elif method == 'ping':
                response['result'] = {}
            elif method == 'tools/list':
                response['result'] = {
                    'tools': self.server.list_tools()
                }
            elif method == 'tools/call':
                tool_name = params.get('name')
                arguments = params.get('arguments', {})
                tool_result = self.server.call_tool(tool_name, arguments)
                # If tool returned an error dict with code, return as error
                if isinstance(tool_result, dict) and 'error' in tool_result and 'code' in tool_result.get('error', {}):
                    response['error'] = tool_result['error']
                else:
                    response['result'] = tool_result
            else:
                response['error'] = {
                    'code': -32601,
                    'message': f'Unknown method: {method}'
                }
        except Exception as e:
            response['error'] = {
                'code': -32603,
                'message': str(e)
            }

        return response

    def run(self):
        """Run the server, reading from stdin and writing to stdout."""
        for line in sys.stdin:
            try:
                message = json.loads(line)
                response = self.handle_message(message)

                # Don't respond to notifications (no id)
                if 'id' in message:
                    print(json.dumps(response))
                    sys.stdout.flush()
            except json.JSONDecodeError:
                # Invalid JSON
                response = {
                    'jsonrpc': '2.0',
                    'error': {
                        'code': -32700,
                        'message': 'Parse error'
                    }
                }
                print(json.dumps(response))
                sys.stdout.flush()
            except Exception as e:
                response = {
                    'jsonrpc': '2.0',
                    'error': {
                        'code': -32603,
                        'message': str(e)
                    }
                }
                print(json.dumps(response))
                sys.stdout.flush()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='CLI Tools MCP Server')
    parser.add_argument('--root', required=True, help='Root directory for operations')
    args = parser.parse_args()

    registry = ToolRegistry()
    server = MCPServer(root_dir=args.root, registry=registry)
    protocol = MCPServerProtocol(server)
    protocol.run()
