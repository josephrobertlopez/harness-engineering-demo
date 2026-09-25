"""Tests for security constraints."""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from server import MCPServer


class TestSecurity(unittest.TestCase):
    """Tests for shell injection prevention and write operation blocking."""

    def setUp(self):
        """Set up test fixtures."""
        self.server = MCPServer()

    @patch("server.subprocess.run")
    def test_pattern_starting_with_dash_is_searched_as_literal(self, mock_run):
        """Scenario: Pattern starting with dash is searched as literal"""
        # Mock ripgrep output showing the pattern was found
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="file.txt:1:-v match\n",
            stderr=""
        )

        response = self.server.call_tool("rg_search", {"pattern": "-v"})

        # Verify the command uses -e flag to treat pattern as literal
        call_args = mock_run.call_args[0][0]
        self.assertIn("-e", call_args)

        # Find the index of -e and verify -v comes after it
        e_index = call_args.index("-e")
        self.assertEqual(call_args[e_index + 1], "-v")

        # Verify result is successful
        self.assertIn("result", response)

    @patch("server.subprocess.run")
    def test_path_with_shell_metacharacters_is_literal(self, mock_run):
        """Scenario: Path with shell metacharacters is literal"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr=""
        )

        # Try to search in a path with shell metacharacters
        response = self.server.call_tool("rg_search", {
            "pattern": "test",
            "path": "foo;rm"
        })

        # Verify the command was called (not executed by shell)
        # The key is that it's passed as an argument, not through shell
        call_args = mock_run.call_args[0][0]

        # The path should be in the command as a separate argument (after --)
        self.assertIn("--", call_args)
        dash_index = call_args.index("--")
        path_arg = call_args[dash_index + 1]
        # Path should contain "foo;rm" as part of the resolved path
        self.assertIn("foo;rm", path_arg)

    def test_write_operations_are_not_exposed(self):
        """Scenario: Write operations are not exposed"""
        # Try to call git_commit (which doesn't exist)
        response = self.server.call_tool("git_commit", {})

        # Should return error -32602 for unknown tool
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32602)

        # Try git_checkout
        response = self.server.call_tool("git_checkout", {})
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32602)

        # Try git_push
        response = self.server.call_tool("git_push", {})
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32602)


if __name__ == "__main__":
    unittest.main()
