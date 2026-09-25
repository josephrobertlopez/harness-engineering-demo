"""Tests for ripgrep invocation specifics."""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from server import MCPServer


class TestRipgrepInvocation(unittest.TestCase):
    """Tests for ripgrep command invocation."""

    def setUp(self):
        """Set up test fixtures."""
        self.server = MCPServer()

    @patch("server.subprocess.run")
    def test_pattern_passed_with_e_flag(self, mock_run):
        """Scenario: Pattern passed with -e flag"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="match",
            stderr=""
        )

        response = self.server.call_tool("rg_search", {"pattern": "test"})

        # Verify -e flag is used before the pattern
        call_args = mock_run.call_args[0][0]
        self.assertIn("-e", call_args)
        e_index = call_args.index("-e")
        self.assertEqual(call_args[e_index + 1], "test")

    @patch("server.subprocess.run")
    def test_dash_separator_before_path_prevents_option_interpretation(self, mock_run):
        """Scenario: Dash separator before path prevents option interpretation"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr=""
        )

        response = self.server.call_tool("rg_search", {
            "pattern": "test",
            "path": "."
        })

        # Verify -- separator is present before the path
        call_args = mock_run.call_args[0][0]
        self.assertIn("--", call_args)
        dash_index = call_args.index("--")
        # Path should be after the -- separator
        self.assertGreater(len(call_args), dash_index + 1)

    @patch("server.subprocess.run")
    def test_rg_search_invokes_ripgrep_with_e_flag_for_dash_patterns(self, mock_run):
        """Scenario: rg_search invokes ripgrep with -e flag for dash patterns"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="file:1:-v match",
            stderr=""
        )

        response = self.server.call_tool("rg_search", {"pattern": "-v"})

        # Verify the command uses -e to ensure -v is treated as a pattern
        call_args = mock_run.call_args[0][0]
        self.assertIn("-e", call_args)

        # Verify -v comes after -e
        e_index = call_args.index("-e")
        self.assertEqual(call_args[e_index + 1], "-v")


if __name__ == "__main__":
    unittest.main()
