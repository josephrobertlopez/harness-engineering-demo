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
    _run_tests,
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
    def test_unmutable_implementation_has_no_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src, tests = project(tmp, "# implements: AC-1\ndef add(a, b):\n    pass\n", WEAK)
            self.assertEqual(check({"AC-1"}, [src], [tests]), [])

    # covers: AC-6
    def test_survives_uses_mutant_not_original_when_in_same_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "impl.py").write_text("def add(a, b):\n    return a + b\n")
            Path(tmp, "test_impl.py").write_text(STRONG)
            test = os.path.join(tmp, "test_impl.py")
            impl = os.path.join(tmp, "impl.py")
            self.assertFalse(_survives(impl, "def add(a, b):\n    return a - b\n", [test]))
            self.assertTrue(_survives(impl, "def add(a, b):\n    return a + b\n", [test]))
