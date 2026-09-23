import unittest

from tests import context  # noqa: F401

from wikiskill.gating import check_budget, decide


class TestGate(unittest.TestCase):
    def test_strict_improvement_accepts(self):
        d = decide(val_candidate=0.6, val_incumbent=0.4, r_best=0.4)
        self.assertTrue(d.accepted)
        self.assertEqual(d.r_best_after, 0.6)

    def test_tie_is_rejected(self):
        """Eq. 4 is a strict inequality. A tie buys nothing and risks drift."""
        d = decide(val_candidate=0.4, val_incumbent=0.4, r_best=0.4)
        self.assertFalse(d.accepted)
        self.assertEqual(d.reason, "no_improvement")
        self.assertEqual(d.r_best_after, 0.4)

    def test_regression_is_rejected_and_r_best_never_drops(self):
        d = decide(val_candidate=0.2, val_incumbent=0.4, r_best=0.8)
        self.assertFalse(d.accepted)
        self.assertEqual(d.r_best_after, 0.8)

    def test_margin_blocks_a_marginal_win(self):
        d = decide(val_candidate=0.45, val_incumbent=0.4, r_best=0.4, margin=0.1)
        self.assertFalse(d.accepted)
        self.assertEqual(d.reason, "below_margin")

    def test_compares_against_the_better_of_incumbent_and_r_best(self):
        """A lucky incumbent re-measurement must not let a weak candidate in."""
        d = decide(val_candidate=0.5, val_incumbent=0.2, r_best=0.8)
        self.assertFalse(d.accepted)


class TestBudget(unittest.TestCase):
    def test_oversized_skill_rejected(self):
        msg = check_budget(skill_bytes=9000, skillset_bytes=9000, skill_budget=8192, skillset_budget=32768)
        self.assertIn("skill is", msg or "")

    def test_oversized_set_rejected(self):
        msg = check_budget(skill_bytes=100, skillset_bytes=40000, skill_budget=8192, skillset_budget=32768)
        self.assertIn("skill set", msg or "")

    def test_within_budget(self):
        self.assertIsNone(
            check_budget(skill_bytes=100, skillset_bytes=200, skill_budget=8192, skillset_budget=32768)
        )


if __name__ == "__main__":
    unittest.main()


class TestBudgetFlagsAreReachable(unittest.TestCase):
    """The README documents these flags; documenting a flag that does not
    exist is worse than not having it, because the reader plans around it."""

    def test_budget_flags_reach_the_config(self):
        from wikiskill.cli import build_parser, config_from

        args = build_parser().parse_args(
            ["--skill-budget-bytes", "4096", "--skillset-budget-bytes", "16384", "status"]
        )
        cfg = config_from(args)
        self.assertEqual(cfg.skill_budget_bytes, 4096)
        self.assertEqual(cfg.skillset_budget_bytes, 16384)

    def test_defaults_match_the_config_dataclass(self):
        from wikiskill.config import RunConfig
        from wikiskill.cli import build_parser, config_from
        from pathlib import Path

        cfg = config_from(build_parser().parse_args(["status"]))
        default = RunConfig(workspace=Path("ws"))
        self.assertEqual(cfg.skill_budget_bytes, default.skill_budget_bytes)
        self.assertEqual(cfg.skillset_budget_bytes, default.skillset_budget_bytes)
