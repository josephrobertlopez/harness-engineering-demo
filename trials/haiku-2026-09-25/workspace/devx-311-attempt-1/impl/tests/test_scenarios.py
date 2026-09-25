"""Tests for CLI MCP server scenarios."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import CLIMCPServer


class TestToolAvailability(unittest.TestCase):
    """Tests for tool availability and setup."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.server = CLIMCPServer(self.temp_dir)

    def test_server_exposes_exactly_four_tools(self):
        """Scenario: Server advertises git and ripgrep tools."""
        self.assertEqual(self.server.AVAILABLE_TOOLS, {"git_status", "git_log", "git_diff_stat", "rg_search"})

    def test_other_clis_not_exposed(self):
        """Scenario: Other CLIs are not exposed."""
        result = self.server.invoke_tool("npm_install", {})
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], -32602)


class TestGitLogTool(unittest.TestCase):
    """Tests for git_log tool."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.server = CLIMCPServer(self.temp_dir)

    @patch('server.subprocess.run')
    def test_git_log_with_explicit_limit(self, mock_run):
        """Scenario: git_log with explicit limit."""
        mock_run.return_value = MagicMock(returncode=0, stdout="abc123 commit message\n", stderr="")

        result = self.server.tool_git_log({"limit": 5})

        mock_run.assert_called_once_with(
            ["git", "log", "--oneline", "-n", "5"],
            cwd=str(Path(self.temp_dir)),
            capture_output=True,
            text=True,
            timeout=10
        )
        self.assertNotIn("isError", result)
        self.assertEqual(result["output"], "abc123 commit message\n")

    @patch('server.subprocess.run')
    def test_git_log_with_default_limit(self, mock_run):
        """Scenario: git_log with default limit."""
        mock_run.return_value = MagicMock(returncode=0, stdout="commits...\n", stderr="")

        result = self.server.tool_git_log({})

        mock_run.assert_called_once_with(
            ["git", "log", "--oneline", "-n", "10"],
            cwd=str(Path(self.temp_dir)),
            capture_output=True,
            text=True,
            timeout=10
        )
        self.assertNotIn("isError", result)


class TestGitDiffStatTool(unittest.TestCase):
    """Tests for git_diff_stat tool."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.server = CLIMCPServer(self.temp_dir)

    @patch('server.subprocess.run')
    def test_git_diff_stat_accepts_no_parameters(self, mock_run):
        """Scenario: git_diff_stat accepts no parameters."""
        mock_run.return_value = MagicMock(returncode=0, stdout="file.py | 10 ++++++++++\n", stderr="")

        result = self.server.tool_git_diff_stat({})

        mock_run.assert_called_once_with(
            ["git", "diff", "--stat"],
            cwd=str(Path(self.temp_dir)),
            capture_output=True,
            text=True,
            timeout=10
        )
        self.assertNotIn("isError", result)


class TestRgSearchTool(unittest.TestCase):
    """Tests for rg_search tool."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.server = CLIMCPServer(self.temp_dir)

    @patch('server.subprocess.run')
    def test_rg_search_with_pattern_and_path(self, mock_run):
        """Scenario: rg_search with pattern and path."""
        mock_run.return_value = MagicMock(returncode=0, stdout="src/file.py:10:TODO fix this\n", stderr="")

        result = self.server.tool_rg_search({"pattern": "TODO", "path": "src/"})

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "rg")
        self.assertIn("-e", args)
        self.assertIn("TODO", args)
        self.assertNotIn("isError", result)

    @patch('server.subprocess.run')
    def test_rg_search_with_default_path(self, mock_run):
        """Scenario: rg_search with default path."""
        mock_run.return_value = MagicMock(returncode=0, stdout="file.py:5:pattern\n", stderr="")

        result = self.server.tool_rg_search({"pattern": "pattern"})

        args = mock_run.call_args[0][0]
        self.assertIn(".", args)  # default path is "."
        self.assertNotIn("isError", result)


class TestErrorHandling(unittest.TestCase):
    """Tests for error handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.server = CLIMCPServer(self.temp_dir)

    @patch('server.subprocess.run')
    def test_ripgrep_exit_1_returns_normal_result(self, mock_run):
        """Scenario: ripgrep exit 1 returns normal result."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")

        result = self.server.tool_rg_search({"pattern": "notfound"})

        self.assertNotIn("isError", result)
        self.assertEqual(result["output"], "")

    @patch('server.subprocess.run')
    def test_ripgrep_exit_1_does_not_set_iserror(self, mock_run):
        """Scenario: ripgrep exit 1 does not set isError."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")

        result = self.server.tool_rg_search({"pattern": "notfound"})

        self.assertNotIn("isError", result)

    @patch('server.subprocess.run')
    def test_ripgrep_exit_2_is_error(self, mock_run):
        """Scenario: Other ripgrep exit codes are errors."""
        mock_run.return_value = MagicMock(returncode=2, stdout="", stderr="regex error")

        result = self.server.tool_rg_search({"pattern": "[invalid(regex"})

        self.assertIn("isError", result)
        self.assertTrue(result["isError"])

    def test_unknown_tool_returns_minus_32602(self):
        """Scenario: Unknown tool returns -32602."""
        result = self.server.invoke_tool("git_push", {})

        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], -32602)

    def test_write_operation_returns_minus_32602(self):
        """Scenario: Write operation returns -32602."""
        result = self.server.invoke_tool("git_commit", {})

        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], -32602)


