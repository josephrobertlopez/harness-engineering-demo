"""Offline end-to-end run. No network, no API key, real assertions.

This asserts that the loop *learns*, not merely that it does not throw: the
validation score has to climb from zero to one, at least one proposal has to
be genuinely rejected, and the held-out test split has to improve over the
no-skills baseline.
"""

import socket
import tempfile
import unittest
from pathlib import Path

from tests import context  # noqa: F401

from wikiskill.config import RunConfig
from wikiskill.loop import EvolutionLoop
from wikiskill.util import read_text_lf


class TestEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Any accidental network call should fail loudly rather than bill someone.
        cls._socket = socket.socket
        socket.socket = _deny  # type: ignore[assignment]

        cls.tmp = tempfile.TemporaryDirectory()
        cls.ws = Path(cls.tmp.name) / "workspace"
        cls.config = RunConfig(
            workspace=cls.ws,
            backend="mock",
            extra={"decoy_iteration": "3"},
        )
        cls.loop = EvolutionLoop(cls.config)
        cls.results = cls.loop.run(8)

    @classmethod
    def tearDownClass(cls):
        socket.socket = cls._socket  # type: ignore[assignment]
        cls.tmp.cleanup()

    def test_converges_and_early_stops(self):
        self.assertLessEqual(len(self.results), 8)
        self.assertEqual(self.results[-1].r_best_after, 1.0)

    def test_validation_is_monotone_non_decreasing(self):
        scores = [r.r_best_after for r in self.results]
        self.assertEqual(scores, sorted(scores))

    def test_at_least_one_genuine_rejection(self):
        rejected = [r for r in self.results if not r.accepted]
        self.assertTrue(rejected, "the decoy proposal should have been rejected")
        self.assertEqual(rejected[0].reject_reason, "no_improvement")

    def test_rejected_skill_never_reached_head(self):
        rejected = next(r for r in self.results if not r.accepted)
        head_names = self.loop.ws.skills.head_skillset().names()
        self.assertEqual(rejected.head_after, rejected.parent_sha)
        # The decoy body carried no rule; whatever landed under that name later
        # came from an accepted proposal.
        for name in head_names:
            skill = self.loop.ws.skills.head_skillset().get(name)
            self.assertIn("[[QUIRK:", skill.body)

    def test_wiki_grew_on_every_iteration_including_the_rejected_one(self):
        logs = read_text_lf(self.config.paths.logs)
        headings = [ln for ln in logs.splitlines() if ln.startswith("## Iteration")]
        self.assertEqual(len(headings), len(self.results))

    def test_skill_impact_has_one_record_per_proposal(self):
        impact = read_text_lf(self.config.paths.skill_impact)
        accepted = impact.count("-- Accepted")
        rejected = impact.count("-- Rejected")
        self.assertEqual(accepted + rejected, len(self.results))
        self.assertEqual(accepted, sum(1 for r in self.results if r.accepted))

    def test_head_moved_exactly_once_per_acceptance(self):
        commits = [
            e for e in self.loop.ws.journal.entries() if e["phase"] == "gate_decision"
        ]
        accepted = sum(1 for e in commits if e["data"].get("accepted"))
        self.assertEqual(accepted, sum(1 for r in self.results if r.accepted))

    def test_cited_evidence_resolves(self):
        for path, text in self.loop.ws.wiki.pages().items():
            self.assertTrue(text.strip(), f"{path} is empty")
        for r in self.results:
            if r.proposal is None:
                continue
            for pattern in r.proposal.evidence_patterns:
                self.assertIn(pattern, self.loop.ws.wiki.pages(), f"{pattern} does not resolve")

    def test_held_out_test_improves_over_no_skills(self):
        baseline, _ = self.loop.evaluate("test", "none")
        evolved, _ = self.loop.evaluate("test", "accepted")
        self.assertEqual(baseline, 0.0)
        self.assertGreater(evolved, baseline)

    def test_splits_are_disjoint(self):
        ids = {s: {t.task_id for t in self.loop.split(s)} for s in ("train", "val", "test")}
        self.assertFalse(ids["train"] & ids["val"])
        self.assertFalse(ids["train"] & ids["test"])
        self.assertFalse(ids["val"] & ids["test"])


def _deny(*_a, **_kw):
    raise RuntimeError("network access attempted during an offline test")


if __name__ == "__main__":
    unittest.main()
