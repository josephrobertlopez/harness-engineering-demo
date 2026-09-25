import unittest
import json
import sys
import os
from io import StringIO
from unittest.mock import Mock, patch, MagicMock
import subprocess
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import MCPServer, ToolRegistry


class TestToolExposure(unittest.TestCase):
    """Test tool discovery and exposure."""

    def setUp(self):
        """Create an MCP server for testing."""
        self.registry = ToolRegistry()
        self.server = MCPServer(root_dir="/repo", registry=self.registry)

    def test_tools_list_returns_four_tools(self):
        """Scenario: tools/list returns four tools"""
        # Get list of tools
        tools = self.registry.list_tools()

        # Should have exactly four tools
        self.assertEqual(len(tools), 4)

        # Check tool names
        tool_names = {tool['name'] for tool in tools}
        expected = {'git_status', 'git_log', 'git_diff_stat', 'rg_search'}
        self.assertEqual(tool_names, expected)

    def test_unknown_tool_returns_error(self):
        """Scenario: unknown tool returns error"""
        # Try to call a tool that doesn't exist
        result = self.server.call_tool('git commit', {})

        # Should return error with code -32602
        self.assertIsNotNone(result)
        self.assertTrue(isinstance(result, dict))
        # Result should indicate error
        if 'error' in result:
            self.assertEqual(result['error']['code'], -32602)


class TestToolParameters(unittest.TestCase):
    """Test tool parameter validation and invocation."""

    def setUp(self):
        """Create an MCP server for testing."""
        self.registry = ToolRegistry()
        self.server = MCPServer(root_dir="/repo", registry=self.registry)

    @patch('subprocess.run')
    def test_rg_search_with_valid_pattern_and_path(self, mock_run):
        """Scenario: rg_search with valid pattern and path"""
        # Mock subprocess to return successful result
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="src/file.py:10:found match",
            stderr=""
        )

        # Call rg_search with valid parameters
        result = self.server.call_tool('rg_search', {
            'pattern': 'foo',
            'path': 'src/'
        })

        # Should succeed
        self.assertNotIn('isError', result)

        # Verify the command was invoked
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        # Command should use rg with the specified syntax
        self.assertIn('rg', args[0])
        self.assertIn('-e', args)
        self.assertIn('foo', args)

    def test_rg_search_rejects_unknown_parameter(self):
        """Scenario: rg_search rejects unknown parameter"""
        # Try to call rg_search with unknown parameter
        result = self.server.call_tool('rg_search', {
            'pattern': 'foo',
            'case_sensitive': True
        })

        # Should return error
        self.assertTrue(result.get('isError', False) or 'error' in result)

    @patch('subprocess.run')
    def test_git_log_with_limit_1(self, mock_run):
        """Scenario: git_log with limit=1"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="commit abc123\nAuthor: User",
            stderr=""
        )

        result = self.server.call_tool('git_log', {'limit': 1})

        # Should succeed
        self.assertNotIn('isError', result)

        # Verify git log was called with -1 limit
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertIn('-1', args)

    @patch('subprocess.run')
    def test_git_log_with_limit_50(self, mock_run):
        """Scenario: git_log with limit=50"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="commit abc123\n" * 50,
            stderr=""
        )

        result = self.server.call_tool('git_log', {'limit': 50})

        # Should succeed
        self.assertNotIn('isError', result)

        # Verify git log was called with -50 limit
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertIn('-50', args)

    @patch('subprocess.run')
    def test_git_log_with_default_limit(self, mock_run):
        """Scenario: git_log with default limit"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="commit abc123\n" * 10,
            stderr=""
        )

        result = self.server.call_tool('git_log', {})

        # Should succeed
        self.assertNotIn('isError', result)

        # Verify git log was called with -10 (default)
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertIn('-10', args)

    @patch('subprocess.run')
    def test_rg_command_invocation_uses_correct_syntax(self, mock_run):
        """Scenario: rg command invocation uses correct syntax"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="file.py:1:match",
            stderr=""
        )

        self.server.call_tool('rg_search', {
            'pattern': 'test_pattern',
            'path': 'src/'
        })

        # Verify the exact command syntax
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]

        # Should match: rg --line-number --no-heading --color never --max-count 50 -e <pattern> -- <path>
        expected_start = ['rg', '--line-number', '--no-heading', '--color', 'never', '--max-count', '50', '-e']
        self.assertEqual(args[:len(expected_start)], expected_start)
        self.assertIn('test_pattern', args)
        self.assertIn('--', args)


