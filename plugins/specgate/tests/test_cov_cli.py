"""Tests for the specgate CLI: layer parsing, discovery, check_layer, main, --staged."""

import io
import os
import runpy
import subprocess
import sys
import tempfile
import unittest
import warnings
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from specgate import cli
from specgate.cli import (
    check_layer,
    extract_ac_ids,
    find_prd_file,
    find_source_and_test_dirs,
    git_env,
    main,
    parse_layers,
    staged_files,
)

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
BANNED = "# TO" "DO: later\nx = 1\n"


def make_repo(root: Path, impl: str = IMPL, test: str = TEST, prd: str = PRD) -> Path:
    """Write prd.md, src/impl.py and tests/test_impl.py under root."""
    (root / "src").mkdir()
    (root / "tests").mkdir()
    (root / "prd.md").write_text(prd)
    (root / "src" / "impl.py").write_text(impl)
    (root / "tests" / "test_impl.py").write_text(test)
    return root


def git(repo: Path, *args: str) -> str:
    """Run git against repo with the hook variables removed."""
    out = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, check=True, env=git_env(),
    )
    return out.stdout


def init_repo(root: Path) -> None:
    git(root, "init", "-q")
    git(root, "config", "user.email", "t@example.com")
    git(root, "config", "user.name", "t")


def run_main(*argv: str) -> tuple[int, str]:
    err = io.StringIO()
    with redirect_stderr(err), redirect_stdout(io.StringIO()):
        code = main(list(argv))
    return code, err.getvalue()


class TestEntryPoint(unittest.TestCase):
    def test_version_exits_zero(self) -> None:
        with redirect_stdout(io.StringIO()) as out, self.assertRaises(SystemExit) as cm:
            main(["--version"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("specgate 0.1.0", out.getvalue())

    def test_no_command_prints_help(self) -> None:
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main([]), 0)
        self.assertIn("usage: specgate", out.getvalue())

    def test_unknown_command_exits_nonzero(self) -> None:
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as cm:
            main(["bogus"])
        self.assertEqual(cm.exception.code, 2)

    def test_runs_as_module(self) -> None:
        with (
            warnings.catch_warnings(),
            patch.object(sys, "argv", ["specgate", "--help"]),
            redirect_stdout(io.StringIO()),
            self.assertRaises(SystemExit) as cm,
        ):
            warnings.simplefilter("ignore", RuntimeWarning)
            runpy.run_module("specgate.cli", run_name="__main__")
        self.assertEqual(cm.exception.code, 0)


class TestParseLayers(unittest.TestCase):
    def test_valid_specs(self) -> None:
        self.assertEqual(parse_layers("L2"), [2])
        self.assertEqual(parse_layers("L0-L2"), [0, 1, 2])
        self.assertEqual(parse_layers("L1-L1"), [1])

    def test_invalid_specs(self) -> None:
        for spec in ("L99", "L7", "L-1", "invalid", "L1-X", "L3-L1", "", "l1"):
            self.assertIsNone(parse_layers(spec), spec)

    def test_main_rejects_invalid_layers_with_exit_2(self) -> None:
        code, err = run_main("check", "--layers", "L99")
        self.assertEqual(code, 2)
        self.assertIn("invalid --layers", err)

    def test_main_rejects_l6_only_with_exit_2(self) -> None:
        code, err = run_main("check", "--layers", "L6")
        self.assertEqual(code, 2)
        self.assertIn("L6 is not run by the CLI; use run_debate()", err)

    def test_main_warns_when_range_extends_to_l6(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, err = run_main("check", "--change", tmp, "--layers", "L5-L6")
        self.assertEqual(code, 0)
        self.assertIn("warning: L6 is not run by the CLI; use run_debate()", err)


class TestDiscovery(unittest.TestCase):
    def test_find_prd_prefers_shallowest_and_skips_caches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIsNone(find_prd_file(tmp))
            (root / "a" / "b").mkdir(parents=True)
            (root / "a" / "b" / "prd.md").write_text("x")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "prd.md").write_text("x")
            self.assertEqual(find_prd_file(tmp), str(root / "a" / "b" / "prd.md"))
            (root / "a" / "prd.md").write_text("x")
            self.assertEqual(find_prd_file(tmp), str(root / "a" / "prd.md"))

    def test_extract_ac_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            prd = Path(tmp) / "prd.md"
            prd.write_text("---\nacs:\n  - id: AC-1\n  - id: AC-2\n  - nope\n  - given: x\n---\n")
            self.assertEqual(extract_ac_ids(str(prd)), {"AC-1", "AC-2"})
            prd.write_text("---\nacs: []\n---\n")
            self.assertEqual(extract_ac_ids(str(prd)), set())
            prd.write_text("---\ntitle: t\n---\n")
            self.assertEqual(extract_ac_ids(str(prd)), set())
            prd.write_text("no frontmatter")
            self.assertEqual(extract_ac_ids(str(prd)), set())
            self.assertEqual(extract_ac_ids(str(Path(tmp) / "missing.md")), set())

    def test_frontmatter_that_is_not_a_mapping_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            prd = Path(tmp) / "prd.md"
            prd.write_text("---\n- a\n- b\n---\n")
            self.assertEqual(extract_ac_ids(str(prd)), set())

    def test_find_source_and_test_dirs_follow_markers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "lib" / "src").mkdir(parents=True)
            (root / "test").mkdir()
            (root / "lib" / "src" / "a.py").write_text(IMPL)
            (root / "test" / "test_a.py").write_text("# covers: AC-1\ndef test_a():\n    assert 1\n")
            (root / ".venv" / "src").mkdir(parents=True)
            (root / ".venv" / "src" / "b.py").write_text(IMPL)
            (root / "tests" / "fixtures").mkdir(parents=True)
            (root / "tests" / "fixtures" / "c.py").write_text(IMPL)
            src, tests = find_source_and_test_dirs(tmp)
            self.assertEqual(src, [str(root / "lib" / "src")])
            self.assertEqual(tests, [str(root / "test")])

    def test_find_dirs_falls_back_then_gives_up(self) -> None:
        with tempfile.TemporaryDirectory() as empty, tempfile.TemporaryDirectory() as repo:
            make_repo(Path(repo))
            self.assertEqual(find_source_and_test_dirs(empty), ([], []))
            self.assertEqual(find_source_and_test_dirs(empty, empty), ([], []))
            src, tests = find_source_and_test_dirs(empty, repo)
            self.assertEqual((src, tests), ([str(Path(repo) / "src")], [str(Path(repo) / "tests")]))


