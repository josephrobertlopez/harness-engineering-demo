import unittest
import os
from specgate.l2_trace import check


class TestSG205(unittest.TestCase):
    """Test SG205: function with implements marker but empty body."""

    def test_empty_body(self):
        """Verify SG205 finding when implements function has empty body."""
        fixture_dir = os.path.dirname(__file__)
        src_path = os.path.join(fixture_dir, 'src.py')

        ac_ids = {'AC-1'}

        findings = check(ac_ids, [src_path], [])

        # Should find a SG205 violation
        sg205_findings = [f for f in findings if f['rule'] == 'SG205']
        self.assertGreater(len(sg205_findings), 0, f"Expected SG205 finding, got: {findings}")


if __name__ == '__main__':
    unittest.main()
