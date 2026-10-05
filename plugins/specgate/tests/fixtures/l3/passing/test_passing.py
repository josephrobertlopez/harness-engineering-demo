"""Test that covers AC-1 and passes."""

import unittest
from src import add


class TestAdd(unittest.TestCase):
    # covers: AC-1
    def test_add_positive_numbers(self):
        """Test adding two positive numbers."""
        result = add(2, 3)
        self.assertEqual(result, 5)
