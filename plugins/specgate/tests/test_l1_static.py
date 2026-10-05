"""Tests for L1 static analysis layer."""

import unittest
import unittest.mock
import shutil
import tempfile
from pathlib import Path
from specgate.l1_static import (
    check_ruff, check_mypy, check_vulture, check_banned_tokens,
    check_markdownlint, check
)


class TestL1Ruff(unittest.TestCase):
    """Test SG101: ruff violations (F401, ERA, T20)."""

    # covers: AC-2
    def test_bad_f401_fixture(self):
        """Red fixture should fail SG101 check."""
        fixture_path = str(Path(__file__).parent / "fixtures" / "l1" / "bad_f401.py")
        findings = check_ruff([fixture_path])

        # Should have at least one SG101 finding
        sg101_findings = [f for f in findings if f['rule'] == 'SG101']
        self.assertTrue(len(sg101_findings) > 0,
                       f"Expected SG101 findings for bad_f401.py, got: {findings}")
        self.assertEqual(sg101_findings[0]['rule'], 'SG101')

    def test_good_f401_fixture(self):
        """Green fixture should pass SG101 check."""
        fixture_path = str(Path(__file__).parent / "fixtures" / "l1" / "good_f401.py")
        findings = check_ruff([fixture_path])

        # Should have no SG101 findings
        sg101_findings = [f for f in findings if f['rule'] == 'SG101']
        self.assertEqual(len(sg101_findings), 0,
                        f"Expected no SG101 findings for good_f401.py, got: {sg101_findings}")


class TestL1Mypy(unittest.TestCase):
    """Test SG102: mypy --strict violations."""

    # covers: AC-2
    def test_mypy_with_injected_runner(self):
        """Test mypy with injected runner that simulates failure."""
        def fake_runner(*args, **kwargs):
            result = unittest.mock.Mock()
            result.returncode = 1
            result.stdout = "bad_mypy.py:2:0: error: Function is missing a type annotation for one or more arguments\n"
            return result

        findings = check_mypy(['dummy.py'], runner=fake_runner)

        # Should have at least one SG102 finding
        sg102_findings = [f for f in findings if f['rule'] == 'SG102']
        self.assertTrue(len(sg102_findings) > 0,
                       f"Expected SG102 findings, got: {findings}")
        self.assertEqual(sg102_findings[0]['rule'], 'SG102')

    def test_mypy_green_with_injected_runner(self):
        """Test mypy green path with injected runner."""
        def fake_runner(*args, **kwargs):
            result = unittest.mock.Mock()
            result.returncode = 0
            result.stdout = ""
            return result

        findings = check_mypy(['dummy.py'], runner=fake_runner)

        # Should have no SG102 findings
        sg102_findings = [f for f in findings if f['rule'] == 'SG102']
        self.assertEqual(len(sg102_findings), 0,
                        f"Expected no SG102 findings, got: {findings}")


class TestL1Vulture(unittest.TestCase):
    """Test SG103: vulture dead code detection."""

    # covers: AC-2
    def test_vulture_with_injected_runner(self):
        """Test vulture with injected runner that simulates failure."""
        def fake_runner(*args, **kwargs):
            result = unittest.mock.Mock()
            result.returncode = 1
            result.stdout = "bad_vulture.py:6: unused variable 'unused_var' (90% confidence)\n"
            return result

        findings = check_vulture(['dummy.py'], runner=fake_runner)

        # Should have at least one SG103 finding
        sg103_findings = [f for f in findings if f['rule'] == 'SG103']
        self.assertTrue(len(sg103_findings) > 0,
                       f"Expected SG103 findings, got: {findings}")
        self.assertEqual(sg103_findings[0]['rule'], 'SG103')

    def test_vulture_green_with_injected_runner(self):
        """Test vulture green path with injected runner."""
        def fake_runner(*args, **kwargs):
            result = unittest.mock.Mock()
            result.returncode = 0
            result.stdout = ""
            return result

        findings = check_vulture(['dummy.py'], runner=fake_runner)

        # Should have no SG103 findings
        sg103_findings = [f for f in findings if f['rule'] == 'SG103']
        self.assertEqual(len(sg103_findings), 0,
                        f"Expected no SG103 findings, got: {findings}")


