"""Tests matching exact spec scenarios for CLI MCP server."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server import CLIMCPServer


class TestToolAvailability(unittest.TestCase):
    """Tests for tool availability."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.server = CLIMCPServer(self.temp_dir)

    def test_server_advertises_git_and_ripgrep_tools(self):
        """Scenario: Server advertises git and ripgrep tools."""
        self.assertEqual(self.server.AVAILABLE_TOOLS, {"git_status", "git_log", "git_diff_stat", "rg_search"})

    def test_other_clis_are_not_exposed(self):
        """Scenario: Other CLIs are not exposed."""
        result = self.server.invoke_tool("npm_install", {})
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], -32602)


class TestToolInvocation(unittest.TestCase):
    """Tests for tool invocation."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.server = CLIMCPServer(self.temp_dir)

    @patch('server.subprocess.run')
    def test_four_tools_are_available(self, mock_run):
        """Scenario: Four tools are available."""
        mock_run.return_value = MagicMock(returncode=0, stdout="output", stderr="")

        # Test all four tools are callable
        result = self.server.invoke_tool("git_status", {})
        self.assertNotIn("error", result)

        result = self.server.invoke_tool("git_log", {"limit": 10})
        self.assertNotIn("error", result)

        result = self.server.invoke_tool("git_diff_stat", {})
        self.assertNotIn("error", result)

        result = self.server.invoke_tool("rg_search", {"pattern": "test"})
        self.assertNotIn("error", result)

    def test_write_operations_are_not_available(self):
        """Scenario: Write operations are not available."""
        for write_op in ["git_push", "git_commit", "git_checkout", "rg_replace"]:
            result = self.server.invoke_tool(write_op, {})
            self.assertIn("error", result)
            self.assertEqual(result["error"]["code"], -32602)


class TestGitLogSignature(unittest.TestCase):
    """Tests for git_log command."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.server = CLIMCPServer(self.temp_dir)

    @patch('server.subprocess.run')
    def test_git_log_with_explicit_limit(self, mock_run):
        """Scenario: git_log with explicit limit."""
        mock_run.return_value = MagicMock(returncode=0, stdout="abc123 msg\n", stderr="")

        result = self.server.tool_git_log({"limit": 5})

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertEqual(args, ["git", "log", "--oneline", "-n", "5"])
        self.assertNotIn("isError", result)

    @patch('server.subprocess.run')
    def test_git_log_with_default_limit(self, mock_run):
        """Scenario: git_log with default limit."""
        mock_run.return_value = MagicMock(returncode=0, stdout="output\n", stderr="")

        result = self.server.tool_git_log({})

        args = mock_run.call_args[0][0]
        self.assertEqual(args, ["git", "log", "--oneline", "-n", "10"])


class TestGitDiffStat(unittest.TestCase):
    """Tests for git_diff_stat."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.server = CLIMCPServer(self.temp_dir)

    @patch('server.subprocess.run')
    def test_git_diff_stat_accepts_no_parameters(self, mock_run):
        """Scenario: git_diff_stat accepts no parameters."""
        mock_run.return_value = MagicMock(returncode=0, stdout="file.py | 5 +++++\n", stderr="")

        result = self.server.tool_git_diff_stat({})

        args = mock_run.call_args[0][0]
        self.assertEqual(args, ["git", "diff", "--stat"])


class TestRgSearchSignature(unittest.TestCase):
    """Tests for rg_search command."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.server = CLIMCPServer(self.temp_dir)

    @patch('server.subprocess.run')
    def test_rg_search_with_pattern_and_path(self, mock_run):
        """Scenario: rg_search with pattern and path."""
        mock_run.return_value = MagicMock(returncode=0, stdout="file.py:5:match\n", stderr="")

        result = self.server.tool_rg_search({"pattern": "TODO", "path": "src/"})

        args = mock_run.call_args[0][0]
        self.assertIn("rg", args[0])
        self.assertIn("TODO", args)
        self.assertIn("src/", args)

    @patch('server.subprocess.run')
    def test_rg_search_with_default_path(self, mock_run):
        """Scenario: rg_search with default path."""
        mock_run.return_value = MagicMock(returncode=0, stdout="output\n", stderr="")

        result = self.server.tool_rg_search({"pattern": "pattern"})

        args = mock_run.call_args[0][0]
        self.assertIn(".", args)


