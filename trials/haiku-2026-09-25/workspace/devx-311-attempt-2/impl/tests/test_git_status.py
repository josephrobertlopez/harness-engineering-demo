"""Tests for git_status tool."""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import MCPServer


class TestGitStatus(unittest.TestCase):
    """Tests for git_status tool."""

    def setUp(self):
        """Set up test fixtures."""
        self.server = MCPServer("/tmp/test_repo")

    @patch('server.subprocess.run')
    def test_git_status_no_arguments(self, mock_run):
        """Scenario: git_status_no_arguments"""
        # Mock successful git status output
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="M  file.txt\n?? new_file.py\n",
            stderr=""
        )

        result = self.server.git_status()

        # Verify isError is False
        self.assertFalse(result["isError"])
        # Verify output is returned
        self.assertIn("output", result)
        # Verify the command was called correctly
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        self.assertEqual(call_args[0], "git")
        self.assertEqual(call_args[1], "status")
        self.assertEqual(call_args[2], "--porcelain=v1")
        self.assertEqual(call_args[3], "--branch")

    def test_git_status_with_arguments_fails(self):
        """Scenario: git_status_with_arguments_fails"""
        result = self.server.git_status(extra_arg="value")

        # Verify isError is True
        self.assertTrue(result["isError"])
        # Verify error message
        self.assertIn("reason", result)
        self.assertIn("no arguments", result["reason"])

    @patch('server.subprocess.run')
    def test_git_status_in_git_repo(self, mock_run):
        """Scenario: git_status_in_git_repo"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="## main\nM  file.txt\n",
            stderr=""
        )

        result = self.server.git_status()

        self.assertFalse(result["isError"])
        self.assertIn("##", result["output"])

    @patch('server.subprocess.run')
    def test_git_status_not_in_git_repo(self, mock_run):
        """Scenario: git_status_not_in_git_repo"""
        mock_run.return_value = MagicMock(
            returncode=128,
            stdout="",
            stderr="fatal: not a git repository"
        )

        result = self.server.git_status()

        self.assertTrue(result["isError"])
        self.assertIn("not a git repository", result["reason"])


if __name__ == "__main__":
    unittest.main()
