"""Coverage tests for L1 layer (static analysis)."""

import unittest
import os
import tempfile
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from specgate.l1_static import check_ruff, check_mypy, check_vulture, check_banned_tokens, check_markdownlint, check


class TestCheckRuff(unittest.TestCase):
    """Test ruff checking."""

    # covers: AC-2
    def test_check_ruff_empty_paths(self) -> None:
        """Test ruff with empty paths."""
        findings = check_ruff([])
        self.assertEqual(len(findings), 0)

    # covers: AC-2
    def test_check_ruff_success(self) -> None:
        """Test successful ruff check."""
        mock_runner = Mock()
        mock_runner.return_value = Mock(returncode=0, stdout='', stderr='')

        findings = check_ruff(['test.py'], runner=mock_runner)
        self.assertEqual(len(findings), 0)

    # covers: AC-2
    def test_check_ruff_failure(self) -> None:
        """Test failed ruff check."""
        mock_runner = Mock()
        output = [
            {'filename': 'test.py', 'location': {'row': 10}, 'message': 'unused import'},
            {'filename': 'test.py', 'location': {'row': 20}, 'message': 'print statement'}
        ]
        mock_runner.return_value = Mock(returncode=1, stdout=json.dumps(output), stderr='')

        findings = check_ruff(['test.py'], runner=mock_runner)
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0]['rule'], 'SG101')
        self.assertEqual(findings[0]['line'], 10)

    # covers: AC-2
    def test_check_ruff_invalid_json(self) -> None:
        """Test ruff with invalid JSON output."""
        mock_runner = Mock()
        mock_runner.return_value = Mock(returncode=1, stdout='not json', stderr='error message')

        findings = check_ruff(['test.py'], runner=mock_runner)
        self.assertEqual(len(findings), 1)
        self.assertIn('error message', findings[0]['message'])

    # covers: AC-2
    def test_check_ruff_exception(self) -> None:
        """Test ruff check with exception."""
        mock_runner = Mock()
        mock_runner.side_effect = OSError("command not found")

        findings = check_ruff(['test.py'], runner=mock_runner)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]['rule'], 'SG101')

    # covers: AC-2
    def test_check_ruff_malformed_location(self) -> None:
        """Test ruff with malformed location."""
        mock_runner = Mock()
        output = [
            {'filename': 'test.py', 'location': 'not a dict', 'message': 'error'},
        ]
        mock_runner.return_value = Mock(returncode=1, stdout=json.dumps(output), stderr='')

        findings = check_ruff(['test.py'], runner=mock_runner)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]['line'], 0)

    # covers: AC-2
    def test_check_ruff_empty_stdout_with_stderr(self) -> None:
        """Test ruff with empty stdout but non-empty stderr (line 51, 66 branch coverage)."""
        mock_runner = Mock()
        mock_runner.return_value = Mock(returncode=1, stdout='', stderr='command failed')

        findings = check_ruff(['test.py'], runner=mock_runner)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]['rule'], 'SG101')
        self.assertIn('command failed', findings[0]['message'])


class TestCheckMypy(unittest.TestCase):
    """Test mypy checking."""

    # covers: AC-2
    def test_check_mypy_empty_paths(self) -> None:
        """Test mypy with empty paths."""
        findings = check_mypy([])
        self.assertEqual(len(findings), 0)

    # covers: AC-2
    def test_check_mypy_success(self) -> None:
        """Test successful mypy check."""
        mock_runner = Mock()
        mock_runner.return_value = Mock(returncode=0, stdout='', stderr='')

        findings = check_mypy(['test.py'], runner=mock_runner)
        self.assertEqual(len(findings), 0)

    # covers: AC-2
    def test_check_mypy_failure(self) -> None:
        """Test failed mypy check."""
        mock_runner = Mock()
        mock_runner.return_value = Mock(
            returncode=1,
            stdout='test.py:10:5: error: Name "x" is not defined [name-defined]\n',
            stderr=''
        )

        findings = check_mypy(['test.py'], runner=mock_runner)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]['rule'], 'SG102')
        self.assertEqual(findings[0]['line'], 10)

    # covers: AC-2
    def test_check_mypy_exception(self) -> None:
        """Test mypy check with exception."""
        mock_runner = Mock()
        mock_runner.side_effect = OSError("command not found")

        findings = check_mypy(['test.py'], runner=mock_runner)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]['rule'], 'SG102')

    # covers: AC-2
    def test_check_mypy_malformed_output(self) -> None:
        """Test mypy with malformed output."""
        mock_runner = Mock()
        mock_runner.return_value = Mock(
            returncode=1,
            stdout='malformed output\ninvalid line\n',
            stderr=''
        )

        findings = check_mypy(['test.py'], runner=mock_runner)
        self.assertEqual(len(findings), 0)


