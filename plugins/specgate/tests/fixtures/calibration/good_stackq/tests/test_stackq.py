"""Tests for stackq."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from stackq import Stack


class StackTests(unittest.TestCase):
    # covers: AC-1
    def test_peek(self) -> None:
        s = Stack()
        for item in (1, 2, 3):
            s.push(item)
        self.assertEqual(s.peek(), 3)
        self.assertEqual(s.peek(), 3)
        self.assertEqual(s.pop(), 3)
        self.assertEqual(s.peek(), 2)

    # covers: AC-2
    def test_pop_empty(self) -> None:
        s = Stack()
        with self.assertRaises(IndexError):
            s.pop()
        s.push(7)
        self.assertEqual(s.pop(), 7)
        with self.assertRaises(IndexError):
            s.pop()


if __name__ == "__main__":
    unittest.main()