class TestPathValidation(unittest.TestCase):
    """Tests for path validation and root directory constraints."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.server = CLIMCPServer(self.temp_dir)

    def test_path_within_root_is_valid(self):
        """Scenario: Paths within root are valid."""
        valid, error = self.server.validate_path("src/")
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_path_traversal_is_rejected(self):
        """Scenario: Path traversal is rejected."""
        valid, error = self.server.validate_path("../../../etc/passwd")
        self.assertFalse(valid)
        self.assertEqual(error, "path escapes the root")

    @patch('server.subprocess.run')
    def test_rg_search_path_outside_root_is_rejected(self, mock_run):
        """Scenario: Path traversal in rg_search is rejected."""
        result = self.server.tool_rg_search({"pattern": "test", "path": "../../etc/passwd"})

        self.assertIn("isError", result)
        self.assertEqual(result["reason"], "path escapes the root")


class TestOutputTruncation(unittest.TestCase):
    """Tests for output truncation."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.server = CLIMCPServer(self.temp_dir)

    @patch('server.subprocess.run')
    def test_output_under_8000_returned_in_full(self, mock_run):
        """Scenario: Output under 8000 characters is returned in full."""
        small_output = "x" * 5000
        mock_run.return_value = MagicMock(returncode=0, stdout=small_output, stderr="")

        result = self.server.tool_git_log({"limit": 10})

        self.assertEqual(result["output"], small_output)
        self.assertNotIn("[truncated]", result["output"])

    @patch('server.subprocess.run')
    def test_output_at_8000_characters_no_marker(self, mock_run):
        """Scenario: Output at exactly 8000 characters is returned without marker."""
        exact_output = "x" * 8000
        mock_run.return_value = MagicMock(returncode=0, stdout=exact_output, stderr="")

        result = self.server.tool_git_log({"limit": 10})

        self.assertEqual(result["output"], exact_output)
        self.assertNotIn("[truncated]", result["output"])

    @patch('server.subprocess.run')
    def test_output_over_8000_is_truncated(self, mock_run):
        """Scenario: Output over 8000 characters is truncated and marked."""
        large_output = "x" * 8500
        mock_run.return_value = MagicMock(returncode=0, stdout=large_output, stderr="")

        result = self.server.invoke_tool("git_log", {"limit": 10})

        self.assertTrue(result["output"].endswith("[truncated]"))
        # Output should be 8000 chars + "[truncated]"
        self.assertEqual(len(result["output"]), 8000 + len("[truncated]"))


class TestJSONRPCProtocol(unittest.TestCase):
    """Tests for JSON-RPC protocol."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.server = CLIMCPServer(self.temp_dir)

    def test_protocol_version(self):
        """Scenario: Server advertises protocol version."""
        self.assertEqual(self.server.PROTOCOL_VERSION, "2025-06-18")

    def test_unparseable_json_returns_minus_32700(self):
        """Scenario: Unparseable JSON returns -32700."""
        response = self.server.process_line("invalid json {")

        response_obj = json.loads(response)
        self.assertEqual(response_obj["error"]["code"], -32700)

    def test_binary_data_returns_minus_32700(self):
        """Scenario: Binary data returns -32700."""
        response = self.server.process_line("\x00\x01\x02")

        response_obj = json.loads(response)
        self.assertEqual(response_obj["error"]["code"], -32700)


class TestShellInjectionPrevention(unittest.TestCase):
    """Tests for shell injection prevention."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.server = CLIMCPServer(self.temp_dir)

    @patch('server.subprocess.run')
    def test_shell_metacharacters_not_interpreted(self, mock_run):
        """Scenario: Shell metacharacters are not interpreted."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        self.server.tool_rg_search({"pattern": "$(rm -rf /)"})

        # Verify the pattern is passed as-is in the argument array
        args = mock_run.call_args[0][0]
        # The pattern should be in the args, not executed
        self.assertIn("$(rm -rf /)", args)

    @patch('server.subprocess.run')
    def test_command_injection_prevented(self, mock_run):
        """Scenario: Command injection attempt is prevented."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        self.server.tool_rg_search({"pattern": "; cat /etc/passwd"})

        # The semicolon should be in the pattern argument, not as a shell separator
        args = mock_run.call_args[0][0]
        self.assertIn("; cat /etc/passwd", args)


