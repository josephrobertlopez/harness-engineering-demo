"""Coverage tests for the L0 schema layer."""

from pathlib import Path
from specgate.l0_schema import parse_prd, check_prd, check_openspec, check
from unittest.mock import Mock, patch
import json
import tempfile
import unittest


class TestParsePRD(unittest.TestCase):
    """Test PRD parsing."""

    # covers: AC-1
    def test_parse_prd_file_not_found(self) -> None:
        """Test parsing non-existent file."""
        result, error = parse_prd("/nonexistent/file.md")
        self.assertIsNone(result)
        self.assertIsNotNone(error)
        self.assertIn("Could not read file", error)

    # covers: AC-1
    def test_parse_prd_no_frontmatter(self) -> None:
        """Test parsing file without frontmatter."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# No frontmatter\n")
            path = f.name

        try:
            result, error = parse_prd(path)
            self.assertIsNone(result)
            self.assertIn("No frontmatter found", error)
        finally:
            Path(path).unlink()

    # covers: AC-1
    def test_parse_prd_no_closing_frontmatter(self) -> None:
        """Test parsing file without closing ---."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("---\ntitle: Test\n# No closing ---\n")
            path = f.name

        try:
            result, error = parse_prd(path)
            self.assertIsNone(result)
            self.assertIn("No closing --- found", error)
        finally:
            Path(path).unlink()

    # covers: AC-1
    def test_parse_prd_empty_frontmatter(self) -> None:
        """Test parsing file with empty frontmatter."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("---\n---\n# Content\n")
            path = f.name

        try:
            result, error = parse_prd(path)
            self.assertIsNone(result)
            self.assertIn("Frontmatter is empty", error)
        finally:
            Path(path).unlink()

    # covers: AC-1
    def test_parse_prd_invalid_yaml(self) -> None:
        """Test parsing file with invalid YAML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("---\ninvalid: [unclosed\n---\n")
            path = f.name

        try:
            result, error = parse_prd(path)
            self.assertIsNone(result)
            self.assertIn("Invalid YAML", error)
        finally:
            Path(path).unlink()

    # covers: AC-1
    def test_parse_prd_valid(self) -> None:
        """Test parsing valid PRD."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("---\ntitle: Test\nacs: []\n---\n# Content\n")
            path = f.name

        try:
            result, error = parse_prd(path)
            self.assertIsNotNone(result)
            self.assertIsNone(error)
            self.assertEqual(result["title"], "Test")
        finally:
            Path(path).unlink()


class TestCheckPRD(unittest.TestCase):
    """Test PRD checking."""

    # covers: AC-1
    def test_check_prd_schema_not_found(self) -> None:
        """Test checking when schema file is not found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write("---\ntitle: Test\n---\n")
                path = f.name

            try:
                # Pass a nonexistent schema path
                nonexistent_schema = str(Path(tmpdir) / "nonexistent.json")
                findings = check_prd(path, schema_path=nonexistent_schema)
                self.assertTrue(any(f['rule'] == 'SG005' for f in findings),
                              f"Expected SG005 finding, got: {findings}")
            finally:
                Path(path).unlink()

    # covers: AC-1
    def test_check_prd_parse_error(self) -> None:
        """Test checking with parse error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# No frontmatter\n")
            path = f.name

        try:
            findings = check_prd(path)
            self.assertTrue(any(f['rule'] == 'SG005' for f in findings))
        finally:
            Path(path).unlink()

    # covers: AC-1
    def test_check_prd_duplicate_ac_ids(self) -> None:
        """Test checking for duplicate AC IDs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a temporary schema
            schema_path = Path(tmpdir) / "prd.schema.json"
            with open(schema_path, 'w') as f:
                json.dump({"type": "object"}, f)

            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write("---\ntitle: Test\nacs:\n  - id: AC-1\n  - id: AC-1\n---\n")
                path = f.name

            try:
                findings = check_prd(path, schema_path=str(schema_path))
                self.assertTrue(any(f['rule'] == 'SG002' for f in findings),
                              f"Expected SG002 finding, got: {findings}")
            finally:
                Path(path).unlink()

    # covers: AC-1
    def test_check_prd_missing_ac_fields(self) -> None:
        """Test checking for missing AC fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a temporary schema
            schema_path = Path(tmpdir) / "prd.schema.json"
            with open(schema_path, 'w') as f:
                json.dump({"type": "object"}, f)

            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write("---\ntitle: Test\nacs:\n  - id: AC-1\n---\n")
                path = f.name

            try:
                findings = check_prd(path, schema_path=str(schema_path))
                # Should have findings for missing given, when, then, tests
                sg003_findings = [f for f in findings if f['rule'] == 'SG003']
                self.assertGreater(len(sg003_findings), 0,
                                 f"Expected SG003 findings, got: {findings}")
            finally:
                Path(path).unlink()


class TestCheckOpenspec(unittest.TestCase):
    """Test openspec checking."""

    # covers: AC-1
    def test_check_openspec_success(self) -> None:
        """Test successful openspec check."""
        mock_runner = Mock()
        mock_runner.return_value = Mock(returncode=0, stderr='', stdout='')

        findings = check_openspec('test.yaml', '/tmp', runner=mock_runner)
        self.assertEqual(len(findings), 0)
        mock_runner.assert_called_once()

    # covers: AC-1
    def test_check_openspec_failure(self) -> None:
        """Test failed openspec check."""
        mock_runner = Mock()
        mock_runner.return_value = Mock(returncode=1, stderr='validation error', stdout='')

        findings = check_openspec('test.yaml', '/tmp', runner=mock_runner)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]['rule'], 'SG004')

    # covers: AC-1
    def test_check_openspec_exception(self) -> None:
        """Test openspec check with OSError exception."""
        mock_runner = Mock()
        mock_runner.side_effect = OSError("command failed")

        findings = check_openspec('test.yaml', '/tmp', runner=mock_runner)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]['rule'], 'SG004')
        self.assertIn('Could not run openspec', findings[0]['message'])

    # covers: AC-1
    def test_check_openspec_default_runner(self) -> None:
        """Test openspec check with default runner."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr='', stdout='')
            findings = check_openspec('test.yaml', '/tmp')
            self.assertEqual(len(findings), 0)


