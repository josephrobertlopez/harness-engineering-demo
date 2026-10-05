import unittest
import os
from specgate.l2_trace import check


class TestSG201(unittest.TestCase):
    """Test SG201: test covers AC-k but implementation lacks implements marker."""

    def test_missing_implements_marker(self):
        """Verify SG201 finding when AC function lacks implements marker."""
        fixture_dir = os.path.dirname(__file__)
        src_path = os.path.join(fixture_dir, 'src.py')
        test_path = os.path.join(fixture_dir, 'test.py')

        # Define AC ids we know about
        ac_ids = {'AC-1'}

        findings = check(ac_ids, [src_path], [test_path])

        # Should find a SG201 violation
        sg201_findings = [f for f in findings if f['rule'] == 'SG201']
        self.assertGreater(len(sg201_findings), 0, f"Expected SG201 finding, got: {findings}")


if __name__ == '__main__':
    unittest.main()
