"""One test per spec scenario. The runner is faked for everything except
the stdio round trip, the real-git check and the limits of run_command, so
the suite runs where git and rg are not installed."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import server
from server import Completed, Server, ToolError, run_command

IMPL = Path(__file__).resolve().parents[1]


class FakeRunner:
    def __init__(self, result=Completed(0, "ok\n", "")):
        self.result = result
        self.calls = []

    def __call__(self, argv, cwd):
        self.calls.append((argv, cwd))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.runner = FakeRunner()
        self.server = Server(self.tmp, runner=self.runner)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def call(self, name, arguments=None):
        response = self.server.handle(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": arguments or {}}}
        )
        return response

    def result(self, name, arguments=None):
        r = self.call(name, arguments)["result"]
        return r["isError"], r["content"][0]["text"]


class Protocol(Base):
    def test_initialize(self):
        """Scenario: Initialize handshake"""
        r = self.server.handle({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}})
        self.assertEqual(r["result"]["protocolVersion"], "2025-06-18")
        self.assertIn("tools", r["result"]["capabilities"])
        self.assertIsNone(self.server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))

    def test_stdio_round_trip(self):
        """Scenario: Stdio round trip"""
        lines = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        ]
        proc = subprocess.run(
            [sys.executable, str(IMPL / "server.py"), "--root", str(self.tmp)],
            input="".join(json.dumps(m) + "\n" for m in lines),
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual([m["id"] for m in out], [1, 2])

    def test_unknown_tool(self):
        """Scenario: Unknown tool"""
        self.assertEqual(self.call("rm_rf")["error"]["code"], -32602)

    def test_unknown_method(self):
        """Scenario: Unknown method"""
        r = self.server.handle({"jsonrpc": "2.0", "id": 3, "method": "resources/list"})
        self.assertEqual(r["error"]["code"], -32601)

    def test_malformed_json(self):
        """Scenario: Malformed JSON"""
        import io

        out = io.StringIO()
        self.server.serve(io.StringIO("{not json\n"), out)
        r = json.loads(out.getvalue())
        self.assertEqual((r["error"]["code"], r["id"]), (-32700, None))


class Catalogue(Base):
    def test_exactly_four_tools(self):
        """Scenario: Exactly four tools"""
        tools = self.server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})["result"]["tools"]
        self.assertEqual(sorted(t["name"] for t in tools), ["git_diff_stat", "git_log", "git_status", "rg_search"])
        self.assertTrue(all(t["inputSchema"]["additionalProperties"] is False for t in tools))
        for name in ("git_status", "git_log", "git_diff_stat"):
            self.call(name)
        self.call("rg_search", {"pattern": "x"})
        self.assertEqual({argv[0] for argv, _ in self.runner.calls}, {"git", "rg"})

    def test_unlisted_argument(self):
        """Scenario: Unlisted argument rejected"""
        is_error, text = self.result("git_status", {"args": "--all"})
        self.assertTrue(is_error)
        self.assertIn("unexpected", text)
        self.assertEqual(self.runner.calls, [])


class GitTools(Base):
    def test_porcelain_status(self):
        """Scenario: Porcelain status"""
        self.call("git_status")
        self.assertEqual(self.runner.calls, [(["git", "status", "--porcelain=v1", "--branch"], self.tmp.resolve())])

    def test_log_default(self):
        """Scenario: Log limit defaults to 10"""
        self.call("git_log")
        self.assertEqual(self.runner.calls[0][0], ["git", "log", "--oneline", "-n", "10"])

    def test_log_out_of_range(self):
        """Scenario: Log limit out of range"""
        for bad in (51, 0, True, "5"):
            is_error, _ = self.result("git_log", {"limit": bad})
            self.assertTrue(is_error, bad)
        self.assertEqual(self.runner.calls, [])

    def test_diff_stat(self):
        self.call("git_diff_stat")
        self.assertEqual(self.runner.calls[0][0], ["git", "diff", "--stat"])

    @unittest.skipUnless(shutil.which("git"), "git not installed")
    def test_real_git_status(self):
        """Scenario: Real git status"""
        subprocess.run(["git", "init", "-q", str(self.tmp)], check=True)
        self.server = Server(self.tmp)  # the real runner, not the fake
        is_error, text = self.result("git_status")
        self.assertFalse(is_error, text)
        self.assertTrue(text.startswith("##"), text)


class RgSearch(Base):
    def test_flag_like_pattern(self):
        """Scenario: Flag-like pattern searched literally"""
        self.call("rg_search", {"pattern": "--files"})
        argv = self.runner.calls[0][0]
        i = argv.index("-e")
        self.assertEqual(argv[i:i + 3], ["-e", "--files", "--"])

    def test_no_matches(self):
        """Scenario: No matches is not an error"""
        self.runner.result = Completed(1, "", "")
        self.assertEqual(self.result("rg_search", {"pattern": "zzz"}), (False, "no matches"))

    def test_empty_pattern(self):
        """Scenario: Empty pattern rejected"""
        self.assertTrue(self.result("rg_search", {"pattern": ""})[0])


class Limits(Base):
    def test_path_escape(self):
        """Scenario: Path escaping root rejected"""
        outside = str(Path(tempfile.gettempdir()).resolve().parent)
        for path in ("../..", outside):
            is_error, text = self.result("rg_search", {"pattern": "x", "path": path})
            self.assertTrue(is_error, path)
            self.assertIn("root", text)
        self.assertEqual(self.runner.calls, [])

    def test_missing_binary(self):
        """Scenario: Missing binary"""
        with self.assertRaisesRegex(ToolError, "not installed"):
            run_command(["definitely-not-a-real-cli-311"], self.tmp)
        self.runner.result = ToolError("rg is not installed on this machine")
        is_error, text = self.result("rg_search", {"pattern": "x"})
        self.assertTrue(is_error)
        self.assertIn("not installed", text)

    def test_timeout(self):
        """Scenario: Timeout"""
        with self.assertRaisesRegex(ToolError, "timed out"):
            run_command([sys.executable, "-c", "import time; time.sleep(5)"], self.tmp, timeout=0.5)
        self.assertEqual(server.TIMEOUT_SECONDS, 10)

    def test_non_zero_exit(self):
        """Scenario: Non-zero exit"""
        self.runner.result = Completed(128, "", "fatal: not a git repository")
        is_error, text = self.result("git_status")
        self.assertTrue(is_error)
        self.assertIn("not a git repository", text)

    def test_truncated(self):
        """Scenario: Output truncated"""
        self.runner.result = Completed(0, "x" * 20000, "")
        _, text = self.result("git_log")
        self.assertEqual(text, "x" * 8000 + "\n[truncated]")


class Registration(unittest.TestCase):
    def test_mcp_json(self):
        """Scenario: Project config is valid"""
        config = json.loads((IMPL / ".mcp.json").read_text(encoding="utf-8"))
        entry = config["mcpServers"]["cli-tools"]
        self.assertEqual(entry["command"], "python")
        self.assertIn("server.py", entry["args"])
        self.assertIn("--root", entry["args"])


if __name__ == "__main__":
    unittest.main()
