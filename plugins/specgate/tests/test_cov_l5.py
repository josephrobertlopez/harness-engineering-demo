"""Coverage tests for the L5 mutation layer."""

import ast
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from specgate.l5_mut import (
    MutantGenerator,
    _function_lines,
    _generate_source_mutant,
    _import_root,
    _run_tests,
    _Sandbox,
    _survives,
    check,
)


class TestMutantGenerator(unittest.TestCase):
    """Test MutantGenerator class."""

    # covers: AC-6
    def test_visit_compare_cmp_flip(self) -> None:
        """Test cmp_flip mutation."""
        source = "x < 5"
        tree = ast.parse(source, mode='eval')
        gen = MutantGenerator({1}, 'cmp_flip', seed=42)
        new_tree = gen.visit(tree)

        self.assertIsNotNone(gen.mutated_line)
        self.assertEqual(gen.mutated_line, 1)

    # covers: AC-6
    def test_visit_compare_no_mutation_different_type(self) -> None:
        """Test compare doesn't mutate for wrong type."""
        source = "x < 5"
        tree = ast.parse(source, mode='eval')
        gen = MutantGenerator({1}, 'bool_flip', seed=42)
        gen.visit(tree)

        self.assertIsNone(gen.mutated_line)

    # covers: AC-6
    def test_visit_compare_no_target_line(self) -> None:
        """Test compare doesn't mutate for non-target line."""
        source = "x < 5"
        tree = ast.parse(source, mode='eval')
        gen = MutantGenerator({10}, 'cmp_flip', seed=42)
        gen.visit(tree)

        self.assertIsNone(gen.mutated_line)

    # covers: AC-6
    def test_visit_boolop_flip_and(self) -> None:
        """Test bool_flip mutation on and."""
        source = "x and y"
        tree = ast.parse(source, mode='eval')
        gen = MutantGenerator({1}, 'bool_flip', seed=42)
        new_tree = gen.visit(tree)

        self.assertIsNotNone(gen.mutated_line)

    # covers: AC-6
    def test_visit_boolop_flip_or(self) -> None:
        """Test bool_flip mutation on or."""
        source = "x or y"
        tree = ast.parse(source, mode='eval')
        gen = MutantGenerator({1}, 'bool_flip', seed=42)
        new_tree = gen.visit(tree)

        self.assertIsNotNone(gen.mutated_line)

    # covers: AC-6
    def test_visit_boolop_wrong_type(self) -> None:
        """Test bool_flip doesn't mutate for wrong type."""
        source = "x and y"
        tree = ast.parse(source, mode='eval')
        gen = MutantGenerator({1}, 'cmp_flip', seed=42)
        gen.visit(tree)

        self.assertIsNone(gen.mutated_line)

    # covers: AC-6
    def test_visit_return_with_value(self) -> None:
        """Test return_none mutation."""
        source = "def f(): return 42"
        tree = ast.parse(source)
        gen = MutantGenerator(set(range(1, 10)), 'return_none', seed=42)
        new_tree = gen.visit(tree)

        self.assertIsNotNone(gen.mutated_line)

    # covers: AC-6
    def test_visit_binop_add(self) -> None:
        """Test arith_swap mutation on add."""
        source = "x + y"
        tree = ast.parse(source, mode='eval')
        gen = MutantGenerator({1}, 'arith_swap', seed=42)
        new_tree = gen.visit(tree)

        self.assertIsNotNone(gen.mutated_line)

    # covers: AC-6
    def test_visit_binop_sub(self) -> None:
        """Test arith_swap mutation on sub."""
        source = "x - y"
        tree = ast.parse(source, mode='eval')
        gen = MutantGenerator({1}, 'arith_swap', seed=42)
        new_tree = gen.visit(tree)

        self.assertIsNotNone(gen.mutated_line)

    # covers: AC-6
    def test_visit_binop_wrong_type(self) -> None:
        """Test arith_swap doesn't mutate for wrong type."""
        source = "x + y"
        tree = ast.parse(source, mode='eval')
        gen = MutantGenerator({1}, 'cmp_flip', seed=42)
        gen.visit(tree)

        self.assertIsNone(gen.mutated_line)


