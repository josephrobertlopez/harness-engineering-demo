"""Tests for root directory and path boundaries."""

import unittest
from unittest.mock import patch, MagicMock
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from server import MCPServer


class TestPathBoundaries(unittest.TestCase):
    """Tests for root directory enforcement."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    @patch("server.subprocess.run")
    def test_commands_run_in_specified_root_directory(self, mock_run):
        """Scenario: Commands run in specified root directory"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="On branch main",
            stderr=""
        )

        server = MCPServer(root_dir=str(self.root))
        server.call_tool("git_status", {})

        # Verify the command was executed with the root directory as cwd
        call_kwargs = mock_run.call_args[1]
        self.assertEqual(call_kwargs["cwd"], self.root)

    def test_relative_path_outside_root_is_rejected(self):
        """Scenario: Relative path outside root is rejected"""
        server = MCPServer(root_dir=str(self.root))

        response = server.call_tool("rg_search", {
            "pattern": "test",
            "path": "../outside"
        })

        # Should return error
        self.assertTrue(response["result"]["isError"])
        self.assertIn("escapes", response["result"]["content"][0]["text"].lower())

    def test_absolute_path_outside_root_is_rejected(self):
        """Scenario: Absolute path outside root is rejected"""
        server = MCPServer(root_dir=str(self.root))

        response = server.call_tool("rg_search", {
            "pattern": "test",
            "path": "/etc/passwd"
        })

        # Should return error
        self.assertTrue(response["result"]["isError"])
        self.assertIn("escapes", response["result"]["content"][0]["text"].lower())


if __name__ == "__main__":
    unittest.main()
