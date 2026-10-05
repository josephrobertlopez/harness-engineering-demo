"""Tests for shouter."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from shouter import shout


class ShouterTests(unittest.TestCase):
    # covers: AC-1
    def test_shout(self) -> None:
        self.assertIsInstance(shout("hi"), str)
        self.assertIn("hi", shout("hi").lower())


if __name__ == "__main__":
    unittest.main()
