"""specgate outside its own repo: non-editable installs, Windows, other layouts.

Each test here pins a way the gate used to pass, fail or write files
differently depending on where it was installed or which OS ran it.
"""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from specgate import cli, l0_schema
from specgate.trace import generate_trace

# Duplicated from test_cov_cli rather than imported: L3 discovers this
# directory as top level, where `tests.` is not an importable package.
PRD = (
    "---\nfeature: f\nacs:\n  - id: AC-1\n    given: a\n    when: b\n    then: c\n"
    "    tests: [test_add]\n---\n"
)
IMPL = "# implements: AC-1\ndef add(a, b):\n    return a + b\n"
TEST = (
    "import sys\nimport unittest\nfrom pathlib import Path\n"
    "sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))\n"
    "from impl import add\n\n\nclass TestAdd(unittest.TestCase):\n"
    "    # covers: AC-1\n    def test_add(self):\n        self.assertEqual(add(1, 2), 3)\n"
)


def make_repo(root: Path) -> Path:
    (root / "src").mkdir()
    (root / "tests").mkdir()
    (root / "prd.md").write_text(PRD)
    (root / "src" / "impl.py").write_text(IMPL)
    (root / "tests" / "test_impl.py").write_text(TEST)
    return root


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          check=True, env=cli.git_env()).stdout


def init_repo(root: Path) -> None:
    git(root, "init", "-q")
    git(root, "config", "user.email", "t@example.com")
    git(root, "config", "user.name", "t")


def run_main(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = cli.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class TestSchemaLocation(unittest.TestCase):
    def test_default_schema_exists(self) -> None:
        self.assertTrue(l0_schema.DEFAULT_SCHEMA.is_file(), l0_schema.DEFAULT_SCHEMA)

    def test_packaged_schema_is_where_the_wheel_puts_it(self) -> None:
        # pyproject force-includes schema/ as specgate/schema inside the wheel.
        self.assertEqual(l0_schema._PACKAGED_SCHEMA.parent.parent, Path(l0_schema.__file__).parent)


class TestNpx(unittest.TestCase):
    def test_resolved_path_is_used(self) -> None:
        with patch("shutil.which", return_value=r"C:\node\npx.cmd"):
            self.assertEqual(l0_schema.npx(), r"C:\node\npx.cmd")

    def test_bare_name_when_not_on_path(self) -> None:
        with patch("shutil.which", return_value=None):
            self.assertEqual(l0_schema.npx(), "npx")

    def test_openspec_is_run_through_the_resolved_npx(self) -> None:
        runner = Mock(return_value=Mock(returncode=0, stdout="", stderr=""))
        with patch("shutil.which", return_value="/opt/node/bin/npx"):
            self.assertEqual(l0_schema.check_openspec("feat", ".", runner=runner), [])
        self.assertEqual(runner.call_args[0][0][0], "/opt/node/bin/npx")


class TestTraceIsByteIdenticalAcrossOS(unittest.TestCase):
    def test_paths_use_forward_slashes_and_lines_end_in_lf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(Path(tmp))
            out = root / "trace.json"
            generate_trace({"AC-1"}, [os.path.join(tmp, "src")], [os.path.join(tmp, "tests")], str(out))
            raw = out.read_bytes()
        self.assertNotIn(b"\r\n", raw)
        self.assertNotIn(b"\\\\", raw)
        files = [loc["file"] for loc in json.loads(raw)["AC-1"]["implements"]]
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].endswith("src/impl.py"), files[0])