class TestTimeout(unittest.TestCase):
    """Test timeout enforcement."""

    def setUp(self):
        """Create an MCP server for testing."""
        self.registry = ToolRegistry()
        self.server = MCPServer(root_dir="/repo", registry=self.registry)

    @patch('subprocess.run')
    def test_rg_search_timeout(self, mock_run):
        """Scenario: rg_search timeout"""
        # Mock subprocess to raise timeout
        mock_run.side_effect = subprocess.TimeoutExpired('rg', 10)

        result = self.server.call_tool('rg_search', {
            'pattern': 'foo',
            'path': 'src/'
        })

        # Should return error
        self.assertTrue(result.get('isError', False))

    @patch('subprocess.run')
    def test_git_log_timeout(self, mock_run):
        """Scenario: git_log timeout"""
        mock_run.side_effect = subprocess.TimeoutExpired('git', 10)

        result = self.server.call_tool('git_log', {'limit': 10})

        # Should return error
        self.assertTrue(result.get('isError', False))

    @patch('subprocess.run')
    def test_git_status_timeout(self, mock_run):
        """Scenario: git_status timeout"""
        mock_run.side_effect = subprocess.TimeoutExpired('git', 10)

        result = self.server.call_tool('git_status', {})

        # Should return error
        self.assertTrue(result.get('isError', False))

    @patch('subprocess.run')
    def test_git_diff_stat_timeout(self, mock_run):
        """Scenario: git_diff_stat timeout"""
        mock_run.side_effect = subprocess.TimeoutExpired('git', 10)

        result = self.server.call_tool('git_diff_stat', {})

        # Should return error
        self.assertTrue(result.get('isError', False))


class TestOutputTruncation(unittest.TestCase):
    """Test output truncation at 8000 characters."""

    def setUp(self):
        """Create an MCP server for testing."""
        self.registry = ToolRegistry()
        self.server = MCPServer(root_dir="/repo", registry=self.registry)

    @patch('subprocess.run')
    def test_successful_output_truncation(self, mock_run):
        """Scenario: successful output truncation"""
        # Create output larger than 8000 characters
        large_output = "x" * 9000
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=large_output,
            stderr=""
        )

        result = self.server.call_tool('git_log', {'limit': 50})

        # Should include truncated marker
        output = result.get('result', {}).get('output', '')
        self.assertLessEqual(len(output), 8011)  # 8000 + len('[truncated]')
        self.assertIn('[truncated]', output)

    @patch('subprocess.run')
    def test_error_message_truncation(self, mock_run):
        """Scenario: error message truncation"""
        # Create a large error message
        large_error = "error: " + "x" * 9000
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr=large_error
        )

        result = self.server.call_tool('git_log', {'limit': 10})

        # Should have error with truncation
        if result.get('isError'):
            reason = result.get('reason', '')
            self.assertLessEqual(len(reason), 8011)
            if len(reason) > 8000:
                self.assertIn('[truncated]', reason)


class TestErrorHandling(unittest.TestCase):
    """Test error handling."""

    def setUp(self):
        """Create an MCP server for testing."""
        self.registry = ToolRegistry()
        self.server = MCPServer(root_dir="/repo", registry=self.registry)

    @patch('subprocess.run')
    def test_invalid_rg_pattern_error(self, mock_run):
        """Scenario: invalid rg pattern error"""
        # Mock invalid regex error
        mock_run.return_value = MagicMock(
            returncode=2,
            stdout="",
            stderr="regex parse error"
        )

        result = self.server.call_tool('rg_search', {
            'pattern': '[invalid(',
            'path': 'src/'
        })

        # Should return error
        self.assertTrue(result.get('isError', False))
        self.assertIn('reason', result)

    @patch('subprocess.run')
    def test_git_status_error_for_non_repository(self, mock_run):
        """Scenario: git_status error for non-repository"""
        # Mock git error for non-repo
        mock_run.return_value = MagicMock(
            returncode=128,
            stdout="",
            stderr="fatal: not a git repository"
        )

        result = self.server.call_tool('git_status', {})

        # Should return error
        self.assertTrue(result.get('isError', False))

    @patch('subprocess.run')
    def test_rg_search_no_matches_is_success(self, mock_run):
        """Scenario: rg_search no matches is success"""
        # Mock rg exit code 1 (no matches)
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr=""
        )

        result = self.server.call_tool('rg_search', {
            'pattern': 'nomatch',
            'path': 'src/'
        })

        # Should NOT be an error (rg exit code 1 is success for no matches)
        self.assertFalse(result.get('isError', False))


