"""Comprehensive tests for all scenarios."""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import tempfile
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import MCPServer


class TestToolInvocation(unittest.TestCase):
    """Tests for tool invocation."""

    def setUp(self):
        self.server = MCPServer("/tmp/test_repo")

    @patch('server.subprocess.run')
    def test_tool_invocation_succeeds(self, mock_run):
        """Scenario: tool_invocation_succeeds"""
        mock_run.return_value = MagicMock(returncode=0, stdout="output", stderr="")

        result = self.server.git_status()

        self.assertFalse(result["isError"])

    def test_unknown_tool_rejected(self):
        """Scenario: unknown_tool_rejected"""
        response = self.server.handle_request({
            "method": "tools/call",
            "params": {"name": "nonexistent_tool"}
        })

        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32602)


class TestNoShellExecution(unittest.TestCase):
    """Tests for no shell execution."""

    def setUp(self):
        self.server = MCPServer("/tmp/test_repo")

    @patch('server.subprocess.run')
    def test_arguments_as_array(self, mock_run):
        """Scenario: arguments_as_array"""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        self.server.git_status()

        # Verify command is passed as array
        args = mock_run.call_args[0][0]
        self.assertIsInstance(args, list)

    @patch('server.subprocess.run')
    def test_shell_metacharacters_literal(self, mock_run):
        """Scenario: shell_metacharacters_literal"""
        mock_run.return_value = MagicMock(returncode=0, stdout="found", stderr="")

        # Pass a pattern with shell metacharacters
        self.server.rg_search(pattern="foo|bar", path=".")

        # Verify pattern is in args as literal
        args = mock_run.call_args[0][0]
        self.assertIn("foo|bar", args)


class TestReadOnly(unittest.TestCase):
    """Tests for read-only operations."""

    def setUp(self):
        self.server = MCPServer("/tmp/test_repo")

    @patch('server.subprocess.run')
    def test_git_operations_readonly(self, mock_run):
        """Scenario: git_operations_readonly"""
        mock_run.return_value = MagicMock(returncode=0, stdout="output", stderr="")

        self.server.git_status()
        self.server.git_log()
        self.server.git_diff_stat()

        # All commands should be git read-only commands
        for call in mock_run.call_args_list:
            cmd = call[0][0][0]
            self.assertEqual(cmd, "git")


class TestTimeout(unittest.TestCase):
    """Tests for timeout enforcement."""

    def setUp(self):
        self.server = MCPServer("/tmp/test_repo")

    @patch('server.subprocess.run')
    def test_command_completes_under_timeout(self, mock_run):
        """Scenario: command_completes_under_timeout"""
        mock_run.return_value = MagicMock(returncode=0, stdout="result", stderr="")

        result = self.server.git_status()

        self.assertFalse(result["isError"])
        # Verify timeout parameter was set
        self.assertEqual(mock_run.call_args[1]["timeout"], 10)

    @patch('server.subprocess.run')
    def test_command_timeout_10_seconds(self, mock_run):
        """Scenario: command_timeout_10_seconds"""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("git", 10)

        result = self.server.git_status()

        self.assertTrue(result["isError"])

    @patch('server.subprocess.run')
    def test_timeout_error_response(self, mock_run):
        """Scenario: timeout_error_response"""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("git", 10)

        result = self.server.git_status()

        self.assertTrue(result["isError"])
        self.assertIn("timeout", result["reason"].lower())


class TestOutputTruncation(unittest.TestCase):
    """Tests for output truncation."""

    def setUp(self):
        self.server = MCPServer("/tmp/test_repo")

    @patch('server.subprocess.run')
    def test_output_under_limit(self, mock_run):
        """Scenario: output_under_limit"""
        output = "x" * 1000
        mock_run.return_value = MagicMock(returncode=0, stdout=output, stderr="")

        result = self.server.git_status()

        self.assertEqual(result["output"], output)
        self.assertNotIn("[truncated]", result["output"])

    @patch('server.subprocess.run')
    def test_output_at_boundary(self, mock_run):
        """Scenario: output_at_boundary"""
        output = "x" * 8000
        mock_run.return_value = MagicMock(returncode=0, stdout=output, stderr="")

        result = self.server.git_status()

        self.assertEqual(result["output"], output)
        self.assertNotIn("[truncated]", result["output"])

    @patch('server.subprocess.run')
    def test_output_exceeds_limit(self, mock_run):
        """Scenario: output_exceeds_limit"""
        output = "x" * 8001
        mock_run.return_value = MagicMock(returncode=0, stdout=output, stderr="")

        result = self.server.git_status()

        self.assertEqual(len(result["output"]), 8011)  # 8000 + len("[truncated]")

    @patch('server.subprocess.run')
    def test_truncation_marker_appended(self, mock_run):
        """Scenario: truncation_marker_appended"""
        output = "x" * 9000
        mock_run.return_value = MagicMock(returncode=0, stdout=output, stderr="")

        result = self.server.git_status()

        self.assertTrue(result["output"].endswith("[truncated]"))


class TestPathIsolation(unittest.TestCase):
    """Tests for path isolation."""

    def setUp(self):
        self.server = MCPServer("/tmp/test_repo")

    @patch('server.subprocess.run')
    def test_path_within_root(self, mock_run):
        """Scenario: path_within_root"""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = self.server.rg_search(pattern="foo", path="subdir/file.py")

        self.assertFalse(result["isError"])

    def test_path_escape_parent_directory(self):
        """Scenario: path_escape_parent_directory"""
        result = self.server.rg_search(pattern="foo", path="../../../etc")

        self.assertTrue(result["isError"])
        self.assertIn("escapes", result["reason"])

    def test_absolute_path_rejected(self):
        """Scenario: absolute_path_rejected"""
        result = self.server.rg_search(pattern="foo", path="/etc/passwd")

        self.assertTrue(result["isError"])