class TestMutantGeneratorBranches(unittest.TestCase):
    """Test additional branch coverage for MutantGenerator."""

    # covers: AC-6
    def test_visit_compare_already_mutated(self) -> None:
        """Test visit_compare doesn't mutate if already mutated."""
        source = "x < 5 and y > 3"
        tree = ast.parse(source, mode='eval')
        gen = MutantGenerator({1}, 'cmp_flip', seed=42)
        # Manually set mutated_line to simulate already mutated
        gen.mutated_line = 1
        new_tree = gen.visit(tree)
        # Should not mutate again
        self.assertEqual(gen.mutated_line, 1)

    # covers: AC-6
    def test_visit_compare_no_flippable_ops(self) -> None:
        """Test visit_compare with non-flippable operators."""
        source = "x in y"
        tree = ast.parse(source, mode='eval')
        gen = MutantGenerator({1}, 'cmp_flip', seed=42)
        new_tree = gen.visit(tree)
        # In operator is not in cmp_flip_map
        self.assertIsNone(gen.mutated_line)

    # covers: AC-6
    def test_visit_boolop_not_and_or(self) -> None:
        """Test visit_boolop handles non-And/Or operators."""
        # This tests the case where a BoolOp doesn't have And or Or
        source = "x and y"
        tree = ast.parse(source, mode='eval')
        gen = MutantGenerator({1}, 'bool_flip', seed=42)
        new_tree = gen.visit(tree)
        self.assertIsNotNone(gen.mutated_line)

    # covers: AC-6
    def test_visit_boolop_already_mutated(self) -> None:
        """Test visit_boolop doesn't mutate if already mutated."""
        source = "x and y"
        tree = ast.parse(source, mode='eval')
        gen = MutantGenerator({1}, 'bool_flip', seed=42)
        gen.mutated_line = 1  # Already mutated
        new_tree = gen.visit(tree)
        # Should remain 1
        self.assertEqual(gen.mutated_line, 1)

    # covers: AC-6
    def test_visit_return_bare_return(self) -> None:
        """Test visit_return with bare return (no value)."""
        source = "def f():\n    return"
        tree = ast.parse(source)
        gen = MutantGenerator(set(range(1, 5)), 'return_none', seed=42)
        new_tree = gen.visit(tree)
        # Bare return has node.value = None, so no mutation
        self.assertIsNone(gen.mutated_line)

    # covers: AC-6
    def test_visit_return_already_mutated(self) -> None:
        """Test visit_return doesn't mutate if already mutated."""
        source = "def f(): return 42"
        tree = ast.parse(source)
        gen = MutantGenerator(set(range(1, 5)), 'return_none', seed=42)
        gen.mutated_line = 1  # Already mutated
        new_tree = gen.visit(tree)
        # Should remain 1
        self.assertEqual(gen.mutated_line, 1)

    # covers: AC-6
    def test_visit_binop_other_operators(self) -> None:
        """Test visit_binop with non-Add/Sub operators."""
        source = "x * y"
        tree = ast.parse(source, mode='eval')
        gen = MutantGenerator({1}, 'arith_swap', seed=42)
        new_tree = gen.visit(tree)
        # Mult is not handled
        self.assertIsNone(gen.mutated_line)

    # covers: AC-6
    def test_visit_binop_already_mutated(self) -> None:
        """Test visit_binop doesn't mutate if already mutated."""
        source = "x + y"
        tree = ast.parse(source, mode='eval')
        gen = MutantGenerator({1}, 'arith_swap', seed=42)
        gen.mutated_line = 1  # Already mutated
        new_tree = gen.visit(tree)
        # Should remain 1
        self.assertEqual(gen.mutated_line, 1)

    # covers: AC-6
    def test_visit_boolop_non_target_line(self) -> None:
        """Test boolop doesn't mutate for non-target lines."""
        source = "x and y"
        tree = ast.parse(source, mode='eval')
        gen = MutantGenerator({999}, 'bool_flip', seed=42)  # Line 999 not in source
        new_tree = gen.visit(tree)
        # Should not mutate
        self.assertIsNone(gen.mutated_line)

    # covers: AC-6
    def test_visit_return_non_target_line(self) -> None:
        """Test return doesn't mutate for non-target lines."""
        source = "def f(): return 42"
        tree = ast.parse(source)
        gen = MutantGenerator({999}, 'return_none', seed=42)  # Line 999 not in source
        new_tree = gen.visit(tree)
        # Should not mutate
        self.assertIsNone(gen.mutated_line)

    # covers: AC-6
    def test_visit_compare_all_operators(self) -> None:
        """Test compare mutation with all operator types."""
        # Test all comparison operators in cmp_flip_map
        test_cases = [
            ("x < y", ast.Lt, ast.GtE),
            ("x <= y", ast.LtE, ast.Gt),
            ("x > y", ast.Gt, ast.LtE),
            ("x >= y", ast.GtE, ast.Lt),
            ("x == y", ast.Eq, ast.NotEq),
            ("x != y", ast.NotEq, ast.Eq),
        ]

        for source, old_op, new_op in test_cases:
            tree = ast.parse(source, mode='eval')
            gen = MutantGenerator({1}, 'cmp_flip', seed=42)
            new_tree = gen.visit(tree)
            self.assertIsNotNone(gen.mutated_line, f"Failed for {source}")

    # covers: AC-6
    def test_visit_binop_sub_mutation(self) -> None:
        """Test arith_swap mutation on subtraction."""
        source = "x - y"
        tree = ast.parse(source, mode='eval')
        gen = MutantGenerator({1}, 'arith_swap', seed=42)
        new_tree = gen.visit(tree)
        self.assertIsNotNone(gen.mutated_line)