class TestL1BannedTokens(unittest.TestCase):
    """Test SG104: banned token detection."""

    # covers: AC-2
    def test_bad_tokens_fixture(self):
        """The red fixture is test data: only a copy outside tests/fixtures is scanned."""
        fixture = Path(__file__).parent / "fixtures" / "l1" / "bad_tokens.py"
        self.assertEqual(check_banned_tokens([str(fixture)]), [])
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "bad_tokens.py"
            shutil.copy(fixture, copy)
            findings = check_banned_tokens([str(copy)])
        found = " ".join(f["message"] for f in findings)
        self.assertTrue(all(f["rule"] == "SG104" for f in findings))
        for token in ("TO" "DO", "FIX" "ME", "X" "XX"):
            self.assertIn(token, found)

    def test_fixture_directory_is_ignored(self):
        """A banned token under tests/fixtures is ignored; the same file elsewhere is not."""
        with tempfile.TemporaryDirectory() as tmp:
            fixtures = Path(tmp) / "tests" / "fixtures"
            fixtures.mkdir(parents=True)
            data = fixtures / "data.py"
            data.write_text("# TO" "DO: data\n")
            other = Path(tmp) / "tests" / "test_x.py"
            other.write_text("# TO" "DO: real\n")
            self.assertEqual(check_banned_tokens([str(data)]), [])
            self.assertEqual(len(check_banned_tokens([str(other)])), 1)

    def test_good_tokens_fixture(self):
        """Green fixture should have no banned tokens."""
        fixture_path = str(Path(__file__).parent / "fixtures" / "l1" / "good_tokens.py")
        findings = check_banned_tokens([fixture_path])

        # Should have no SG104 findings
        sg104_findings = [f for f in findings if f['rule'] == 'SG104']
        self.assertEqual(len(sg104_findings), 0,
                        f"Expected no SG104 findings for good_tokens.py, got: {sg104_findings}")


class TestL1Markdownlint(unittest.TestCase):
    """Test SG105: markdownlint violations."""

    # covers: AC-8
    def test_markdownlint_with_injected_runner(self):
        """Test markdownlint with injected runner that simulates failure."""
        def fake_runner(*args, **kwargs):
            result = unittest.mock.Mock()
            result.returncode = 1
            result.stdout = "bad_markdown.md:3:1 MD001 Heading levels should increase by one level at a time\n"
            return result

        findings = check_markdownlint(['dummy.md'], runner=fake_runner)

        # Should have at least one SG105 finding
        sg105_findings = [f for f in findings if f['rule'] == 'SG105']
        self.assertTrue(len(sg105_findings) > 0,
                       f"Expected SG105 findings, got: {findings}")
        self.assertEqual(sg105_findings[0]['rule'], 'SG105')

    def test_markdownlint_green_with_injected_runner(self):
        """Test markdownlint green path with injected runner."""
        def fake_runner(*args, **kwargs):
            result = unittest.mock.Mock()
            result.returncode = 0
            result.stdout = ""
            return result

        findings = check_markdownlint(['dummy.md'], runner=fake_runner)

        # Should have no SG105 findings
        sg105_findings = [f for f in findings if f['rule'] == 'SG105']
        self.assertEqual(len(sg105_findings), 0,
                        f"Expected no SG105 findings, got: {findings}")


class TestL1Check(unittest.TestCase):
    """Test combined check function."""

    def test_check_with_injected_runner(self):
        """Test check function with all tools passing."""
        def fake_runner(*args, **kwargs):
            result = unittest.mock.Mock()
            result.returncode = 0
            result.stdout = ""
            return result

        findings = check([], md_paths=[], runner=fake_runner)

        # Should have no findings
        self.assertEqual(len(findings), 0,
                        f"Expected no findings, got: {findings}")

    def test_check_combines_all_results(self):
        """Test that check combines results from multiple tools."""
        def fake_runner(*args, **kwargs):
            # Simulate ruff failure
            if 'ruff' in args[0]:
                result = unittest.mock.Mock()
                result.returncode = 1
                result.stdout = json.dumps([{
                    'filename': 'test.py',
                    'location': {'row': 5},
                    'message': 'F401 unused import'
                }])
                return result
            # Simulate markdownlint failure
            elif 'markdownlint' in str(args[0]):
                result = unittest.mock.Mock()
                result.returncode = 1
                result.stdout = "test.md:3:1 MD001 Heading error\n"
                return result
            else:
                result = unittest.mock.Mock()
                result.returncode = 0
                result.stdout = ""
                return result

        import json
        findings = check(['test.py'], md_paths=['test.md'], runner=fake_runner)

        # Should have findings from both ruff and markdownlint
        rules = {f['rule'] for f in findings}
        self.assertIn('SG101', rules, f"Expected SG101 in rules, got: {rules}")


if __name__ == '__main__':
    unittest.main()