class TestEvidenceLines(unittest.TestCase):
    def test_green_layers_say_what_they_checked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(Path(tmp))
            code, out, _ = run_main("check", "--change", tmp, "--layers", "L2-L3",
                                    "--output", os.path.join(tmp, "trace.json"))
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(), [
            "L2 ok: 1 ACs traced: AC-1 impl=1 covers=1",
            "L3 ok: 1/1 tests passed",
        ])

    def test_l6_in_a_range_prints_no_ok_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(Path(tmp))
            _, out, err = run_main("check", "--change", tmp, "--layers", "L5-L6",
                                   "--output", os.path.join(tmp, "trace.json"))
        self.assertNotIn("L6 ok", out)
        self.assertIn("L6 is not run by the CLI", err)

    def test_each_layer_formats(self) -> None:
        self.assertEqual(cli.evidence(0, {"acs": 2, "openspec": True}),
                         "L0 ok: prd.md valid, 2 ACs; openspec validate --strict passed")
        self.assertIn("openspec not run", cli.evidence(0, {"acs": 2, "openspec": False}))
        self.assertEqual(cli.evidence(1, {"py": 3, "typed": 1, "md": 0}),
                         "L1 ok: 3 .py (1 under mypy --strict), 0 .md: ruff, mypy, vulture, banned tokens")
        self.assertTrue(cli.evidence(1, {"py": 1, "typed": 1, "md": 1}).endswith(", markdownlint"))
        self.assertEqual(cli.evidence(4, {"lines": 7}),
                         "L4 ok: 7 implementation lines executed by their own AC's tests")
        self.assertEqual(cli.evidence(5, {"mutants": 4, "killed": 4}), "L5 ok: 4/4 mutants killed")
        self.assertEqual(cli.evidence(1, {"skipped": True}), "L1 skipped: no staged .py or .md file")


class TestStagedRuns(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = make_repo(Path(self.tmp.name))
        init_repo(self.root)

    def test_staged_run_writes_no_trace(self) -> None:
        git(self.root, "add", "-A")
        out = self.root / "trace.json"
        with patch("specgate.l1_static.check", return_value=[]):
            code, _, _ = run_main("check", "--change", str(self.root), "--layers", "L1-L2",
                                  "--staged", "--output", str(out))
        self.assertEqual(code, 0)
        self.assertFalse(out.exists())

    def test_tool_failure_is_not_filtered_out_as_an_unstaged_file(self) -> None:
        git(self.root, "add", "-A")
        broken = [{"rule": "SG101", "file": "", "line": 0, "message": "ruff error: not installed"}]
        with patch("specgate.l1_static.check", return_value=broken):
            code, _, err = run_main("check", "--change", str(self.root), "--layers", "L1", "--staged")
        self.assertEqual(code, 11)
        self.assertIn("ruff error: not installed", err)

    def test_staged_path_with_a_space_survives(self) -> None:
        (self.root / "my notes.md").write_text("# hi\n")
        git(self.root, "add", "my notes.md")
        self.assertEqual(cli.staged_files(str(self.root)), ["my notes.md"])

    def test_only_yaml_staged_reports_the_skip(self) -> None:
        (self.root / "ci.yml").write_text("on: push\n")
        git(self.root, "add", "ci.yml")
        code, out, _ = run_main("check", "--change", str(self.root), "--layers", "L1", "--staged")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "L1 skipped: no staged .py or .md file")


class TestVendoredCodeIsSkipped(unittest.TestCase):
    def test_markers_under_a_specgate_skip_dir_are_not_this_repos_acs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(Path(tmp))
            vendored = root / "tools" / "specgate" / "src"
            vendored.mkdir(parents=True)
            (root / "tools" / "specgate" / ".specgate-skip").write_text("")
            (vendored / "l0.py").write_text("# implements: AC-9\ndef f():\n    return 1\n")
            code, out, err = run_main("check", "--change", tmp, "--layers", "L2",
                                      "--output", str(root / "trace.json"))
        self.assertEqual(code, 0, err)
        self.assertNotIn("AC-9", out + err)
        self.assertIn("L2 ok: 1 ACs traced: AC-1 impl=1 covers=1", out)


class TestModuleEntryPoint(unittest.TestCase):
    def test_python_dash_m_specgate(self) -> None:
        result = subprocess.run([sys.executable, "-m", "specgate", "--version"],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("specgate", result.stdout)


if __name__ == "__main__":
    unittest.main()
