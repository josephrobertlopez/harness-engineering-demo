import unittest
import os
from specgate.l2_trace import check


class TestGreen(unittest.TestCase):
    """Test green case: proper AC implementation and test should pass."""

    def test_proper_markers(self):
        """Verify no findings for proper AC markers and implementation."""
        fixture_dir = os.path.dirname(__file__)
        src_path = os.path.join(fixture_dir, 'src.py')
        test_path = os.path.join(fixture_dir, 'test.py')

        ac_ids = {'AC-1'}

        findings = check(ac_ids, [src_path], [test_path])

        # Should find no violations
        self.assertEqual(len(findings), 0, f"Expected no findings for green case, but got: {findings}")


if __name__ == '__main__':
    unittest.main()