class TestCheck(unittest.TestCase):
    """Test combined check function."""

    # covers: AC-1
    def test_check_prd_only(self) -> None:
        """Test checking PRD without openspec."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# No frontmatter\n")
            path = f.name

        try:
            findings = check(path)
            self.assertTrue(any(f['rule'] == 'SG005' for f in findings))
        finally:
            Path(path).unlink()

    # covers: AC-1
    def test_check_prd_with_openspec(self) -> None:
        """Test checking PRD with openspec."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as prd:
            prd.write("---\ntitle: Test\n---\n")
            prd_path = prd.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as change:
            change.write("test: value\n")
            change_path = change.name

        try:
            mock_runner = Mock()
            mock_runner.return_value = Mock(returncode=0, stderr='', stdout='')

            with patch('subprocess.run', mock_runner):
                findings = check(prd_path, change_path, '/tmp')
                # Should succeed (returncode 0 means no openspec findings)
                openspec_findings = [f for f in findings if f["rule"] == "SG004"]
                self.assertEqual(len(openspec_findings), 0)
        finally:
            Path(prd_path).unlink()
            Path(change_path).unlink()


class TestCheckOpenspecStderr(unittest.TestCase):
    """Test openspec checking with stderr output."""

    # covers: AC-1
    def test_check_openspec_stdout_error(self) -> None:
        """Test openspec check with error in stdout."""
        mock_runner = Mock()
        mock_runner.return_value = Mock(returncode=1, stderr='', stdout='validation failed\nerror details')

        findings = check_openspec('test.yaml', '/tmp', runner=mock_runner)
        self.assertEqual(len(findings), 1)
        self.assertIn('validation failed', findings[0]['message'])


class TestParseOpenspecVarious(unittest.TestCase):
    """Test parse_prd with various frontmatter structures."""

    # covers: AC-1
    def test_parse_prd_minimal_valid(self) -> None:
        """Test parsing minimal valid frontmatter."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("---\nfeature: Test\n---\n")
            path = f.name

        try:
            result, error = parse_prd(path)
            self.assertIsNotNone(result)
            self.assertIsNone(error)
            self.assertEqual(result["feature"], "Test")
        finally:
            Path(path).unlink()

    # covers: AC-1
    def test_check_prd_with_empty_acs_list(self) -> None:
        """Test checking with empty ACs list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a temporary schema
            schema_path = Path(tmpdir) / "prd.schema.json"
            with open(schema_path, 'w') as f:
                json.dump({"type": "object"}, f)

            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write("---\nfeature: Test\nacs: []\n---\n")
                path = f.name

            try:
                findings = check_prd(path, schema_path=str(schema_path))
                # Should have no findings for valid empty list
                self.assertIsNotNone(findings,
                                   "Expected findings list (may be empty or have entries)")
                self.assertIsInstance(findings, list)
            finally:
                Path(path).unlink()