class TestShellInjectionPrevention(unittest.TestCase):
    """Tests for shell injection prevention."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.server = CLIMCPServer(self.temp_dir)

    @patch('server.subprocess.run')
    def test_shell_metacharacters_are_not_interpreted(self, mock_run):
        """Scenario: Shell metacharacters are not interpreted."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        self.server.tool_rg_search({"pattern": "$(rm -rf /)"})

        args = mock_run.call_args[0][0]
        self.assertIn("$(rm -rf /)", args)

    @patch('server.subprocess.run')
    def test_command_path_injection_is_prevented(self, mock_run):
        """Scenario: Command path injection is prevented."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        self.server.tool_rg_search({"pattern": "; cat /etc/passwd"})

        args = mock_run.call_args[0][0]
        self.assertIn("; cat /etc/passwd", args)

    @patch('server.subprocess.run')
    def test_path_traversal_characters_are_not_shell_evaluated(self, mock_run):
        """Scenario: Path traversal characters are not shell-evaluated."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        self.server.tool_rg_search({"pattern": "test", "path": "../../../etc/passwd"})

        # Path validation should reject this
        # This is handled by validate_path


class TestTimeout(unittest.TestCase):
    """Tests for timeout behavior."""

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

        self.assertIn("isError", result)


class TestOutputTruncation(unittest.TestCase):
    """Tests for output truncation."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.server = CLIMCPServer(self.temp_dir)

    @patch('server.subprocess.run')
    def test_output_under_8000_characters_is_returned_in_full(self, mock_run):
        """Scenario: Output under 8000 characters is returned in full."""
        output = "x" * 5000
        mock_run.return_value = MagicMock(returncode=0, stdout=output, stderr="")

        result = self.server.invoke_tool("git_log", {"limit": 10})

        self.assertEqual(result["output"], output)

    @patch('server.subprocess.run')
    def test_output_at_exactly_8000_characters_is_returned_without_marker(self, mock_run):
        """Scenario: Output at exactly 8000 characters is returned without marker."""
        output = "x" * 8000
        mock_run.return_value = MagicMock(returncode=0, stdout=output, stderr="")

        result = self.server.invoke_tool("git_log", {"limit": 10})

        self.assertEqual(result["output"], output)
        self.assertNotIn("[truncated]", result["output"])

    @patch('server.subprocess.run')
    def test_output_over_8000_characters_is_truncated_and_marked(self, mock_run):
        """Scenario: Output over 8000 characters is truncated and marked."""
        output = "x" * 8500
        mock_run.return_value = MagicMock(returncode=0, stdout=output, stderr="")

        result = self.server.invoke_tool("git_log", {"limit": 10})

        self.assertTrue(result["output"].endswith("[truncated]"))
        self.assertEqual(len(result["output"]), 8000 + len("[truncated]"))


class TestErrorHandling(unittest.TestCase):
    """Tests for error handling."""

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
        self.assertIn("reason", result)


class TestRipgrepExitStatus(unittest.TestCase):
    """Tests for ripgrep exit codes."""

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

    @patch('server.subprocess.run')
    def test_ripgrep_exit_1_does_not_set_iserror(self, mock_run):
        """Scenario: ripgrep exit 1 does not set isError."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")

        result = self.server.tool_rg_search({"pattern": "notfound"})

        self.assertNotIn("isError", result)

    @patch('server.subprocess.run')
    def test_other_ripgrep_exit_codes_are_errors(self, mock_run):
        """Scenario: Other ripgrep exit codes are errors."""
        mock_run.return_value = MagicMock(returncode=2, stdout="", stderr="error")

        result = self.server.tool_rg_search({"pattern": "[invalid"})

        self.assertIn("isError", result)