class TestGitLog(unittest.TestCase):
    """Tests for git_log."""

    def setUp(self):
        self.server = MCPServer("/tmp/test_repo")

    @patch('server.subprocess.run')
    def test_git_log_default_limit(self, mock_run):
        """Scenario: git_log_default_limit"""
        mock_run.return_value = MagicMock(returncode=0, stdout="commits", stderr="")

        self.server.git_log()

        args = mock_run.call_args[0][0]
        self.assertIn("10", args)  # Default limit

    @patch('server.subprocess.run')
    def test_git_log_valid_limit_1(self, mock_run):
        """Scenario: git_log_valid_limit_1"""
        mock_run.return_value = MagicMock(returncode=0, stdout="1 commit", stderr="")

        result = self.server.git_log(limit=1)

        self.assertFalse(result["isError"])
        args = mock_run.call_args[0][0]
        self.assertIn("1", args)

    @patch('server.subprocess.run')
    def test_git_log_valid_limit_50(self, mock_run):
        """Scenario: git_log_valid_limit_50"""
        mock_run.return_value = MagicMock(returncode=0, stdout="50 commits", stderr="")

        result = self.server.git_log(limit=50)

        self.assertFalse(result["isError"])

    def test_git_log_invalid_limit_below_range(self):
        """Scenario: git_log_invalid_limit_below_range"""
        result = self.server.git_log(limit=0)

        self.assertTrue(result["isError"])
        self.assertIn("1", result["reason"])

    def test_git_log_invalid_limit_above_range(self):
        """Scenario: git_log_invalid_limit_above_range"""
        result = self.server.git_log(limit=51)

        self.assertTrue(result["isError"])
        self.assertIn("50", result["reason"])

    def test_git_log_non_integer_limit(self):
        """Scenario: git_log_non_integer_limit"""
        result = self.server.git_log(limit="ten")

        self.assertTrue(result["isError"])
        self.assertIn("integer", result["reason"])


class TestRgSearch(unittest.TestCase):
    """Tests for rg_search."""

    def setUp(self):
        self.server = MCPServer("/tmp/test_repo")

    @patch('server.subprocess.run')
    def test_rg_search_pattern_only(self, mock_run):
        """Scenario: rg_search_pattern_only"""
        mock_run.return_value = MagicMock(returncode=0, stdout="results", stderr="")

        result = self.server.rg_search(pattern="foo")

        self.assertFalse(result["isError"])
        args = mock_run.call_args[0][0]
        self.assertIn("-e", args)
        self.assertIn("foo", args)

    @patch('server.subprocess.run')
    def test_rg_search_pattern_and_path(self, mock_run):
        """Scenario: rg_search_pattern_and_path"""
        mock_run.return_value = MagicMock(returncode=0, stdout="results", stderr="")

        result = self.server.rg_search(pattern="foo", path="src")

        self.assertFalse(result["isError"])

    @patch('server.subprocess.run')
    def test_rg_search_pattern_with_dash(self, mock_run):
        """Scenario: rg_search_pattern_with_dash"""
        mock_run.return_value = MagicMock(returncode=0, stdout="results", stderr="")

        self.server.rg_search(pattern="-v")

        args = mock_run.call_args[0][0]
        self.assertIn("-v", args)

    @patch('server.subprocess.run')
    def test_rg_search_no_matches(self, mock_run):
        """Scenario: rg_search_no_matches"""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")

        result = self.server.rg_search(pattern="nonexistent")

        self.assertFalse(result["isError"])

    @patch('server.subprocess.run')
    def test_rg_search_with_matches(self, mock_run):
        """Scenario: rg_search_with_matches"""
        mock_run.return_value = MagicMock(returncode=0, stdout="file.py:10:match", stderr="")

        result = self.server.rg_search(pattern="foo")

        self.assertFalse(result["isError"])
        self.assertIn("file.py", result["output"])

    def test_rg_search_invalid_flags(self):
        """Scenario: rg_search_invalid_flags"""
        result = self.server.rg_search(pattern="foo", unknown_arg="value")

        self.assertTrue(result["isError"])


class TestErrorHandling(unittest.TestCase):
    """Tests for error handling."""

    def setUp(self):
        self.server = MCPServer("/tmp/test_repo")

    @patch('server.subprocess.run')
    def test_error_missing_binary(self, mock_run):
        """Scenario: error_missing_binary"""
        mock_run.side_effect = FileNotFoundError("git")

        result = self.server.git_status()

        self.assertTrue(result["isError"])
        self.assertIn("not found", result["reason"])

    def test_error_path_escape(self):
        """Scenario: error_path_escape"""
        result = self.server.rg_search(pattern="foo", path="../outside")

        self.assertTrue(result["isError"])
        self.assertIn("escapes", result["reason"])


class TestMCPProtocol(unittest.TestCase):
    """Tests for MCP protocol."""

    def setUp(self):
        self.server = MCPServer("/tmp/test_repo")

    def test_mcp_initialize_version(self):
        """Scenario: mcp_initialize_version"""
        response = self.server.handle_request({"method": "initialize"})

        self.assertEqual(response["protocolVersion"], "2025-06-18")

    def test_mcp_error_unknown_tool(self):
        """Scenario: mcp_error_unknown_tool"""
        response = self.server.handle_request({
            "method": "tools/call",
            "params": {"name": "unknown"}
        })

        self.assertEqual(response["error"]["code"], -32602)

    def test_mcp_error_unknown_method(self):
        """Scenario: mcp_error_unknown_method"""
        response = self.server.handle_request({"method": "unknown_method"})

        self.assertEqual(response["error"]["code"], -32601)


if __name__ == "__main__":
    unittest.main()