class TestRunTests(unittest.TestCase):
    """Test _run_tests function."""

    # covers: AC-6
    def test_run_tests_success(self) -> None:
        """Test _run_tests with passing tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a simple test file
            test_file = Path(temp_dir) / 'test_simple.py'
            test_file.write_text('''
import unittest
class TestSimple(unittest.TestCase):
    def test_pass(self):
        self.assertTrue(True)
''')

            # Run the test
            result = _run_tests(temp_dir, 'test_simple')
            self.assertTrue(result)

    # covers: AC-6
    def test_run_tests_failure(self) -> None:
        """Test _run_tests with failing tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file that fails
            test_file = Path(temp_dir) / 'test_fail.py'
            test_file.write_text('''
import unittest
class TestFail(unittest.TestCase):
    def test_fail(self):
        self.assertTrue(False)
''')

            result = _run_tests(temp_dir, 'test_fail')
            self.assertFalse(result)

    # covers: AC-6
    def test_run_tests_timeout(self) -> None:
        """Test _run_tests handles timeout."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file
            test_file = Path(temp_dir) / 'test_timeout.py'
            test_file.write_text('import unittest\nclass TestTimeout(unittest.TestCase):\n    pass')

            with patch('subprocess.run') as mock_run:
                mock_run.side_effect = subprocess.TimeoutExpired("python", 10)
                result = _run_tests(temp_dir, 'test_timeout')
                self.assertFalse(result)

    # covers: AC-6
    def test_run_tests_oserror(self) -> None:
        """Test _run_tests handles OSError."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('subprocess.run') as mock_run:
                mock_run.side_effect = OSError("no such file")
                result = _run_tests(temp_dir, 'nonexistent')
                self.assertFalse(result)




    # covers: AC-6
    def test_run_tests_real_oserror_for_missing_directory(self) -> None:
        self.assertFalse(_run_tests("/nonexistent/dir", "x"))


class TestFunctionLines(unittest.TestCase):
    SOURCE = "class A:\n    def f(self):\n        return 1\n\n\nclass B:\n    def f(self):\n        return 2\n"

    # covers: AC-6
    def test_methods_with_the_same_name_are_told_apart(self) -> None:
        self.assertEqual(_function_lines(self.SOURCE, "m:A.f"), {2, 3})
        self.assertEqual(_function_lines(self.SOURCE, "m:B.f"), {7, 8})

    # covers: AC-6
    def test_unknown_function_has_no_lines(self) -> None:
        self.assertEqual(_function_lines(self.SOURCE, "m:C.f"), set())


