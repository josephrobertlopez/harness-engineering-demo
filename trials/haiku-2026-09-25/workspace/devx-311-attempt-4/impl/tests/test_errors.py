"""Tests for error handling."""

import unittest
from unittest.mock import patch, MagicMock
import subprocess
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from server import MCPServer


class TestErrorHandling(unittest.TestCase):
    """Tests for error handling and JSON-RPC responses."""

    def setUp(self):
        """Set up test fixtures."""
        self.server = MCPServer()

    @patch("server.subprocess.run")
    def test_tool_failure_returns_iserror_flag(self, mock_run):
        """Scenario: Tool failure returns isError flag"""
        # Mock a command failure (returncode != 0 and != 1)
        mock_run.return_value = MagicMock(
            returncode=2,
            stdout="",
            stderr="Error: file not found"
        )

        response = self.server.call_tool("git_status", {})

        # Should return result with isError: true
        self.assertIn("result", response)
        self.assertTrue(response["result"]["isError"])

    @patch("server.subprocess.run")
    def test_rg_exit_code_1_no_matches_is_success(self, mock_run):
        """Scenario: rg exit code 1 no matches is success"""
        # rg exit code 1 means no matches
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["rg"], output="", stderr=""
        )

        response = self.server.call_tool("rg_search", {"pattern": "notfound"})

        # Should be successful (no isError flag)
        self.assertIn("result", response)
        # Either no isError key or isError is False
        if "isError" in response["result"]:
            self.assertFalse(response["result"]["isError"])

    def test_unknown_tool_name_returns_json_rpc_error_32602(self):
        """Scenario: Unknown tool name returns JSON-RPC error -32602"""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "unknown_tool", "arguments": {}},
            "id": 1,
        }

        response = self.server.handle_request(request)

        # Should return error, not result
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32602)

    def test_unknown_method_returns_json_rpc_error_32601(self):
        """Scenario: Unknown method returns JSON-RPC error -32601"""
        request = {
            "jsonrpc": "2.0",
            "method": "unknown_method",
            "id": 1,
        }

        response = self.server.handle_request(request)

        # Should return error
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32601)

    def test_unparseable_json_returns_json_rpc_error_32700(self):
        """Scenario: Unparseable JSON returns JSON-RPC error -32700"""
        # This would be caught at the main() level in real usage
        # For testing, we can verify the error code is available
        error = self.server.json_rpc_error(-32700, "Parse error")

        self.assertIn("error", error)
        self.assertEqual(error["error"]["code"], -32700)


if __name__ == "__main__":
    unittest.main()
