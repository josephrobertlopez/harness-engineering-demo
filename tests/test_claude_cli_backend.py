"""The CLI backend must fail loudly rather than launder an error into a reply."""

import unittest
from unittest import mock

from tests import context  # noqa: F401

from wikiskill.backends.base import LLMRequest
from wikiskill.backends.claude_cli import ClaudeCliBackend, _parse

REQ = LLMRequest(role="inference", model="claude-haiku-4-5", system="s", prompt="p")


class Completed:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestParse(unittest.TestCase):
    def test_result_object(self):
        text, usage = _parse('{"type":"result","result":"hello","usage":{"input_tokens":3}}')
        self.assertEqual(text, "hello")
        self.assertEqual(usage, {"input_tokens": 3})

    def test_stream_of_messages_takes_the_result(self):
        text, _ = _parse('[{"type":"assistant"},{"type":"result","result":"final"}]')
        self.assertEqual(text, "final")

    def test_content_blocks(self):
        text, _ = _parse('{"content":[{"type":"text","text":"a"},{"type":"text","text":"b"}]}')
        self.assertEqual(text, "ab")

    def test_prose_is_an_error_not_a_reply(self):
        """The real failure this guards: an org policy blocking the CLI."""
        with self.assertRaises(RuntimeError) as cm:
            _parse("Your organization requires remote managed settings to load")
        self.assertIn("did not return JSON", str(cm.exception))

    def test_empty_output_is_an_error(self):
        with self.assertRaises(RuntimeError):
            _parse("   ")


class TestBackend(unittest.TestCase):
    def test_nonzero_exit_surfaces_stderr(self):
        backend = ClaudeCliBackend(executable="claude")
        with mock.patch(
            "subprocess.run",
            return_value=Completed(returncode=1, stderr="organization requires remote managed settings"),
        ):
            with self.assertRaises(RuntimeError) as cm:
                backend.complete(REQ)
        self.assertIn("organization requires remote managed settings", str(cm.exception))

    def test_missing_executable_points_at_the_mock_backend(self):
        backend = ClaudeCliBackend(executable="claude")
        with mock.patch("subprocess.run", side_effect=FileNotFoundError):
            with self.assertRaises(RuntimeError) as cm:
                backend.complete(REQ)
        self.assertIn("--backend mock", str(cm.exception))

    def test_tools_are_disabled(self):
        """The evaluated model must not reach the real filesystem."""
        backend = ClaudeCliBackend(executable="claude")
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return Completed(stdout='{"type":"result","result":"ok"}')

        with mock.patch("subprocess.run", side_effect=fake_run):
            backend.complete(REQ)
        cmd = captured["cmd"]
        self.assertIn("--allowed-tools", cmd)
        self.assertEqual(cmd[cmd.index("--allowed-tools") + 1], "")


if __name__ == "__main__":
    unittest.main()
