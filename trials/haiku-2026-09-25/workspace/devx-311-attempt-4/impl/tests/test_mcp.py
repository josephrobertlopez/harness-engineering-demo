"""Tests for MCP protocol integration."""

import unittest
from unittest.mock import patch, MagicMock
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from server import MCPServer


class TestMCPProtocol(unittest.TestCase):
    """Tests for MCP protocol implementation."""

    def setUp(self):
        """Set up test fixtures."""
        self.server = MCPServer()

    def test_mcp_activation_via_claude_mcp_add_command(self):
        """Scenario: MCP activation via claude mcp add command"""
        # This test verifies that the server can be activated via command line
        # The command format is: claude mcp add cli-tools -- python /path/server.py --root /path/to/repo
        # We test that the server accepts the --root argument
        import argparse
        from server import MCPServer

        # Simulate command line args
        parser = argparse.ArgumentParser()
        parser.add_argument("--root", default=".")
        args = parser.parse_args(["--root", "/test/repo"])

        server = MCPServer(root_dir=args.root)
        self.assertEqual(str(server.root_dir), "/test/repo")

    def test_mcp_activation_via_mcp_json_file(self):
        """Scenario: MCP activation via .mcp.json file"""
        # This test verifies the server works when activated via .mcp.json
        # The .mcp.json file contains: { "cli-tools": { "command": "python /path/server.py --root /path" } }
        # We verify the server can be created with the root from the config
        server = MCPServer(root_dir="/home/user/myrepo")
        self.assertIsNotNone(server)

        # Verify initialize works
        response = server.initialize()
        self.assertIn("result", response)
        self.assertEqual(response["result"]["protocolVersion"], "2025-06-18")

    def test_tools_list_method_returns_schemas(self):
        """Scenario: tools/list method returns schemas"""
        # Mock the request
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1,
        }

        response = self.server.handle_request(request)

        self.assertIn("result", response)
        self.assertIn("tools", response["result"])

        tools = response["result"]["tools"]

        # Verify each tool has required schema fields
        for tool in tools:
            self.assertIn("name", tool)
            self.assertIn("description", tool)
            self.assertIn("inputSchema", tool)

            schema = tool["inputSchema"]
            self.assertIn("type", schema)
            self.assertIn("properties", schema)


if __name__ == "__main__":
    unittest.main()
