import unittest
import os
from specgate.l2_trace import check


class TestSG204(unittest.TestCase):
    """Test SG204: test function with covers marker but no asserts."""

    def test_no_asserts(self):
        """Verify SG204 finding when covers test has no asserts."""
        fixture_dir = os.path.dirname(__file__)
        test_path = os.path.join(fixture_dir, 'test.py')

        ac_ids = {'AC-1'}

        findings = check(ac_ids, [], [test_path])

        # Should find a SG204 violation
        sg204_findings = [f for f in findings if f['rule'] == 'SG204']
        self.assertGreater(len(sg204_findings), 0, f"Expected SG204 finding, got: {findings}")


if __name__ == '__main__':
    unittest.main()