class TestCheckVulture(unittest.TestCase):
    """Test vulture checking."""

    # covers: AC-2
    def test_check_vulture_empty_paths(self) -> None:
        """Test vulture with empty paths."""
        findings = check_vulture([])
        self.assertEqual(len(findings), 0)

    # covers: AC-2
    def test_check_vulture_success(self) -> None:
        """Test successful vulture check."""
        mock_runner = Mock()
        mock_runner.return_value = Mock(returncode=0, stdout='', stderr='')

        findings = check_vulture(['test.py'], runner=mock_runner)
        self.assertEqual(len(findings), 0)

    # covers: AC-2
    def test_check_vulture_failure(self) -> None:
        """Test failed vulture check."""
        mock_runner = Mock()
        mock_runner.return_value = Mock(
            returncode=1,
            stdout='test.py:10: unused variable "x" (90% confidence)\n',
            stderr=''
        )

        findings = check_vulture(['test.py'], runner=mock_runner)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]['rule'], 'SG103')
        self.assertEqual(findings[0]['line'], 10)

    # covers: AC-2
    def test_check_vulture_exception(self) -> None:
        """Test vulture check with exception."""
        mock_runner = Mock()
        mock_runner.side_effect = OSError("command not found")

        findings = check_vulture(['test.py'], runner=mock_runner)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]['rule'], 'SG103')


