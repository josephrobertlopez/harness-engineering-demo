"""Tests for tool exposure and execution."""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from server import MCPServer


class TestToolExposure(unittest.TestCase):
    """Tests for exposing the four CLI tools."""

    def setUp(self):
        """Set up test fixtures."""
        self.server = MCPServer()

    def test_tools_list_returns_exactly_four_tools(self):
        """Scenario: Tools list returns exactly four tools"""
        response = self.server.list_tools()

        self.assertIn("result", response)
        tools = response["result"]["tools"]

        # Must return exactly 4 tools
        self.assertEqual(len(tools), 4)

        # Tool names must be exactly these
        tool_names = {tool["name"] for tool in tools}
        expected = {"git_status", "git_log", "git_diff_stat", "rg_search"}
        self.assertEqual(tool_names, expected)

        # Each tool must have a schema
        for tool in tools:
            self.assertIn("inputSchema", tool)
            self.assertIn("description", tool)

    @patch("server.subprocess.run")
    def test_git_status_executes(self, mock_run):
        """Scenario: git_status executes"""
        # Mock successful git status output
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="On branch main\n",
            stderr=""
        )

        response = self.server.call_tool("git_status", {})

        self.assertIn("result", response)
        self.assertIn("content", response["result"])
        self.assertGreater(len(response["result"]["content"]), 0)

        # Verify git was called
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        self.assertIn("git", call_args)
        self.assertIn("status", call_args)

    @patch("server.subprocess.run")
    def test_git_log_executes_with_limit_parameter(self, mock_run):
        """Scenario: git_log executes with limit parameter"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="commit abc123\n",
            stderr=""
        )

        response = self.server.call_tool("git_log", {"limit": 5})

        self.assertIn("result", response)
        self.assertIn("content", response["result"])

        # Verify git log was called with limit
        call_args = mock_run.call_args[0][0]
        self.assertIn("git", call_args)
        self.assertIn("log", call_args)
        self.assertIn("-5", call_args)

    @patch("server.subprocess.run")
    def test_git_diff_stat_executes(self, mock_run):
        """Scenario: git_diff_stat executes"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="file.txt | 1 +\n",
            stderr=""
        )

        response = self.server.call_tool("git_diff_stat", {})

        self.assertIn("result", response)
        self.assertIn("content", response["result"])

        # Verify git diff --stat was called
        call_args = mock_run.call_args[0][0]
        self.assertIn("git", call_args)
        self.assertIn("diff", call_args)
        self.assertIn("--stat", call_args)

    @patch("server.subprocess.run")
    def test_rg_search_executes_with_pattern(self, mock_run):
        """Scenario: rg_search executes with pattern"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="file.txt:1:pattern found\n",
            stderr=""
        )

        response = self.server.call_tool("rg_search", {"pattern": "test"})

        self.assertIn("result", response)
        self.assertIn("content", response["result"])

        # Verify rg was called with pattern
        call_args = mock_run.call_args[0][0]
        self.assertIn("rg", call_args)
        self.assertIn("-e", call_args)
        self.assertIn("test", call_args)

    def test_unknown_tool_returns_error(self):
        """Scenario: Unknown tool returns error -32602"""
        response = self.server.call_tool("unknown_tool", {})

        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32602)


if __name__ == "__main__":
    unittest.main()