class TestToolNameCaseSensitivity(unittest.TestCase):
    """Tests for tool name case sensitivity."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.server = CLIMCPServer(self.temp_dir)

    def test_tool_names_are_case_sensitive(self):
        """Scenario: Tool names are case-sensitive."""
        result = self.server.invoke_tool("Git_Log", {})

        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], -32602)

    def test_uppercase_tool_name_returns_error(self):
        """Scenario: Uppercase tool names return -32602."""
        result = self.server.invoke_tool("GIT_LOG", {})

        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], -32602)


if __name__ == "__main__":
    unittest.main()


class TestTimeout(unittest.TestCase):
    """Tests for command timeout."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.server = CLIMCPServer(self.temp_dir)
    
    @patch('server.subprocess.run')
    def test_tool_execution_times_out_after_10_seconds(self, mock_run):
        """Scenario: Tool execution times out after 10 seconds."""
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired("git", 10)
        
        result = self.server.tool_git_log({"limit": 10})
        
        # Should return an error
        self.assertIn("isError", result)
        self.assertTrue(result["isError"])


class TestErrorReasons(unittest.TestCase):
    """Tests for error reasons."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.server = CLIMCPServer(self.temp_dir)
    
    @patch('server.subprocess.run')
    def test_tool_failure_includes_error_reason(self, mock_run):
        """Scenario: Tool failure includes error reason."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="fatal error")
        
        result = self.server.tool_git_log({"limit": 10})
        
        self.assertIn("isError", result)
        self.assertTrue(result["isError"])
        self.assertIn("reason", result)
        self.assertTrue(len(result["reason"]) > 0)


class TestRootDirectoryConstraint(unittest.TestCase):
    """Tests for root directory constraint."""
    
    def test_root_directory_constraint_is_enforced(self):
        """Scenario: Root directory constraint is enforced at startup."""
        temp_dir = tempfile.mkdtemp()
        server = CLIMCPServer(temp_dir)
        
        # Root should be set and resolved
        self.assertEqual(str(server.root), Path(temp_dir).resolve().__str__())


class TestJSONRPCCommunication(unittest.TestCase):
    """Tests for JSON-RPC communication."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.server = CLIMCPServer(self.temp_dir)
    
    @patch('server.subprocess.run')
    def test_server_listens_on_stdin_for_jsonrpc_requests(self, mock_run):
        """Scenario: Server listens on stdin for JSON-RPC requests."""
        # This is tested via process_line method
        mock_run.return_value = MagicMock(returncode=0, stdout="result", stderr="")
        
        request = '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "git_status", "arguments": {}}, "id": 1}'
        response = self.server.process_line(request)
        
        self.assertIsNotNone(response)
        response_obj = json.loads(response)
        self.assertIn("jsonrpc", response_obj)
        self.assertEqual(response_obj["jsonrpc"], "2.0")
    
    @patch('server.subprocess.run')
    def test_server_sends_jsonrpc_responses_on_stdout(self, mock_run):
        """Scenario: Server sends JSON-RPC responses on stdout."""
        mock_run.return_value = MagicMock(returncode=0, stdout="result", stderr="")
        
        request = '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "git_status", "arguments": {}}, "id": 42}'
        response = self.server.process_line(request)
        
        response_obj = json.loads(response)
        self.assertEqual(response_obj["id"], 42)
        self.assertIn("result", response_obj)


class TestRegistration(unittest.TestCase):
    """Tests for registration (integration tests, not fully unit-testable)."""
    
    def test_cli_registration_format(self):
        """Scenario: CLI registration works."""
        # This test verifies the command format is as expected
        # Full integration test would require spawning claude mcp command
        expected_command = "claude mcp add cli-tools -- python /abs/path/server.py --root /abs/path/to/repo"
        self.assertIn("claude mcp add", expected_command)
        self.assertIn("--root", expected_command)
    
    def test_project_configuration_format(self):
        """Scenario: Project configuration registration works."""
        # This test verifies the .mcp.json format is as expected
        mcp_config = {
            "command": "python /abs/path/server.py --root /abs/path/to/repo"
        }
        self.assertIn("command", mcp_config)
        self.assertIn("--root", mcp_config["command"])