class TestCheckBannedTokens(unittest.TestCase):
    """Test banned tokens checking."""

    # covers: AC-2
    def test_check_banned_tokens_empty(self) -> None:
        """Test banned tokens with empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("# valid code\n")
            path = f.name

        try:
            findings = check_banned_tokens([path])
            self.assertEqual(len(findings), 0)
        finally:
            Path(path).unlink()

    # covers: AC-2
    def test_check_banned_tokens_todo(self) -> None:
        """Test banned tokens finds banned-token."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("# TO" "DO: fix this\n")
            path = f.name

        try:
            findings = check_banned_tokens([path])
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]['rule'], 'SG104')
            self.assertIn('TO' 'DO', findings[0]['message'])
        finally:
            Path(path).unlink()

    # covers: AC-2
    def test_check_banned_tokens_fixme(self) -> None:
        """Test banned tokens finds banned-token."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("x = 1  # FIX" "ME: this\n")
            path = f.name

        try:
            findings = check_banned_tokens([path])
            self.assertEqual(len(findings), 1)
            self.assertIn('FIX' 'ME', findings[0]['message'])
        finally:
            Path(path).unlink()

    # covers: AC-2
    def test_check_banned_tokens_xxx(self) -> None:
        """Test banned tokens finds banned-token."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("# X" "XX: hack\n")
            path = f.name

        try:
            findings = check_banned_tokens([path])
            self.assertEqual(len(findings), 1)
            self.assertIn('X' 'XX', findings[0]['message'])
        finally:
            Path(path).unlink()

    # covers: AC-2
    def test_check_banned_tokens_skip(self) -> None:
        """Test banned tokens finds banned-token."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def skip" "Test(self): pass\n")
            path = f.name

        try:
            findings = check_banned_tokens([path])
            self.assertEqual(len(findings), 1)
            self.assertIn('skip', findings[0]['message'])
        finally:
            Path(path).unlink()

    # covers: AC-2
    def test_check_banned_tokens_file_error(self) -> None:
        """Test banned tokens with unreadable file."""
        findings = check_banned_tokens(['/nonexistent/file.py'])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]['rule'], 'SG104')


class TestCheckMarkdownlint(unittest.TestCase):
    """Test markdownlint checking."""

    # covers: AC-8
    def test_check_markdownlint_empty(self) -> None:
        """Test markdownlint with empty paths."""
        findings = check_markdownlint([])
        self.assertEqual(len(findings), 0)

    # covers: AC-8
    def test_check_markdownlint_success(self) -> None:
        """Test successful markdownlint check."""
        mock_runner = Mock()
        mock_runner.return_value = Mock(returncode=0, stdout='', stderr='')

        findings = check_markdownlint(['test.md'], runner=mock_runner)
        self.assertEqual(len(findings), 0)

    # covers: AC-8
    def test_check_markdownlint_failure(self) -> None:
        """Test failed markdownlint check."""
        mock_runner = Mock()
        mock_runner.return_value = Mock(
            returncode=1,
            stdout='test.md:10:4 MD001 Title level violation\n',
            stderr=''
        )

        findings = check_markdownlint(['test.md'], runner=mock_runner)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]['rule'], 'SG105')
        self.assertEqual(findings[0]['line'], 10)

    # covers: AC-8
    def test_check_markdownlint_exception(self) -> None:
        """Test markdownlint check with exception."""
        mock_runner = Mock()
        mock_runner.side_effect = OSError("command not found")

        findings = check_markdownlint(['test.md'], runner=mock_runner)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]['rule'], 'SG105')


class TestCheck(unittest.TestCase):
    """Test combined check function."""

    # covers: AC-2
    def test_check_python_only(self) -> None:
        """Test check with Python files only."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("# valid\n")
            path = f.name

        try:
            mock_runner = Mock()
            mock_runner.return_value = Mock(returncode=0, stdout='', stderr='')

            findings = check([path], runner=mock_runner)
            # Should run all Python checks
            mock_runner.assert_called()
        finally:
            Path(path).unlink()

    # covers: AC-2
    def test_check_markdown_only(self) -> None:
        """Test check with Markdown files only."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Test\n")
            path = f.name

        try:
            mock_runner = Mock()
            mock_runner.return_value = Mock(returncode=0, stdout='', stderr='')

            findings = check([], md_paths=[path], runner=mock_runner)
            # Should run markdownlint
            self.assertEqual(len(findings), 0)
        finally:
            Path(path).unlink()

    # covers: AC-2
    def test_check_both(self) -> None:
        """Test check with both Python and Markdown files."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            py_path = f.name
            f.write("# valid\n")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            md_path = f.name
            f.write("# Test\n")

        try:
            mock_runner = Mock()
            mock_runner.return_value = Mock(returncode=0, stdout='', stderr='')

            findings = check([py_path], md_paths=[md_path], runner=mock_runner)
            self.assertEqual(len(findings), 0)
        finally:
            Path(py_path).unlink()
            Path(md_path).unlink()


class TestVultureMalformedOutput(unittest.TestCase):
    """Test vulture with malformed output."""

    # covers: AC-2
    def test_check_vulture_malformed_output(self) -> None:
        """Test vulture with malformed output."""
        mock_runner = Mock()
        mock_runner.return_value = Mock(
            returncode=1,
            stdout='malformed line without colon\n',
            stderr=''
        )

        findings = check_vulture(['test.py'], runner=mock_runner)
        self.assertEqual(len(findings), 0)


class TestMarkdownlintMalformedOutput(unittest.TestCase):
    """Test markdownlint with malformed output."""

    # covers: AC-8
    def test_check_markdownlint_malformed_output(self) -> None:
        """Test markdownlint with malformed output."""
        mock_runner = Mock()
        mock_runner.return_value = Mock(
            returncode=1,
            stdout='malformed output\n',
            stderr=''
        )

        findings = check_markdownlint(['test.md'], runner=mock_runner)
        self.assertEqual(len(findings), 0)


