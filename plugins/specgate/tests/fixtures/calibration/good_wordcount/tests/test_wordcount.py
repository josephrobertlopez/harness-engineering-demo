"""Tests for wordcount."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from wordcount import count_words, longest_word


class WordcountTests(unittest.TestCase):
    # covers: AC-1
    def test_count_words(self) -> None:
        self.assertEqual(count_words("one two  three"), 3)
        self.assertEqual(count_words("a\tb\nc"), 3)
        self.assertEqual(count_words(""), 0)

    # covers: AC-2
    def test_longest_word(self) -> None:
        self.assertEqual(longest_word("a bbb cc"), "bbb")
        self.assertEqual(longest_word(""), "")
        self.assertEqual(longest_word("   "), "")


if __name__ == "__main__":
    unittest.main()