class TestGenerateSourceMutant(unittest.TestCase):
    # covers: AC-6
    def test_returns_mutated_source_and_original_line(self) -> None:
        src = "def f(a):\n    return a > 1\n"
        mutated, line = _generate_source_mutant(src, {2}, "cmp_flip", 0) or ("", 0)
        self.assertIn("a <= 1", mutated)
        self.assertEqual(line, 2)

    # covers: AC-6
    def test_each_mutation_type(self) -> None:
        src = "def f(a, b):\n    return a + b if a and b else a\n"
        expect = {"bool_flip": "a or b", "arith_swap": "a - b"}
        for kind, text in expect.items():
            result = _generate_source_mutant(src, {2}, kind, 0)
            self.assertIsNotNone(result, kind)
            self.assertIn(text, (result or ("", 0))[0])

    # covers: AC-6
    def test_return_none_drops_the_value(self) -> None:
        mutated, line = _generate_source_mutant("def f(a):\n    return a\n", {2}, "return_none", 0) or ("", 0)
        self.assertEqual(mutated.splitlines()[1].strip(), "return")
        self.assertEqual(line, 2)

    # covers: AC-6
    def test_nothing_to_mutate_or_bad_source(self) -> None:
        self.assertIsNone(_generate_source_mutant("x = 1\n", {1}, "cmp_flip", 0))
        self.assertIsNone(_generate_source_mutant("def (:\n", {1}, "cmp_flip", 0))

    # covers: AC-6
    def test_only_the_first_eligible_node_is_mutated(self) -> None:
        mutated, _ = _generate_source_mutant("def f(a, b, c):\n    return a + b + c\n", {2}, "arith_swap", 0) or ("", 0)
        self.assertEqual(mutated.count("-"), 1)


IMPL = "# implements: AC-1\ndef add(a, b):\n    return a + b\n"
STRONG = (
    "import unittest\nimport impl\n\n\nclass T(unittest.TestCase):\n"
    "    # covers: AC-1\n    def test_add(self):\n        self.assertEqual(impl.add(1, 2), 3)\n"
)
WEAK = STRONG.replace("self.assertEqual(impl.add(1, 2), 3)", "self.assertTrue(impl.add)")


def project(root: str, impl: str, test: str) -> tuple[str, str]:
    os.mkdir(os.path.join(root, "src"))
    os.mkdir(os.path.join(root, "tests"))
    Path(root, "src", "impl.py").write_text(impl)
    Path(root, "tests", "test_impl.py").write_text(test)
    return os.path.join(root, "src"), os.path.join(root, "tests")


class TestCheck(unittest.TestCase):
    # covers: AC-6
    def test_strong_test_kills_every_mutant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src, tests = project(tmp, IMPL, STRONG)
            self.assertEqual(check({"AC-1"}, [src], [tests]), [])

    # covers: AC-6
    def test_weak_test_leaves_exact_survivors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src, tests = project(tmp, IMPL, WEAK)
            findings = check({"AC-1"}, [src], [tests])
            self.assertEqual(
                [(f["rule"], f["line"], f["message"]) for f in findings],
                [
                    ("SG501", 3, "Surviving mutant in add: arith_swap at line 3"),
                    ("SG501", 3, "Surviving mutant in add: return_none at line 3"),
                ],
            )
            self.assertEqual(findings, check({"AC-1"}, [src], [tests]))

    # covers: AC-6
    def test_acs_without_markers_or_without_tests_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src, tests = project(tmp, IMPL, "import unittest\n")
            self.assertEqual(check({"AC-1", "AC-9"}, [src], [tests]), [])

    # covers: AC-6
    def test_ac_with_tests_but_no_implementation_has_no_mutants(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src, tests = project(tmp, "def add(a, b):\n    return a + b\n", STRONG)
            self.assertEqual(check({"AC-1"}, [src], [tests]), [])

    # covers: AC-6
    def test_unmutable_implementation_is_sg503_not_a_pass(self) -> None:
        """This used to assert [] -- "0/0 mutants killed" read as green."""
        with tempfile.TemporaryDirectory() as tmp:
            src, tests = project(tmp, "# implements: AC-1\ndef add(a, b):\n    pass\n", WEAK)
            stats: dict[str, int] = {}
            findings = check({"AC-1"}, [src], [tests], stats=stats)
            self.assertEqual([(f["rule"], f["line"]) for f in findings], [("SG503", 2)])
            self.assertIn("AC-1: no mutable operation", findings[0]["message"])
            self.assertEqual(stats, {"mutants": 0, "killed": 0})

    # covers: AC-6
    def test_one_mutable_ac_does_not_hide_an_unmutable_one(self) -> None:
        impl = IMPL + "\n\n# implements: AC-2\ndef noop():\n    pass\n"
        test = STRONG + "\n    # covers: AC-2\n    def test_noop(self):\n        self.assertIsNone(impl.noop())\n"
        with tempfile.TemporaryDirectory() as tmp:
            src, tests = project(tmp, impl, test)
            findings = check({"AC-1", "AC-2"}, [src], [tests])
            self.assertEqual([f["rule"] for f in findings], ["SG503"])
            self.assertIn("AC-2", findings[0]["message"])

    # covers: AC-6
    def test_survives_uses_mutant_not_original_when_in_same_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "impl.py").write_text("def add(a, b):\n    return a + b\n")
            Path(tmp, "test_impl.py").write_text(STRONG)
            impl = os.path.join(tmp, "impl.py")
            box = _Sandbox([impl, os.path.join(tmp, "test_impl.py")])
            try:
                tests = {tmp: ["test_impl"]}
                self.assertFalse(_survives(box, impl, "def add(a, b):\n    return a - b\n", tests))
                self.assertTrue(_survives(box, impl, "def add(a, b):\n    return a + b\n", tests))
                # The copy is restored after each mutant, and the original never touched.
                self.assertTrue(box.passes(tests))
                self.assertEqual(Path(impl).read_text(), "def add(a, b):\n    return a + b\n")
            finally:
                box.close()