class TestCheckLayer(unittest.TestCase):
    def test_l0_without_prd_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            findings, red = check_layer(0, change_dir=tmp)
        self.assertTrue(red)
        self.assertEqual(findings[0]["rule"], "SG006")

    def test_l0_valid_prd_is_green_and_bad_prd_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(Path(tmp))
            self.assertEqual(check_layer(0, change_dir=tmp), ([], False))
            (Path(tmp) / "prd.md").write_text("---\nacs: [{id: AC-1}]\n---\n")
            findings, red = check_layer(0, change_dir=tmp)
        self.assertTrue(red)
        self.assertIn("SG003", {f["rule"] for f in findings})

    def test_l0_runs_openspec_only_when_an_openspec_dir_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(Path(tmp))
            with patch("specgate.l0_schema.check", return_value=[]) as fake:
                check_layer(0, change_dir=tmp, cwd=tmp)
                fake.assert_called_once_with(str(root / "prd.md"), None, None)
            (root / "openspec").mkdir()
            with patch("specgate.l0_schema.check", return_value=[]) as fake:
                check_layer(0, change_dir=tmp, cwd=tmp)
                fake.assert_called_once_with(str(root / "prd.md"), root.name, tmp)

    def test_l1_passes_python_and_markdown_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(Path(tmp))
            with patch("specgate.l1_static.check", return_value=[]) as fake:
                self.assertEqual(check_layer(1, change_dir=tmp), ([], False))
            py, = fake.call_args.args
            self.assertEqual(sorted(Path(p).name for p in py), ["impl.py", "test_impl.py"])
            self.assertEqual(fake.call_args.kwargs["md_paths"], [str(root / "prd.md")])

    def test_l1_green_in_empty_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(check_layer(1, change_dir=tmp), ([], False))

    def test_l2_flags_test_without_implementation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(Path(tmp), impl="def add(a, b):\n    return a + b\n")
            findings, red = check_layer(2, change_dir=tmp)
        self.assertTrue(red)
        self.assertEqual({f["rule"] for f in findings}, {"SG201"})

    def test_l3_uses_given_junit_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(Path(tmp))
            junit = os.path.join(tmp, "out.xml")
            self.assertEqual(check_layer(3, change_dir=tmp, junit_path=junit), ([], False))
            self.assertIn('name="ac"', Path(junit).read_text())

    def test_l3_default_junit_leaves_no_file_behind(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(Path(tmp))
            before = sorted(os.listdir(tmp))
            self.assertEqual(check_layer(3, change_dir=tmp), ([], False))
            self.assertEqual(sorted(os.listdir(tmp)), before)

    def test_l4_and_l5_green_on_covered_strong_test(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(Path(tmp))
            self.assertEqual(check_layer(4, change_dir=tmp), ([], False))
            self.assertEqual(check_layer(5, change_dir=tmp), ([], False))

    def test_l5_flags_surviving_mutant(self) -> None:
        weak = TEST.replace("self.assertEqual(add(1, 2), 3)", "self.assertTrue(add)")
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(Path(tmp), test=weak)
            findings, red = check_layer(5, change_dir=tmp)
        self.assertTrue(red)
        self.assertEqual({f["rule"] for f in findings}, {"SG501"})

    def test_layers_after_l0_skip_when_no_prd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for layer in (2, 3, 4, 5):
                self.assertEqual(check_layer(layer, change_dir=tmp), ([], False))

    def test_l6_and_unknown_layers_are_not_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(Path(tmp))
            self.assertEqual(check_layer(6, change_dir=tmp), ([], False))
            self.assertEqual(check_layer(99, change_dir=tmp), ([], False))

    def test_defaults_to_cwd_then_dot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(check_layer(0, cwd=tmp)[1])
            old = os.getcwd()
            os.chdir(tmp)
            try:
                self.assertTrue(check_layer(0)[1])
            finally:
                os.chdir(old)


class TestMain(unittest.TestCase):
    def test_green_run_writes_identical_trace_twice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            make_repo(repo)
            out = Path(tmp) / "trace.json"
            with patch("specgate.l1_static.check", return_value=[]):
                self.assertEqual(run_main("check", "--change", str(repo), "--output", str(out))[0], 0)
                first = out.read_bytes()
                out.unlink()
                self.assertEqual(run_main("check", "--change", str(repo), "--output", str(out))[0], 0)
            self.assertEqual(out.read_bytes(), first)
            self.assertIn(b'"AC-1"', first)
            self.assertIn(b"impl.py", first)

    def test_red_layer_exit_code_is_10_plus_layer_and_no_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            make_repo(root, impl="def add(a, b):\n    return a + b\n")
            out = Path(tmp) / "trace.json"
            with patch("specgate.l1_static.check", return_value=[]):
                code, err = run_main("check", "--change", str(root), "--layers", "L0-L5",
                                     "--output", str(out))
            self.assertEqual(code, 12)
            self.assertIn("L2 SG201", err)
            self.assertFalse(out.exists())

    def test_stops_at_first_red_layer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch("specgate.cli.check_layer", return_value=([{
                "rule": "SG000", "file": "f", "line": 1, "message": "m"}], True)) as fake:
                code, _ = run_main("check", "--change", tmp, "--layers", "L0-L5")
        self.assertEqual(code, 10)
        self.assertEqual(fake.call_count, 1)

    def test_no_prd_means_no_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "trace.json"
            code, _ = run_main("check", "--change", tmp, "--layers", "L5", "--output", str(out))
            self.assertEqual(code, 0)
            self.assertFalse(out.exists())

    def test_default_change_is_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old = os.getcwd()
            os.chdir(tmp)
            try:
                code, _ = run_main("check", "--layers", "L0")
            finally:
                os.chdir(old)
        self.assertEqual(code, 10)


class TestStaged(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        init_repo(self.root)
        patcher = [
            patch("specgate.l1_static.check_ruff", return_value=[]),
            patch("specgate.l1_static.check_mypy", return_value=[]),
            patch("specgate.l1_static.check_vulture", return_value=[]),
        ]
        for p in patcher:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.tmp.cleanup)

    def run_staged(self) -> tuple[int, str]:
        return run_main("check", "--change", str(self.root), "--layers", "L1", "--staged",
                        "--output", str(self.root / "trace.json"))

    def test_nothing_staged_is_green_even_with_bad_files(self) -> None:
        (self.root / "bad.py").write_text(BANNED)
        code, err = self.run_staged()
        self.assertEqual(code, 0)
        self.assertIn("nothing staged", err)

    def test_unstaged_bad_file_is_ignored(self) -> None:
        (self.root / "src").mkdir()
        (self.root / "src" / "good.py").write_text("x = 1\n")
        (self.root / "src" / "bad.py").write_text(BANNED)
        git(self.root, "add", "src/good.py")
        self.assertEqual(staged_files(str(self.root)), ["src/good.py"])
        self.assertEqual(self.run_staged()[0], 0)

    def test_staged_bad_file_is_red(self) -> None:
        (self.root / "src").mkdir()
        (self.root / "src" / "bad.py").write_text(BANNED)
        git(self.root, "add", "src/bad.py")
        code, err = self.run_staged()
        self.assertEqual(code, 11)
        self.assertIn("SG104", err)

    def test_staged_fixture_file_is_ignored(self) -> None:
        fixtures = self.root / "tests" / "fixtures"
        fixtures.mkdir(parents=True)
        (fixtures / "bad_tokens.py").write_text(BANNED)
        git(self.root, "add", "-A")
        (self.root / "src").mkdir()
        (self.root / "src" / "ok.py").write_text("x = 1\n")
        git(self.root, "add", "src/ok.py")
        self.assertEqual(self.run_staged()[0], 0)

    def test_only_non_code_files_staged_runs_nothing(self) -> None:
        (self.root / "notes.txt").write_text("hi")
        git(self.root, "add", "notes.txt")
        self.assertEqual(check_layer(1, change_dir=str(self.root),
                                     only=frozenset({str(self.root / "notes.txt")})), ([], False))

    def test_staged_files_outside_a_repo_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as plain:
            with patch.dict(os.environ, {"GIT_CEILING_DIRECTORIES": str(Path(plain).parent)}):
                self.assertEqual(staged_files(plain), [])


class TestGitIsolation(unittest.TestCase):
    def test_git_env_strips_hook_variables(self) -> None:
        bogus = {"GIT_DIR": "/nonexistent", "GIT_WORK_TREE": "/nonexistent",
                 "GIT_INDEX_FILE": "/nonexistent"}
        with patch.dict(os.environ, bogus):
            env = git_env()
        for name in bogus:
            self.assertNotIn(name, env)
        self.assertIn("PATH", env)

    def test_bogus_git_dir_never_reaches_the_real_repo(self) -> None:
        here = Path(__file__).resolve().parent
        probe = subprocess.run(["git", "-C", str(here), "rev-parse", "HEAD"],
                               capture_output=True, text=True, check=False, env=git_env())
        before = probe.stdout.strip()
        bogus = {"GIT_DIR": "/nonexistent/.git", "GIT_WORK_TREE": "/nonexistent",
                 "GIT_INDEX_FILE": "/nonexistent/index"}
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, bogus):
            root = Path(tmp)
            init_repo(root)
            (root / "a.py").write_text("x = 1\n")
            git(root, "add", "a.py")
            git(root, "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "fixture")
            (root / "b.py").write_text("y = 2\n")
            git(root, "add", "b.py")
            self.assertEqual(staged_files(tmp), ["b.py"])
            self.assertEqual(git(root, "log", "--format=%s").split(), ["fixture"])
        after = subprocess.run(["git", "-C", str(here), "rev-parse", "HEAD"],
                               capture_output=True, text=True, check=False, env=git_env())
        self.assertEqual(after.stdout.strip(), before)
        self.assertTrue(cli.__file__)


if __name__ == "__main__":
    unittest.main()
