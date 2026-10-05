"""Tests for the L4 layer: per-AC line coverage measured in a child process."""

import ast
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from specgate.l2_trace import MarkerLocation
from specgate.l4_cov import _covered_lines, _executable_lines, _impl_lines, check

HEADER = (
    "import sys\nimport unittest\nfrom pathlib import Path\n"
    "sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))\n"
    "import impl\n\n\n"
)


def func(source: str) -> ast.FunctionDef:
    node = ast.parse(source).body[0]
    assert isinstance(node, ast.FunctionDef)
    return node


def build(root: Path, impl_src: str, test_body: str) -> tuple[str, str]:
    (root / "src").mkdir()
    (root / "tests").mkdir()
    (root / "src" / "impl.py").write_text(impl_src)
    (root / "tests" / "test_impl.py").write_text(HEADER + test_body)
    return str(root / "src"), str(root / "tests")


BRANCHY = (
    "# implements: AC-1\n"
    "def sign(x):\n"
    "    if x > 0:\n"
    "        return 1\n"
    "    return -1\n"
)
TEST_POSITIVE_ONLY = (
    "class T(unittest.TestCase):\n"
    "    # covers: AC-1\n"
    "    def test_pos(self):\n"
    "        self.assertEqual(impl.sign(5), 1)\n"
)


class TestExecutableLines(unittest.TestCase):
    # covers: AC-5
    def test_docstring_is_excluded(self) -> None:
        node = func('def f():\n    """doc"""\n    x = 1\n    return x\n')
        self.assertEqual(_executable_lines(node), [3, 4])

    # covers: AC-5
    def test_without_docstring_and_nested_statements(self) -> None:
        node = func("def f(a):\n    if a:\n        return 1\n    return 2\n")
        self.assertEqual(_executable_lines(node), [2, 3, 4])

    # covers: AC-5
    def test_non_string_first_expression_is_a_statement(self) -> None:
        node = func("def f():\n    1\n    return 2\n")
        self.assertEqual(_executable_lines(node), [2, 3])


class TestImplLines(unittest.TestCase):
    def marker(self, path: Path, qualname: str) -> MarkerLocation:
        return MarkerLocation(str(path), "m", 1, "AC-1", "implements", qualname)

    # covers: AC-5
    def test_method_and_missing_function(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "impl.py"
            src.write_text("class C:\n    def m(self):\n        return 1\n")
            self.assertEqual(_impl_lines(self.marker(src, "impl:C.m")), [3])
            self.assertEqual(_impl_lines(self.marker(src, "impl:C.gone")), [])


class TestCoveredLines(unittest.TestCase):
    # covers: AC-5
    def test_runs_only_the_named_tests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src, tests = build(
                Path(tmp), BRANCHY,
                TEST_POSITIVE_ONLY.replace("impl.sign(5), 1)", "impl.sign(5), 1)\n"
                "    def test_neg(self):\n        self.assertEqual(impl.sign(-5), -1)"),
            )
            real = os.path.realpath(os.path.join(src, "impl.py"))
            only_pos = _covered_lines(tests, ["test_impl.T.test_pos"])
            self.assertIn((real, 4), only_pos)
            self.assertNotIn((real, 5), only_pos)
            both = _covered_lines(tests, ["test_impl.T.test_pos", "test_impl.T.test_neg"])
            self.assertIn((real, 5), both)

    # covers: AC-5
    def test_unloadable_test_yields_no_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(_covered_lines(tmp, ["no_such_module.T.test"]), set())

    # covers: AC-5
    def test_ambient_coverage_environment_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src, tests = build(Path(tmp), BRANCHY, TEST_POSITIVE_ONLY)
            with patch.dict(os.environ, {"COVERAGE_FILE": os.path.join(tmp, "elsewhere")}):
                lines = _covered_lines(tests, ["test_impl.T.test_pos"])
            self.assertTrue(lines)
            self.assertFalse(os.path.exists(os.path.join(tmp, "elsewhere")))


class TestCheck(unittest.TestCase):
    # covers: AC-5
    def test_fully_covered_ac_is_green(self) -> None:
        body = TEST_POSITIVE_ONLY.replace("sign(5), 1)", "sign(5), 1)\n        self.assertEqual(impl.sign(-5), -1)")
        with tempfile.TemporaryDirectory() as tmp:
            src, tests = build(Path(tmp), BRANCHY, body)
            self.assertEqual(check({"AC-1"}, [src], [tests]), [])

    # covers: AC-5
    def test_unexecuted_line_is_sg401_with_exact_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src, tests = build(Path(tmp), BRANCHY, TEST_POSITIVE_ONLY)
            findings = check({"AC-1"}, [src], [tests])
            self.assertEqual([(f["rule"], f["line"]) for f in findings], [("SG401", 5)])
            self.assertIn("AC-1", findings[0]["message"])
            self.assertEqual(findings, check({"AC-1"}, [src], [tests]))

    # covers: AC-5
    def test_other_tests_do_not_count_for_the_ac(self) -> None:
        body = (
            "class T(unittest.TestCase):\n"
            "    # covers: AC-1\n    def test_pos(self):\n"
            "        self.assertEqual(impl.sign(5), 1)\n"
            "    def test_unmarked(self):\n"
            "        self.assertEqual(impl.sign(-5), -1)\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            src, tests = build(Path(tmp), BRANCHY, body)
            self.assertEqual([f["line"] for f in check({"AC-1"}, [src], [tests])], [5])

    # covers: AC-5
    def test_acs_missing_an_implementation_or_a_test_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src, tests = build(Path(tmp), BRANCHY, "")
            self.assertEqual(check({"AC-1"}, [src], [tests]), [])
        with tempfile.TemporaryDirectory() as tmp:
            src, tests = build(Path(tmp), "def sign(x):\n    return x\n", TEST_POSITIVE_ONLY)
            self.assertEqual(check({"AC-1"}, [src], [tests]), [])

    # covers: AC-5
    def test_tests_in_two_directories_are_pooled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src, tests = build(root, BRANCHY, TEST_POSITIVE_ONLY)
            other = root / "more"
            other.mkdir()
            (other / "test_neg.py").write_text(
                HEADER.replace("parent.parent", "parent.parent")
                + "class N(unittest.TestCase):\n    # covers: AC-1\n    def test_neg(self):\n"
                "        self.assertEqual(impl.sign(-5), -1)\n"
            )
            self.assertEqual(check({"AC-1"}, [src], [tests, str(other)]), [])

    # covers: AC-5
    def test_nothing_is_written_into_the_working_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src, tests = build(Path(tmp), BRANCHY, TEST_POSITIVE_ONLY)
            before = sorted(os.listdir("."))
            check({"AC-1"}, [src], [tests])
            self.assertEqual(sorted(os.listdir(".")), before)
            self.assertEqual(sorted(os.listdir(tests)), ["test_impl.py"])

    # covers: AC-5
    def test_marker_on_missing_function_adds_no_lines(self) -> None:
        marker = MarkerLocation("x.py", "f", 1, "AC-1", "implements", "x:f")
        with tempfile.TemporaryDirectory() as tmp:
            src, tests = build(Path(tmp), BRANCHY, TEST_POSITIVE_ONLY)
            with patch("specgate.l4_cov._impl_lines", return_value=[]):
                self.assertEqual(check({"AC-1"}, [src], [tests]), [])
        self.assertEqual(marker.ac_id, "AC-1")


if __name__ == "__main__":
    unittest.main()
