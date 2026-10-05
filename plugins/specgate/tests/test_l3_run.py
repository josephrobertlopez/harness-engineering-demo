"""L3 run test loader and rule verification."""

import unittest
import os
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from specgate.l3_run import run_tests, write_junit, check
from specgate.l2_trace import get_marker_map


def load_tests(loader, tests, pattern):
    """Load tests from the L3 fixtures directory.

    This function implements the load_tests protocol to allow unittest.discover()
    to find tests that are normally hidden in a fixtures/ subdirectory without
    an __init__.py in the parent tests/ directory.
    """
    suite = unittest.TestSuite()

    # Add the rule verification tests from this module
    suite.addTests(loader.loadTestsFromTestCase(TestL3RuleDiscovery))

    return suite


class TestL3RuleDiscovery(unittest.TestCase):
    """Verify L3 rules (SG301, SG302) and JUnit generation."""

    def setUp(self):
        """Set up paths for fixture directories."""
        self.fixtures_dir = os.path.join(
            os.path.dirname(__file__), 'fixtures', 'l3'
        )

    def test_sg301_failing_test_produces_rule(self):
        """Verify SG301 rule is produced for failing AC test."""
        fixture_path = os.path.join(self.fixtures_dir, 'failing')
        self.assertTrue(
            os.path.isdir(fixture_path),
            f"Fixture directory 'failing' not found at {fixture_path}"
        )

        src_path = os.path.join(fixture_path, 'src.py')
        test_path = os.path.join(fixture_path, 'test.py')

        ac_ids = {'AC-1', 'AC-2', 'AC-3'}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            junit_path = f.name

        try:
            findings = check(ac_ids, [fixture_path], [fixture_path], junit_path)

            # Verify SG301 is produced
            sg301_findings = [f for f in findings if f['rule'] == 'SG301']
            self.assertGreater(
                len(sg301_findings), 0,
                f"Expected rule SG301 in findings, got: {findings}"
            )

            # Verify the message mentions AC-2 and FAIL status
            sg301_msg = sg301_findings[0]['message']
            self.assertIn('AC-2', sg301_msg)
            self.assertIn('FAIL', sg301_msg)
        finally:
            if os.path.exists(junit_path):
                os.unlink(junit_path)

    def test_sg301_skipped_test_produces_rule(self):
        """Verify SG301 rule is produced for skipped AC test."""
        fixture_path = os.path.join(self.fixtures_dir, 'skipped')
        self.assertTrue(
            os.path.isdir(fixture_path),
            f"Fixture directory 'skipped' not found at {fixture_path}"
        )

        ac_ids = {'AC-1', 'AC-2', 'AC-3'}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            junit_path = f.name

        try:
            findings = check(ac_ids, [fixture_path], [fixture_path], junit_path)

            # Verify SG301 is produced for skipped test
            sg301_findings = [f for f in findings if f['rule'] == 'SG301']
            self.assertGreater(
                len(sg301_findings), 0,
                f"Expected rule SG301 in findings for skipped test, got: {findings}"
            )

            # Verify the message mentions AC-3 and SKIP status
            sg301_msg = sg301_findings[0]['message']
            self.assertIn('AC-3', sg301_msg)
            self.assertIn('SKIP', sg301_msg)
        finally:
            if os.path.exists(junit_path):
                os.unlink(junit_path)

    def test_junit_parses_and_has_ac_properties(self):
        """Verify JUnit XML is valid and contains AC properties."""
        fixture_path = os.path.join(self.fixtures_dir, 'passing')
        self.assertTrue(
            os.path.isdir(fixture_path),
            f"Fixture directory 'passing' not found at {fixture_path}"
        )

        ac_ids = {'AC-1', 'AC-2', 'AC-3'}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            junit_path = f.name

        try:
            check(ac_ids, [fixture_path], [fixture_path], junit_path)

            # Verify JUnit file exists
            self.assertTrue(os.path.exists(junit_path), f"JUnit file not created at {junit_path}")

            # Parse JUnit XML
            tree = ET.parse(junit_path)
            root = tree.getroot()

            # Verify root is testsuites
            self.assertEqual(root.tag, 'testsuites')

            # Verify testsuite exists
            testsuites = root.findall('testsuite')
            self.assertGreater(len(testsuites), 0)

            testsuite = testsuites[0]

            # Verify testcases exist
            testcases = testsuite.findall('testcase')
            self.assertGreater(len(testcases), 0)

            # Verify properties exist and contain AC values
            found_ac_property = False
            for testcase in testcases:
                properties = testcase.find('properties')
                if properties is not None:
                    props = properties.findall('property')
                    for prop in props:
                        if prop.get('name') == 'ac':
                            found_ac_property = True
                            ac_value = prop.get('value')
                            self.assertIsNotNone(ac_value)
                            # AC value should match known AC ids
                            self.assertIn(ac_value, ac_ids)

            self.assertTrue(found_ac_property, "No AC properties found in JUnit XML")
        finally:
            if os.path.exists(junit_path):
                os.unlink(junit_path)

    def test_junit_deterministic_output(self):
        """Verify two runs produce byte-identical JUnit XML."""
        fixture_path = os.path.join(self.fixtures_dir, 'passing')
        self.assertTrue(
            os.path.isdir(fixture_path),
            f"Fixture directory 'passing' not found at {fixture_path}"
        )

        ac_ids = {'AC-1', 'AC-2', 'AC-3'}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            junit_path1 = f.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            junit_path2 = f.name

        try:
            # Run twice
            check(ac_ids, [fixture_path], [fixture_path], junit_path1)
            check(ac_ids, [fixture_path], [fixture_path], junit_path2)

            # Read both files
            with open(junit_path1, 'rb') as f:
                content1 = f.read()

            with open(junit_path2, 'rb') as f:
                content2 = f.read()

            # Verify byte-identical output
            self.assertEqual(content1, content2, "JUnit output is not deterministic across runs")
        finally:
            if os.path.exists(junit_path1):
                os.unlink(junit_path1)
            if os.path.exists(junit_path2):
                os.unlink(junit_path2)

    def test_passing_ac_no_sg301(self):
        """Verify passing AC test does not produce SG301."""
        fixture_path = os.path.join(self.fixtures_dir, 'passing')
        self.assertTrue(
            os.path.isdir(fixture_path),
            f"Fixture directory 'passing' not found at {fixture_path}"
        )

        ac_ids = {'AC-1', 'AC-2', 'AC-3'}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            junit_path = f.name

        try:
            findings = check(ac_ids, [fixture_path], [fixture_path], junit_path)

            # Verify no SG301 for passing test
            sg301_findings = [f for f in findings if f['rule'] == 'SG301']
            self.assertEqual(len(sg301_findings), 0, "Passing test should not produce SG301")
        finally:
            if os.path.exists(junit_path):
                os.unlink(junit_path)


if __name__ == '__main__':
    unittest.main()
