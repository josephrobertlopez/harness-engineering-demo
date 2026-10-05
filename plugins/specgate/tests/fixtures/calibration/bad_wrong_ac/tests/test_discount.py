"""Tests for discount."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from discount import validate_price


class DiscountTests(unittest.TestCase):
    # covers: AC-1
    def test_negative_price(self) -> None:
        with self.assertRaises(ValueError):
            validate_price(-1)
        self.assertEqual(validate_price(3), 3)


if __name__ == "__main__":
    unittest.main()