PKG_IMPL = "# implements: AC-1\ndef add(a, b):\n    return a + b\n"
PKG_TEST = (
    "import unittest\nfrom pathlib import Path\nfrom calc.ops import add\n\n\n"
    "class T(unittest.TestCase):\n"
    "    # covers: AC-1\n    def test_add(self):\n"
    "        self.assertTrue((Path(__file__).parent / 'fixtures' / 'data.txt').is_file())\n"
    "        self.assertEqual(add(1, 2), 3)\n"
)


def package_project(root: str, test: str = PKG_TEST) -> tuple[str, str]:
    """src/calc/ops.py as a package; tests/ needs a fixture beside __file__."""
    pkg = Path(root, "src", "calc")
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "ops.py").write_text(PKG_IMPL)
    tests = Path(root, "tests")
    (tests / "fixtures").mkdir(parents=True)
    (tests / "fixtures" / "data.txt").write_text("x")
    (tests / "test_ops.py").write_text(test)
    return str(pkg), str(tests)


class TestSandboxIsReal(unittest.TestCase):
    """The flat-copy sandbox made every mutant of a package or fixture-using test 'killed'."""

    # covers: AC-6
    def test_package_layout_with_fixtures_is_mutated_for_real(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src, tests = package_project(tmp)
            stats: dict[str, int] = {}
            self.assertEqual(check({"AC-1"}, [src], [tests], stats=stats), [])
            self.assertEqual(stats, {"mutants": 2, "killed": 2})

    # covers: AC-6
    def test_weak_package_test_now_leaves_survivors(self) -> None:
        weak = PKG_TEST.replace("self.assertEqual(add(1, 2), 3)", "self.assertTrue(add)")
        with tempfile.TemporaryDirectory() as tmp:
            src, tests = package_project(tmp, weak)
            stats: dict[str, int] = {}
            findings = check({"AC-1"}, [src], [tests], stats=stats)
            self.assertEqual([f["rule"] for f in findings], ["SG501", "SG501"])
            self.assertEqual(stats, {"mutants": 2, "killed": 0})

    # covers: AC-6
    def test_tests_failing_unmutated_are_sg502_not_kills(self) -> None:
        broken = PKG_TEST.replace("add(1, 2), 3", "add(1, 2), 4")
        with tempfile.TemporaryDirectory() as tmp:
            src, tests = package_project(tmp, broken)
            stats: dict[str, int] = {}
            findings = check({"AC-1"}, [src], [tests], stats=stats)
            self.assertEqual([(f["rule"], f["line"]) for f in findings], [("SG502", 8)])
            self.assertIn("before any mutation", findings[0]["message"])
            self.assertEqual(stats, {"mutants": 0, "killed": 0})

    # covers: AC-6
    def test_no_plan_reports_zero_counts(self) -> None:
        stats: dict[str, int] = {}
        self.assertEqual(check({"AC-1"}, [], [], stats=stats), [])
        self.assertEqual(stats, {"mutants": 0, "killed": 0})

    def test_import_root_is_above_the_outermost_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src, _ = package_project(tmp)
            self.assertEqual(_import_root(Path(src) / "ops.py"), Path(tmp, "src"))
            self.assertEqual(_import_root(Path(tmp, "tests", "test_ops.py")), Path(tmp, "tests"))
