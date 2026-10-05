"""Tests for pricing."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pricing import total


class PricingTests(unittest.TestCase):
    # covers: AC-1
    def test_total(self) -> None:
        self.assertEqual(total([1.5, 2.5]), 4.0)
        self.assertEqual(total([]), 0)
        self.assertEqual(total([5]), 5)


if __name__ == "__main__":
    unittest.main()
