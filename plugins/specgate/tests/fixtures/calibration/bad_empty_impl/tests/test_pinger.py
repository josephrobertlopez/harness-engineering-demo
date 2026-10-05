"""Tests for pinger."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pinger import ping


class PingerTests(unittest.TestCase):
    # covers: AC-1
    def test_ping(self) -> None:
        self.assertIsNone(ping("example"))


if __name__ == "__main__":
    unittest.main()
