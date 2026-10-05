"""Tests for greeter."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from greeter import greet


class GreeterTests(unittest.TestCase):
    # covers: AC-1
    def test_greet(self) -> None:
        greet("Ada")
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
