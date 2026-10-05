"""Strong test that pins behavior."""

import unittest
from src import compare_values


class TestStrongCompare(unittest.TestCase):
    # covers: AC-1
    def test_compare_less_than(self):
        """Test that compare_values returns True for a < b."""
        # Strong assertions that pin the behavior
        self.assertTrue(compare_values(1, 2))
        self.assertFalse(compare_values(2, 1))
        self.assertFalse(compare_values(1, 1))
        # These specific assertions will fail if the comparison operator is mutated
        self.assertTrue(compare_values(0, 100))
        self.assertFalse(compare_values(100, 0))
