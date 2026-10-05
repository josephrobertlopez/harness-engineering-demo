"""Test that covers AC-2 and fails."""

import unittest
from src import multiply


class TestMultiply(unittest.TestCase):
    # covers: AC-2
    def test_multiply_positive_numbers(self):
        """Test multiplying two positive numbers - this test will fail."""
        result = multiply(2, 3)
        self.assertEqual(result, 7)  # Wrong expected value, should be 6
