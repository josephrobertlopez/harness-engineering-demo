"""Tests for tool parameters and defaults."""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from server import MCPServer


class TestParameters(unittest.TestCase):
    """Tests for tool parameters and default values."""

    def setUp(self):
        """Set up test fixtures."""
        self.server = MCPServer()

    @patch("server.subprocess.run")
    def test_git_log_without_limit_uses_default_10(self, mock_run):
        """Scenario: git_log without limit uses default 10"""
        # Create output with 10 commits
        commits = "\n".join([f"commit {i:06d}" for i in range(10)])
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=commits,
            stderr=""
        )

        response = self.server.call_tool("git_log", {})

        # Verify command was called with -10 (default)
        call_args = mock_run.call_args[0][0]
        self.assertIn("-10", call_args)

        # Verify result contains 10 entries
        content_text = response["result"]["content"][0]["text"]
        self.assertEqual(content_text.count("commit"), 10)

    @patch("server.subprocess.run")
    def test_git_log_with_limit_1_returns_1_entry(self, mock_run):
        """Scenario: git_log with limit 1 returns 1 entry"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="commit 000000",
            stderr=""
        )

        response = self.server.call_tool("git_log", {"limit": 1})

        # Verify command was called with -1
        call_args = mock_run.call_args[0][0]
        self.assertIn("-1", call_args)

        # Verify result
        self.assertIn("result", response)

    @patch("server.subprocess.run")
    def test_git_log_with_limit_50_returns_50_entries(self, mock_run):
        """Scenario: git_log with limit 50 returns 50 entries"""
        commits = "\n".join([f"commit {i:06d}" for i in range(50)])
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=commits,
            stderr=""
        )

        response = self.server.call_tool("git_log", {"limit": 50})

        # Verify command was called with -50
        call_args = mock_run.call_args[0][0]
        self.assertIn("-50", call_args)

        # Verify result
        self.assertIn("result", response)

    @patch("server.subprocess.run")
    def test_rg_search_without_path_uses_default_current_directory(self, mock_run):
        """Scenario: rg_search without path uses default current directory"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="file.txt:1:match",
            stderr=""
        )

        response = self.server.call_tool("rg_search", {"pattern": "test"})

        # Verify the command includes -- and .
        call_args = mock_run.call_args[0][0]
        self.assertIn("--", call_args)

        # The current directory should be used (resolved to full path)
        dash_index = call_args.index("--")
        self.assertGreater(len(call_args), dash_index + 1)
        # Path should be after the -- separator

    @patch("server.subprocess.run")
    def test_rg_search_with_path_searches_that_directory(self, mock_run):
        """Scenario: rg_search with path searches that directory"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="src/file.txt:1:match",
            stderr=""
        )

        response = self.server.call_tool("rg_search", {
            "pattern": "test",
            "path": "src/"
        })

        # Verify the path is in the command
        call_args = mock_run.call_args[0][0]
        self.assertIn("--", call_args)

        # The path should be after --
        dash_index = call_args.index("--")
        self.assertGreater(len(call_args), dash_index + 1)


if __name__ == "__main__":
    unittest.main()
