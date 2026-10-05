"""Test that covers AC-3 and is skipped."""

import unittest
from src import divide


class TestDivide(unittest.TestCase):
    @unittest.skip("Test is skipped for now")
    # covers: AC-3
    def test_divide_positive_numbers(self):
        """Test dividing two positive numbers - skipped."""
        result = divide(6, 2)
        self.assertEqual(result, 3)
