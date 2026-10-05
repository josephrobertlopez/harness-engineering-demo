"""Tests for clamper."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from clamper import clamp_high, clamp_low


class ClamperTests(unittest.TestCase):
    # covers: AC-1
    def test_clamp_low(self) -> None:
        self.assertEqual(clamp_low(1, 5), 5)
        self.assertEqual(clamp_low(9, 5), 9)
        self.assertEqual(clamp_low(5, 5), 5)

    # covers: AC-2
    def test_clamp_high(self) -> None:
        self.assertEqual(clamp_high(9, 5), 5)
        self.assertEqual(clamp_high(1, 5), 1)
        self.assertEqual(clamp_high(5, 5), 5)


if __name__ == "__main__":
    unittest.main()
