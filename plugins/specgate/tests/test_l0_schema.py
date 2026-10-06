import unittest
import unittest.mock
from pathlib import Path
from specgate.l0_schema import check_prd, check_openspec


class TestL0BadID(unittest.TestCase):
    """Test SG001: schema violation (invalid AC id format)"""

    # covers: AC-1
    def test_bad_id_fixture(self):
        fixture_path = Path(__file__).parent / "fixtures" / "l0" / "bad-id.md"
        findings = check_prd(str(fixture_path))

        # Should have at least one SG001 finding
        sg001_findings = [f for f in findings if f['rule'] == 'SG001']
        self.assertTrue(len(sg001_findings) > 0,
                       f"Expected SG001 findings for bad-id.md, got: {findings}")
        self.assertEqual(sg001_findings[0]['rule'], 'SG001')


class TestL0DupID(unittest.TestCase):
    """Test SG002: duplicate AC id"""

    # covers: AC-1
    def test_dup_id_fixture(self):
        fixture_path = Path(__file__).parent / "fixtures" / "l0" / "dup-id.md"
        findings = check_prd(str(fixture_path))

        # Should have at least one SG002 finding
        sg002_findings = [f for f in findings if f['rule'] == 'SG002']
        self.assertTrue(len(sg002_findings) > 0,
                       f"Expected SG002 findings for dup-id.md, got: {findings}")
        self.assertEqual(sg002_findings[0]['rule'], 'SG002')


class TestL0MissingThen(unittest.TestCase):
    """Test SG003: AC missing then field"""

    # covers: AC-1
    def test_missing_then_fixture(self):
        fixture_path = Path(__file__).parent / "fixtures" / "l0" / "missing-then.md"
        findings = check_prd(str(fixture_path))

        # Should have at least one SG003 finding
        sg003_findings = [f for f in findings if f['rule'] == 'SG003']
        self.assertTrue(len(sg003_findings) > 0,
                       f"Expected SG003 findings for missing-then.md, got: {findings}")
        self.assertEqual(sg003_findings[0]['rule'], 'SG003')
        # The AC is named by its 1-based position; L5 showed nothing pinned it.
        self.assertEqual([f['message'] for f in sg003_findings], ["AC 1 missing 'then' field"])


class TestL0NoTests(unittest.TestCase):
    """Test SG003: AC missing tests"""

    # covers: AC-1
    def test_no_tests_fixture(self):
        fixture_path = Path(__file__).parent / "fixtures" / "l0" / "no-tests.md"
        findings = check_prd(str(fixture_path))

        # Should have at least one SG003 finding
        sg003_findings = [f for f in findings if f['rule'] == 'SG003']
        self.assertTrue(len(sg003_findings) > 0,
                       f"Expected SG003 findings for no-tests.md, got: {findings}")
        self.assertEqual(sg003_findings[0]['rule'], 'SG003')
        self.assertEqual([f['message'] for f in sg003_findings], ["AC 1 missing or empty 'tests' field"])


class TestL0NoFrontmatter(unittest.TestCase):
    """Test SG005: PRD has no parseable YAML frontmatter"""

    def test_no_frontmatter_fixture(self):
        fixture_path = Path(__file__).parent / "fixtures" / "l0" / "no-frontmatter.md"
        findings = check_prd(str(fixture_path))

        # Should have at least one SG005 finding
        sg005_findings = [f for f in findings if f['rule'] == 'SG005']
        self.assertTrue(len(sg005_findings) > 0,
                       f"Expected SG005 findings for no-frontmatter.md, got: {findings}")
        self.assertEqual(sg005_findings[0]['rule'], 'SG005')


class TestL0Good(unittest.TestCase):
    """Test green fixture passes all rules"""

    # covers: AC-1
    def test_good_fixture(self):
        fixture_path = Path(__file__).parent / "fixtures" / "l0" / "good.md"
        findings = check_prd(str(fixture_path))

        # Should have no findings
        self.assertEqual(len(findings), 0,
                        f"Expected no findings for good.md, got: {findings}")


class TestL0OpenSpec(unittest.TestCase):
    """Test SG004: openspec validate failed"""

    def test_openspec_with_injected_runner(self):
        # Create a fake runner that simulates openspec failure
        def fake_runner(*args, **kwargs):
            result = unittest.mock.Mock()
            result.returncode = 1
            result.stderr = "openspec validation failed"
            return result

        # Mock subprocess.run
        findings = check_openspec("some-change.md", "/tmp", runner=fake_runner)

        # Should have at least one SG004 finding
        sg004_findings = [f for f in findings if f['rule'] == 'SG004']
        self.assertTrue(len(sg004_findings) > 0,
                       f"Expected SG004 findings for failed openspec, got: {findings}")
        self.assertEqual(sg004_findings[0]['rule'], 'SG004')


if __name__ == '__main__':
    unittest.main()
