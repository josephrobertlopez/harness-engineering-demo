"""Tests for resource limits."""

import unittest
from unittest.mock import patch, MagicMock
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from server import MCPServer


class TestResourceLimits(unittest.TestCase):
    """Tests for timeout and output truncation limits."""

    def setUp(self):
        """Set up test fixtures."""
        self.server = MCPServer()

    @patch("server.subprocess.run")
    def test_command_timeout_after_10_seconds(self, mock_run):
        """Scenario: Command timeout after 10 seconds"""
        # Mock a timeout
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", timeout=10)

        response = self.server.call_tool("git_status", {})

        # Should return isError: true with timeout message
        self.assertIn("result", response)
        self.assertTrue(response["result"]["isError"])

        content_text = response["result"]["content"][0]["text"]
        self.assertIn("timed out", content_text.lower())

    @patch("server.subprocess.run")
    def test_output_truncated_when_exceeding_8000_characters(self, mock_run):
        """Scenario: Output truncated when exceeding 8000 characters"""
        # Create output longer than 8000 characters
        long_output = "a" * 9000
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=long_output,
            stderr=""
        )

        response = self.server.call_tool("git_log", {})

        content_text = response["result"]["content"][0]["text"]

        # Should be truncated to 8000 + "[truncated]" marker
        self.assertLessEqual(len(content_text), 8000 + len("[truncated]"))
        self.assertIn("[truncated]", content_text)

    @patch("server.subprocess.run")
    def test_output_exactly_8000_characters_returns_without_marker(self, mock_run):
        """Scenario: Output exactly 8000 characters returns without marker"""
        # Create output exactly 8000 characters
        exact_output = "a" * 8000
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=exact_output,
            stderr=""
        )

        response = self.server.call_tool("git_log", {})

        content_text = response["result"]["content"][0]["text"]

        # Should be exactly 8000 characters without marker
        self.assertEqual(len(content_text), 8000)
        self.assertNotIn("[truncated]", content_text)


if __name__ == "__main__":
    unittest.main()
