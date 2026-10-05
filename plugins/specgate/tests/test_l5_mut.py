"""L5 mutation test layer verification."""

import json
import os
import unittest

from specgate.l5_mut import check


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, _pattern: str | None) -> unittest.TestSuite:
    """Load tests from the L5 fixtures directory.

    This function implements the load_tests protocol to allow unittest.discover()
    to find tests that are normally hidden in a fixtures/ subdirectory without
    an __init__.py in the parent tests/ directory.
    """
    suite = unittest.TestSuite()

    # Add the rule verification tests from this module
    suite.addTests(loader.loadTestsFromTestCase(TestL5MutantGeneration))

    return suite


class TestL5MutantGeneration(unittest.TestCase):
    """Verify L5 rules (SG501) and mutation survival detection."""

    def setUp(self) -> None:
        """Set up paths for fixture directories."""
        self.fixtures_dir = os.path.join(
            os.path.dirname(__file__), 'fixtures', 'l5'
        )

    # covers: AC-6
    def test_weak_fixture_produces_sg501(self) -> None:
        """Verify SG501 rule is produced for weak test with surviving mutants."""
        fixture_path = os.path.join(self.fixtures_dir, 'weak')
        self.assertTrue(
            os.path.isdir(fixture_path),
            f"Fixture directory 'weak' not found at {fixture_path}"
        )

        ac_ids = {'AC-1'}

        findings = check(ac_ids, [fixture_path], [fixture_path])

        # Verify SG501 is produced (weak test should allow mutants to survive)
        sg501_findings = [f for f in findings if f['rule'] == 'SG501']
        self.assertGreater(
            len(sg501_findings), 0,
            f"Expected rule SG501 in findings (weak test allows survival), got: {findings}"
        )

    # covers: AC-6
    def test_strong_fixture_produces_no_sg501(self) -> None:
        """Verify SG501 rule is not produced for strong test (all mutants killed)."""
        fixture_path = os.path.join(self.fixtures_dir, 'strong')
        self.assertTrue(
            os.path.isdir(fixture_path),
            f"Fixture directory 'strong' not found at {fixture_path}"
        )

        ac_ids = {'AC-1'}

        findings = check(ac_ids, [fixture_path], [fixture_path])

        # Verify no SG501 (strong test should kill all mutants)
        sg501_findings = [f for f in findings if f['rule'] == 'SG501']
        self.assertEqual(
            len(sg501_findings), 0,
            f"Expected no SG501 findings (strong test kills mutants), got: {findings}"
        )

    # covers: AC-6
    def test_results_deterministic_weak(self) -> None:
        """Verify two runs produce identical results on weak fixture."""
        fixture_path = os.path.join(self.fixtures_dir, 'weak')
        self.assertTrue(
            os.path.isdir(fixture_path),
            f"Fixture directory 'weak' not found at {fixture_path}"
        )

        ac_ids = {'AC-1'}

        # Run twice
        findings1 = check(ac_ids, [fixture_path], [fixture_path])
        findings2 = check(ac_ids, [fixture_path], [fixture_path])

        # Convert to JSON for byte-identical comparison
        json1 = json.dumps(findings1, sort_keys=True)
        json2 = json.dumps(findings2, sort_keys=True)

        # Verify byte-identical output
        self.assertEqual(
            json1, json2,
            f"Results are not deterministic across runs.\nRun 1:\n{json1}\n\nRun 2:\n{json2}"
        )

    def test_results_deterministic_strong(self) -> None:
        """Verify two runs produce identical results on strong fixture."""
        fixture_path = os.path.join(self.fixtures_dir, 'strong')
        self.assertTrue(
            os.path.isdir(fixture_path),
            f"Fixture directory 'strong' not found at {fixture_path}"
        )

        ac_ids = {'AC-1'}

        # Run twice
        findings1 = check(ac_ids, [fixture_path], [fixture_path])
        findings2 = check(ac_ids, [fixture_path], [fixture_path])

        # Convert to JSON for byte-identical comparison
        json1 = json.dumps(findings1, sort_keys=True)
        json2 = json.dumps(findings2, sort_keys=True)

        # Verify byte-identical output
        self.assertEqual(
            json1, json2,
            f"Results are not deterministic across runs.\nRun 1:\n{json1}\n\nRun 2:\n{json2}"
        )

    def test_weak_sg501_has_valid_fields(self) -> None:
        """Verify SG501 findings have all required fields."""
        fixture_path = os.path.join(self.fixtures_dir, 'weak')
        self.assertTrue(
            os.path.isdir(fixture_path),
            f"Fixture directory 'weak' not found at {fixture_path}"
        )

        ac_ids = {'AC-1'}

        findings = check(ac_ids, [fixture_path], [fixture_path])

        # Get SG501 findings
        sg501_findings = [f for f in findings if f['rule'] == 'SG501']
        self.assertGreater(len(sg501_findings), 0)

        # Verify each finding has required fields
        for finding in sg501_findings:
            self.assertIn('rule', finding)
            self.assertIn('file', finding)
            self.assertIn('line', finding)
            self.assertIn('message', finding)

            self.assertEqual(finding['rule'], 'SG501')
            self.assertIsInstance(finding['file'], str)
            self.assertIsInstance(finding['line'], int)
            self.assertIsInstance(finding['message'], str)

    def test_strong_returns_empty_list(self) -> None:
        """Verify strong fixture returns empty findings list."""
        fixture_path = os.path.join(self.fixtures_dir, 'strong')
        self.assertTrue(
            os.path.isdir(fixture_path),
            f"Fixture directory 'strong' not found at {fixture_path}"
        )

        ac_ids = {'AC-1'}

        findings = check(ac_ids, [fixture_path], [fixture_path])

        # Verify findings is an empty list
        self.assertIsInstance(findings, list)
        self.assertEqual(len(findings), 0, f"Expected empty findings, got: {findings}")


if __name__ == '__main__':
    unittest.main()
