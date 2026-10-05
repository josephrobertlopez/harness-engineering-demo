"""Tests for slugger."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from slugger import slugify, strip_punctuation


class SluggerTests(unittest.TestCase):
    # covers: AC-1
    def test_slugify(self) -> None:
        self.assertEqual(slugify("Hello World"), "hello-world")
        self.assertEqual(slugify("  A   b  "), "a-b")
        self.assertEqual(slugify(""), "")

    # covers: AC-2
    def test_strip_punctuation(self) -> None:
        self.assertEqual(strip_punctuation("a,b!"), "ab")
        self.assertEqual(strip_punctuation("x y."), "x y")
        self.assertEqual(strip_punctuation("r2d2"), "r2d2")
        self.assertEqual(strip_punctuation(""), "")


if __name__ == "__main__":
    unittest.main()
