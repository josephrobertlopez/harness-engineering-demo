"""CLAUDE.md invariants that had no test of their own, and doc claims that drift.

Invariants 2 and 7, and the round_even scar's "assert it", were enforced only by the code being written carefully.
The harness health check that added HARNESS.md asked which invariants a
script could hold, and these two can: a public method is a fact, and so is
a path.

The doc-count test exists because that same check found README.md and
START-HERE.md both promising "119 tests" when the suite had 154. A number a
reader uses to decide whether their copy works has to be true.
"""

import re
import tempfile
import unittest
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from pathlib import Path

from tests import context  # noqa: F401

from wikiskill.bench import starter
from wikiskill.layers.raw import RawStore, trace_id
from wikiskill.layers.wiki import WikiStore

REPO = Path(__file__).resolve().parents[1]

#: The whole public surface of the wiki. Only the last three write. Adding a
#: method here is a deliberate act: if it deletes, prunes or rolls back
#: anything, it breaks invariant 2 -- the wiki is never rolled back, so
#: nothing may be able to reach it and undo.
WIKI_SURFACE = {
    "ensure", "pages", "read_relative", "index", "impact_log",
    "apply_patch_ops", "append_log", "append_skill_impact",
}


class TestWikiHasNoDeletePath(unittest.TestCase):
    """Invariant 2."""

    def test_public_surface_is_the_declared_one(self):
        public = {n for n in vars(WikiStore) if not n.startswith("_") and callable(getattr(WikiStore, n))}
        self.assertEqual(public, WIKI_SURFACE)

    def test_no_method_can_undo(self):
        undo = re.compile(r"delete|remove|prune|rollback|revert|clear|reset|truncate|unlink", re.I)
        self.assertEqual([n for n in vars(WikiStore) if undo.search(n)], [])


class TestTracePathsCarryTheSha(unittest.TestCase):
    """Invariant 7: incumbent and candidate must not overwrite each other."""

    def test_same_task_two_skill_sets_two_paths(self):
        store = RawStore(Path(tempfile.gettempdir()) / "unused")
        incumbent, candidate = "a" * 40, "b" * 40
        self.assertNotEqual(
            store.trace_path(3, "val", "T1", incumbent),
            store.trace_path(3, "val", "T1", candidate),
        )
        self.assertNotEqual(
            store.steps_path(3, "val", "T1", incumbent),
            store.steps_path(3, "val", "T1", candidate),
        )
        self.assertNotEqual(trace_id(3, "val", "T1", incumbent), trace_id(3, "val", "T1", candidate))


class TestBenchmarkValuesDiscriminate(unittest.TestCase):
    """CLAUDE.md scar: two round_even amounts once rounded the same either way.

    A value that rounds identically under half-even and half-up passes
    without the skill, so the baseline looks better than it is and the
    family's split carries no signal.
    """

    def test_every_round_even_amount_depends_on_the_rounding_mode(self):
        cent = Decimal("0.01")
        same = [a for a in starter._AMOUNTS
                if Decimal(a).quantize(cent, ROUND_HALF_EVEN) == Decimal(a).quantize(cent, ROUND_HALF_UP)]
        self.assertEqual(same, [])


class TestDocumentedTestCounts(unittest.TestCase):
    def test_counts_in_readmes_match_the_suite(self):
        suite = unittest.defaultTestLoader.discover(str(REPO / "tests"), top_level_dir=str(REPO))
        actual = suite.countTestCases()
        claims = []
        for name in ("README.md", "START-HERE.md"):
            text = (REPO / name).read_text(encoding="utf-8")
            claims += [(name, int(n)) for n in re.findall(r"\b(\d{2,4}) tests\b", text)]
        self.assertTrue(claims, "no test count found to check -- update this test if the docs stopped stating one")
        wrong = [(name, n) for name, n in claims if n != actual]
        self.assertEqual(wrong, [], f"the suite has {actual} tests")


if __name__ == "__main__":
    unittest.main()