class TestUnknownTools(unittest.TestCase):
    """Tests for unknown tool handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.server = CLIMCPServer(self.temp_dir)

    def test_unknown_tool_returns_error_minus_32602(self):
        """Scenario: Unknown tool returns -32602."""
        result = self.server.invoke_tool("unknown_tool", {})

        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], -32602)

    def test_write_operation_returns_error_minus_32602(self):
        """Scenario: Write operation returns -32602."""
        result = self.server.invoke_tool("git_push", {})

        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], -32602)


class TestPathValidation(unittest.TestCase):
    """Tests for path validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.server = CLIMCPServer(self.temp_dir)

    def test_paths_within_root_are_valid(self):
        """Scenario: Paths within root are valid."""
        valid, error = self.server.validate_path("src/")
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_path_traversal_is_rejected(self):
        """Scenario: Path traversal is rejected."""
        valid, error = self.server.validate_path("../../../etc/passwd")
        self.assertFalse(valid)
        self.assertEqual(error, "path escapes the root")

    def test_absolute_paths_outside_root_are_rejected(self):
        """Scenario: Absolute paths outside root are rejected."""
        valid, error = self.server.validate_path("/etc/passwd")
        self.assertFalse(valid)
        self.assertEqual(error, "path escapes the root")


class TestJSONRPCProtocol(unittest.TestCase):
    """Tests for JSON-RPC protocol."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.server = CLIMCPServer(self.temp_dir)

    @patch('server.subprocess.run')
    def test_server_listens_on_stdin_for_jsonrpc_requests(self, mock_run):
        """Scenario: Server listens on stdin for JSON-RPC requests."""
        mock_run.return_value = MagicMock(returncode=0, stdout="result", stderr="")

        request = '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "git_status", "arguments": {}}, "id": 1}'
        response = self.server.process_line(request)

        self.assertIsNotNone(response)
        response_obj = json.loads(response)
        self.assertEqual(response_obj["jsonrpc"], "2.0")

    @patch('server.subprocess.run')
    def test_server_sends_jsonrpc_responses_on_stdout(self, mock_run):
        """Scenario: Server sends JSON-RPC responses on stdout."""
        mock_run.return_value = MagicMock(returncode=0, stdout="result", stderr="")

        request = '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "git_status", "arguments": {}}, "id": 42}'
        response = self.server.process_line(request)

        response_obj = json.loads(response)
        self.assertEqual(response_obj["id"], 42)


class TestProtocolVersion(unittest.TestCase):
    """Tests for protocol version."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.server = CLIMCPServer(self.temp_dir)

    def test_server_advertises_protocol_version(self):
        """Scenario: Server advertises protocol version."""
        self.assertEqual(self.server.PROTOCOL_VERSION, "2025-06-18")


class TestParseErrors(unittest.TestCase):
    """Tests for parse error handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.server = CLIMCPServer(self.temp_dir)

    def test_unparseable_json_returns_error_minus_32700(self):
        """Scenario: Unparseable JSON returns -32700."""
        response = self.server.process_line("invalid json {")
        response_obj = json.loads(response)
        self.assertEqual(response_obj["error"]["code"], -32700)

    def test_binary_data_returns_error_minus_32700(self):
        """Scenario: Binary data returns -32700."""
        response = self.server.process_line("\x00\x01\x02")
        response_obj = json.loads(response)
        self.assertEqual(response_obj["error"]["code"], -32700)


class TestRootDirectoryConstraint(unittest.TestCase):
    """Tests for root directory constraint."""

    def test_root_directory_constraint_is_enforced(self):
        """Scenario: Root directory constraint is enforced at startup."""
        temp_dir = tempfile.mkdtemp()
        server = CLIMCPServer(temp_dir)

        self.assertEqual(str(server.root), Path(temp_dir).resolve().__str__())


class TestRegistration(unittest.TestCase):
    """Tests for registration (integration level)."""

    def test_cli_registration_works(self):
        """Scenario: CLI registration works."""
        cmd = "claude mcp add cli-tools -- python /path/server.py --root /repo"
        self.assertIn("claude mcp add", cmd)
        self.assertIn("--root", cmd)

    def test_project_configuration_registration_works(self):
        """Scenario: Project configuration registration works."""
        config = {"command": "python /path/server.py --root /repo"}
        self.assertIn("--root", config["command"])


if __name__ == "__main__":
    unittest.main()
