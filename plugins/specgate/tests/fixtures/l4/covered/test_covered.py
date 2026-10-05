"""Test that covers AC-1 with full branch coverage."""

import unittest
from src import validate_positive


class TestValidate(unittest.TestCase):
    # covers: AC-1
    def test_positive_number(self) -> None:
        """Test with a positive number (covers the if branch)."""
        result = validate_positive(5)
        self.assertTrue(result)

    # covers: AC-1
    def test_non_positive_number(self) -> None:
        """Test with a non-positive number (covers the else branch)."""
        result = validate_positive(-5)
        self.assertFalse(result)
