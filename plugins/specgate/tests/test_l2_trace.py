"""L2 trace test loader and rule verification."""

import unittest
import os
from specgate.l2_trace import check


def load_tests(loader, tests, _pattern):
    """Load tests from the L2 fixtures directory.

    This function implements the load_tests protocol to allow unittest.discover()
    to find tests that are normally hidden in a fixtures/ subdirectory without
    an __init__.py in the parent tests/ directory.
    """
    suite = unittest.TestSuite()

    # Add the manually discovered L2 fixture tests
    fixtures_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'l2')
    suite.addTests(loader.discover(fixtures_path, pattern='test_sg*.py', top_level_dir=fixtures_path))

    # Add the rule verification tests from this module
    suite.addTests(loader.loadTestsFromTestCase(TestL2RuleDiscovery))

    return suite


class TestL2RuleDiscovery(unittest.TestCase):
    """Verify that each L2 rule (SG201-SG205) is produced by l2_trace.check()."""

    def setUp(self):
        """Set up paths for fixture directories."""
        self.fixtures_dir = os.path.join(
            os.path.dirname(__file__), 'fixtures', 'l2'
        )

    def _rules(self, fixture_name):
        """Rule ids that l2_trace.check reports for a fixture.

        Each fixture may have src.py and/or test.py. Include whichever files exist.
        """
        fixture_path = os.path.join(self.fixtures_dir, fixture_name)
        self.assertTrue(
            os.path.isdir(fixture_path),
            f"Fixture directory {fixture_name} not found at {fixture_path}"
        )

        src_path = os.path.join(fixture_path, 'src.py')
        test_path = os.path.join(fixture_path, 'test.py')

        # Collect which files exist in this fixture
        src_paths = [src_path] if os.path.isfile(src_path) else []
        test_paths = [test_path] if os.path.isfile(test_path) else []

        # At least one file type must exist
        self.assertTrue(
            src_paths or test_paths,
            f"Fixture {fixture_name} has neither src.py nor test.py"
        )

        # Use minimal AC id set to match what the fixture tests use
        # sg203 specifically needs AC-999 to NOT be in the set to trigger SG203
        ac_ids = {'AC-1'}

        return {f['rule'] for f in check(ac_ids, src_paths, test_paths)}

    # covers: AC-3
    def test_sg201_rule_produced(self):
        """Verify SG201 rule is produced by sg201 fixture."""
        self.assertIn('SG201', self._rules('sg201'))

    # covers: AC-3
    def test_sg202_rule_produced(self):
        """Verify SG202 rule is produced by sg202 fixture."""
        self.assertIn('SG202', self._rules('sg202'))

    # covers: AC-3
    def test_sg203_rule_produced(self):
        """Verify SG203 rule is produced by sg203 fixture."""
        self.assertIn('SG203', self._rules('sg203'))

    # covers: AC-3
    def test_sg204_rule_produced(self):
        """Verify SG204 rule is produced by sg204 fixture."""
        self.assertIn('SG204', self._rules('sg204'))

    # covers: AC-3
    def test_sg205_rule_produced(self):
        """Verify SG205 rule is produced by sg205 fixture."""
        self.assertIn('SG205', self._rules('sg205'))


if __name__ == '__main__':
    unittest.main()
