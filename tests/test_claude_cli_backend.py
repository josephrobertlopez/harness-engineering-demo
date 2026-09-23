"""The CLI backend must fail loudly rather than launder an error into a reply."""

import unittest
from pathlib import Path
from unittest import mock

from tests import context  # noqa: F401

from wikiskill.backends.base import LLMRequest
from wikiskill.backends.claude_cli import ClaudeCliBackend, _parse, resolve_executable

REQ = LLMRequest(role="inference", model="claude-haiku-4-5", system="s", prompt="p")


class Completed:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestParse(unittest.TestCase):
    def test_result_object(self):
        text, usage, cost = _parse(
            '{"type":"result","result":"hello","usage":{"input_tokens":3},"total_cost_usd":0.5}'
        )
        self.assertEqual(text, "hello")
        self.assertEqual(usage, {"input_tokens": 3})
        self.assertEqual(cost, 0.5)

    def test_stream_of_messages_takes_the_result(self):
        text, _, _ = _parse('[{"type":"assistant"},{"type":"result","result":"final"}]')
        self.assertEqual(text, "final")

    def test_content_blocks(self):
        text, _, _ = _parse('{"content":[{"type":"text","text":"a"},{"type":"text","text":"b"}]}')
        self.assertEqual(text, "ab")

    def test_is_error_flag_is_raised(self):
        with self.assertRaises(RuntimeError):
            _parse('{"type":"result","is_error":true,"result":"boom"}')

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

    def test_isolation_flags(self):
        """The measurement must be of our benchmark, not of Claude Code.

        Appending to the default system prompt leaves Claude Code's own
        coding-agent identity in front of ours and it wins; leaving tools,
        settings or MCP servers enabled lets the model solve tasks by means
        the trace does not record.
        """
        cmd = ClaudeCliBackend(executable="claude").build_command(REQ)

        # Replace, never append.
        self.assertIn("--system-prompt", cmd)
        self.assertNotIn("--append-system-prompt", cmd)
        self.assertEqual(cmd[cmd.index("--system-prompt") + 1], REQ.system)

        # `--tools ""` is the documented kill switch; `--allowed-tools ""`
        # is a different option and does not disable anything.
        self.assertIn("--tools", cmd)
        self.assertEqual(cmd[cmd.index("--tools") + 1], "")
        self.assertNotIn("--allowed-tools", cmd)

        self.assertIn("--restricted", cmd)
        self.assertIn("--strict-mcp-config", cmd)
        self.assertEqual(cmd[cmd.index("--output-format") + 1], "json")

    def test_cost_accumulates(self):
        backend = ClaudeCliBackend(executable="claude")
        with mock.patch(
            "subprocess.run",
            return_value=Completed(stdout='{"result":"ok","total_cost_usd":0.25}'),
        ):
            backend.complete(REQ)
            backend.complete(REQ)
        self.assertAlmostEqual(backend.total_cost_usd, 0.5)


class TestExecutableResolution(unittest.TestCase):
    def test_windows_shim_is_bypassed_when_the_real_exe_exists(self):
        """A .CMD shim mangles braces, quotes and newlines in arguments.

        It fails silently: the model gets a corrupted system prompt and
        answers in prose, so the bug looks like a prompting problem.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "claude.CMD").write_text("shim", encoding="utf-8")
            real = root / "node_modules/@anthropic-ai/claude-code/bin"
            real.mkdir(parents=True)
            (real / "claude.exe").write_text("binary", encoding="utf-8")
            with mock.patch("shutil.which", return_value=str(root / "claude.CMD")):
                self.assertEqual(resolve_executable(), str(real / "claude.exe"))

    def test_plain_executable_is_used_as_is(self):
        with mock.patch("shutil.which", return_value="/usr/local/bin/claude"):
            self.assertEqual(resolve_executable(), str(Path("/usr/local/bin/claude")))

    def test_explicit_wins(self):
        self.assertEqual(resolve_executable("/custom/claude"), "/custom/claude")


if __name__ == "__main__":
    unittest.main()
