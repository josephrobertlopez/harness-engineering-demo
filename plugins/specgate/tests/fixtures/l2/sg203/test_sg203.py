import unittest
import os
from specgate.l2_trace import check


class TestSG203(unittest.TestCase):
    """Test SG203: marker references unknown AC id."""

    def test_unknown_ac_id(self):
        """Verify SG203 finding when marker references unknown AC id."""
        fixture_dir = os.path.dirname(__file__)
        src_path = os.path.join(fixture_dir, 'src.py')

        # Define only AC-1 as known; AC-999 is unknown
        ac_ids = {'AC-1'}

        findings = check(ac_ids, [src_path], [])

        # Should find a SG203 violation for AC-999
        sg203_findings = [f for f in findings if f['rule'] == 'SG203']
        self.assertGreater(len(sg203_findings), 0, f"Expected SG203 finding, got: {findings}")
        self.assertTrue(any('AC-999' in f['message'] for f in sg203_findings),
                       f"SG203 finding should mention AC-999, got: {sg203_findings}")


if __name__ == '__main__':
    unittest.main()