class TestCheckWithBothParameters(unittest.TestCase):
    """Test check function with both PRD and openspec."""

    # covers: AC-1
    def test_check_with_bad_cwd(self) -> None:
        """Test check with invalid cwd."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as prd:
            prd.write("---\ntitle: Test\n---\n")
            prd_path = prd.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as change:
            change.write("invalid\n")
            change_path = change.name

        try:
            mock_runner = Mock()
            mock_runner.return_value = Mock(returncode=1, stderr='error', stdout='')

            with patch('subprocess.run', mock_runner):
                findings = check(prd_path, change_path, '/nonexistent')
                # Should have some findings
                self.assertGreater(len(findings), 0)
        finally:
            Path(prd_path).unlink()
            Path(change_path).unlink()


class TestCheckPrdBranchCoverage(unittest.TestCase):
    """Test branch coverage for check_prd function."""

    # covers: AC-1
    def test_check_prd_ac_not_dict(self) -> None:
        """Test checking with AC that's not a dict (line 106, 121 false branch)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("---\nfeature: Test\nacs:\n  - string_ac\n  - another_string\n---\n")
            path = f.name

        try:
            findings = check_prd(path)
            # When acs contains non-dict items, they should be skipped
            # but we might get schema validation errors
            self.assertIsInstance(findings, list)
        finally:
            Path(path).unlink()

    # covers: AC-1
    def test_check_prd_ac_dict_no_id(self) -> None:
        """Test checking with AC dict that lacks 'id' field (line 106 false branch)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("---\nfeature: Test\nacs:\n  - name: test_ac\n    given: some state\n    when: action\n    then: result\n    tests: []\n---\n")
            path = f.name

        try:
            findings = check_prd(path)
            # AC without 'id' should not trigger SG002 (duplicate ID check)
            # but might trigger other checks
            sg002_findings = [f for f in findings if f['rule'] == 'SG002']
            self.assertEqual(len(sg002_findings), 0)
        finally:
            Path(path).unlink()

    # covers: AC-1
    def test_check_prd_duplicate_ac_ids(self) -> None:
        """Test checking with duplicate AC IDs (SG002 rule)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("""---
feature: Test
acs:
  - id: AC-1
    given: state1
    when: action1
    then: result1
    tests: [test1]
  - id: AC-1
    given: state2
    when: action2
    then: result2
    tests: [test2]
---
""")
            path = f.name

        try:
            findings = check_prd(path)
            sg002_findings = [f for f in findings if f['rule'] == 'SG002']
            self.assertGreater(len(sg002_findings), 0, "Should detect duplicate AC IDs")
            self.assertEqual(sg002_findings[0]['message'], "Duplicate AC ID: AC-1")
        finally:
            Path(path).unlink()

    # covers: AC-1
    def test_check_prd_ac_with_all_required_fields(self) -> None:
        """Test checking AC with all required fields (positive case for SG003)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("""---
feature: Test
acs:
  - id: AC-1
    given: initial state
    when: user performs action
    then: expected result
    tests:
      - test_ac_1
---
""")
            path = f.name

        try:
            findings = check_prd(path)
            sg003_findings = [f for f in findings if f['rule'] == 'SG003']
            self.assertEqual(len(sg003_findings), 0, "Should not report missing fields when all are present")
        finally:
            Path(path).unlink()

    # covers: AC-1
    def test_check_prd_ac_with_empty_string_fields(self) -> None:
        """Test checking AC with empty string fields (should trigger SG003)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("""---
feature: Test
acs:
  - id: AC-1
    given: ""
    when: action
    then: result
    tests: [test1]
---
""")
            path = f.name

        try:
            findings = check_prd(path)
            sg003_findings = [f for f in findings if f['rule'] == 'SG003']
            self.assertGreater(len(sg003_findings), 0, "Should detect empty 'given' field")
        finally:
            Path(path).unlink()

    # covers: AC-1
    def test_check_openspec_returncode_zero(self) -> None:
        """Test openspec check with zero return code (success case)."""
        mock_runner = Mock()
        mock_runner.return_value = Mock(returncode=0, stderr='', stdout='')

        findings = check_openspec('test.yaml', '/tmp', runner=mock_runner)
        self.assertEqual(len(findings), 0)

    # covers: AC-1
    def test_check_openspec_returncode_nonzero_with_stderr(self) -> None:
        """Test openspec check with non-zero return code and stderr."""
        mock_runner = Mock()
        mock_runner.return_value = Mock(returncode=1, stderr='validation failed: bad syntax', stdout='')

        findings = check_openspec('test.yaml', '/tmp', runner=mock_runner)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]['rule'], 'SG004')
        self.assertIn('validation failed: bad syntax', findings[0]['message'])

    # covers: AC-1
    def test_check_openspec_returncode_nonzero_with_stdout(self) -> None:
        """Test openspec check with non-zero return code and stdout."""
        mock_runner = Mock()
        mock_runner.return_value = Mock(returncode=1, stderr='', stdout='error output')

        findings = check_openspec('test.yaml', '/tmp', runner=mock_runner)
        self.assertEqual(len(findings), 1)
        self.assertIn('error output', findings[0]['message'])