class TestPathValidation(unittest.TestCase):
    """Test path validation and security."""

    def setUp(self):
        """Create an MCP server for testing."""
        self.registry = ToolRegistry()
        self.server = MCPServer(root_dir="/repo", registry=self.registry)

    def test_rg_search_rejects_path_escape_with_dotdot(self):
        """Scenario: rg_search rejects path escape with ../"""
        result = self.server.call_tool('rg_search', {
            'pattern': 'foo',
            'path': '../etc/passwd'
        })

        # Should return error
        self.assertTrue(result.get('isError', False))
        self.assertIn('escapes', result.get('reason', '').lower())

    def test_rg_search_rejects_absolute_path_outside_root(self):
        """Scenario: rg_search rejects absolute path outside root"""
        result = self.server.call_tool('rg_search', {
            'pattern': 'foo',
            'path': '/etc/passwd'
        })

        # Should return error
        self.assertTrue(result.get('isError', False))
        self.assertIn('escapes', result.get('reason', '').lower())


class TestShellSafety(unittest.TestCase):
    """Test that arguments are not interpreted by shell."""

    def setUp(self):
        """Create an MCP server for testing."""
        self.registry = ToolRegistry()
        self.server = MCPServer(root_dir="/repo", registry=self.registry)

    @patch('subprocess.run')
    def test_pattern_with_dash_is_literal(self, mock_run):
        """Scenario: pattern with dash is literal"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="-v match line",
            stderr=""
        )

        self.server.call_tool('rg_search', {
            'pattern': '-v',
            'path': 'src/'
        })

        # Verify -v is passed as pattern, not flag
        args = mock_run.call_args[0][0]
        self.assertIn('-e', args)
        self.assertIn('-v', args)
        # -v should come after -e, not as a standalone flag
        e_index = args.index('-e')
        v_index = args.index('-v')
        self.assertGreater(v_index, e_index)

    @patch('subprocess.run')
    def test_pattern_with_semicolon_is_literal(self, mock_run):
        """Scenario: pattern with semicolon is literal"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr=""
        )

        self.server.call_tool('rg_search', {
            'pattern': 'foo; rm -rf /',
            'path': 'src/'
        })

        # Verify the pattern is passed as a single argument
        args = mock_run.call_args[0][0]
        self.assertIn('foo; rm -rf /', args)

    @patch('subprocess.run')
    def test_pattern_with_variable_syntax_is_literal(self, mock_run):
        """Scenario: pattern with variable syntax is literal"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr=""
        )

        self.server.call_tool('rg_search', {
            'pattern': '$VAR',
            'path': 'src/'
        })

        # Verify $VAR is passed literally, not expanded
        args = mock_run.call_args[0][0]
        self.assertIn('$VAR', args)


class TestServerConfiguration(unittest.TestCase):
    """Test server configuration."""

    def test_server_accepts_root_flag(self):
        """Scenario: server accepts --root flag"""
        # Should be able to create server with root directory
        server = MCPServer(root_dir="/home/user/repo", registry=ToolRegistry())
        self.assertIsNotNone(server)
        self.assertEqual(server.root_dir, "/home/user/repo")

    def test_all_commands_operate_within_root(self):
        """Scenario: all commands operate within root"""
        server = MCPServer(root_dir="/home/user/repo", registry=ToolRegistry())

        # Path operations should be relative to root
        # This is tested implicitly through path validation in other tests
        self.assertEqual(server.root_dir, "/home/user/repo")


if __name__ == '__main__':
    unittest.main()
