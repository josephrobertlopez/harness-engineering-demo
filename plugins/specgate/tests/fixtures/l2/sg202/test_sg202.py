import unittest
import os
from specgate.l2_trace import check


class TestSG202(unittest.TestCase):
    """Test SG202: implementation carries marker but no test covers it."""

    def test_missing_covers_marker(self):
        """Verify SG202 finding when AC implementation lacks test coverage."""
        fixture_dir = os.path.dirname(__file__)
        src_path = os.path.join(fixture_dir, 'src.py')
        test_path = os.path.join(fixture_dir, 'test.py')

        ac_ids = {'AC-1'}

        findings = check(ac_ids, [src_path], [test_path])

        # Should find a SG202 violation
        sg202_findings = [f for f in findings if f['rule'] == 'SG202']
        self.assertGreater(len(sg202_findings), 0, f"Expected SG202 finding, got: {findings}")


if __name__ == '__main__':
    unittest.main()
