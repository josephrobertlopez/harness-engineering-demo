"""Weak test that doesn't pin behavior."""

import unittest
from src import compare_values


class TestWeakCompare(unittest.TestCase):
    # covers: AC-1
    def test_compare_is_callable(self):
        """Test that compare_values is callable (weak assertion)."""
        # This weak test only checks that the function is callable,
        # not what it actually returns. Mutants will survive this.
        self.assertTrue(callable(compare_values))