class TestRuffEmptyOutput(unittest.TestCase):
    """Test ruff with empty output."""

    # covers: AC-2
    def test_check_ruff_empty_json_array(self) -> None:
        """Test ruff with empty JSON array."""
        mock_runner = Mock()
        mock_runner.return_value = Mock(returncode=0, stdout='[]', stderr='')

        findings = check_ruff(['test.py'], runner=mock_runner)
        self.assertEqual(len(findings), 0)


class TestMypyMultipleErrors(unittest.TestCase):
    """Test mypy with multiple errors."""

    # covers: AC-2
    def test_check_mypy_multiple_lines(self) -> None:
        """Test mypy with multiple error lines."""
        mock_runner = Mock()
        mock_runner.return_value = Mock(
            returncode=1,
            stdout='file1.py:10:5: error: error1\nfile2.py:20:3: error: error2\n',
            stderr=''
        )

        findings = check_mypy(['file1.py', 'file2.py'], runner=mock_runner)
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0]['file'], 'file1.py')
        self.assertEqual(findings[1]['file'], 'file2.py')


class TestCheckWithDefaultRunner(unittest.TestCase):
    """Test check function with default runner."""

    # covers: AC-2
    def test_check_with_none_runner(self) -> None:
        """Test check function uses default subprocess.run when runner is None."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("# valid\n")
            path = f.name

        try:
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout='', stderr='')
                # Call check without passing runner (defaults to None)
                findings = check([path], runner=None)
                # Should have called subprocess.run
                mock_run.assert_called()
        finally:
            Path(path).unlink()


class TestBannedTokensMultiple(unittest.TestCase):
    """Test banned tokens with multiple matches."""

    # covers: AC-2
    def test_check_banned_tokens_multiple_in_file(self) -> None:
        """Test banned tokens finds multiple matches."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("# TO" "DO: fix\nx = 1  # FIX" "ME: bug\n")
            path = f.name

        try:
            findings = check_banned_tokens([path])
            self.assertGreaterEqual(len(findings), 2)
            rules = [f['rule'] for f in findings]
            self.assertTrue(all(r == 'SG104' for r in rules))
        finally:
            Path(path).unlink()

    # covers: AC-2
    def test_check_banned_tokens_expectedfailure(self) -> None:
        """Test banned tokens finds banned-token."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("@expected" "Failure\ndef test(): pass\n")
            path = f.name

        try:
            findings = check_banned_tokens([path])
            self.assertEqual(len(findings), 1)
            self.assertIn('expected' 'Failure', findings[0]['message'])
        finally:
            Path(path).unlink()


if __name__ == '__main__':
    unittest.main()


class TestMarkerCommentsAreNotCommentedOutCode(unittest.TestCase):
    """AC marker comments are exempt from ERA001; real commented-out code is not."""

    def ruff(self, source: str) -> list:
        from pathlib import Path as P
        with tempfile.TemporaryDirectory() as tmp:
            path = P(tmp) / "m.py"
            path.write_text(source)
            return check_ruff([str(path)])

    # covers: AC-2
    def test_marker_only_file_has_no_sg101(self) -> None:
        src = "# implements: AC-1\ndef f():\n    return 1\n\n\n# covers: AC-12\ndef g():\n    return 2\n"
        self.assertEqual(self.ruff(src), [])

    # covers: AC-2
    def test_real_commented_out_code_still_flagged(self) -> None:
        findings = self.ruff("# x = foo(1)\ny = 1\n")
        self.assertEqual([(f["rule"], f["line"]) for f in findings], [("SG101", 1)])

    # covers: AC-2
    def test_marker_exemption_is_per_line(self) -> None:
        findings = self.ruff("# implements: AC-1\n# x = foo(1)\ny = 1\n")
        self.assertEqual([f["line"] for f in findings], [2])

    # covers: AC-2
    def test_unreadable_or_out_of_range_rows_are_not_markers(self) -> None:
        from specgate.l1_static import _is_marker_line
        self.assertFalse(_is_marker_line("/nonexistent/file.py", 1))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.py")
            with open(path, "w") as f:
                f.write("# covers: AC-1\n")
            self.assertTrue(_is_marker_line(path, 1))
            self.assertFalse(_is_marker_line(path, 0))
            self.assertFalse(_is_marker_line(path, 2))
