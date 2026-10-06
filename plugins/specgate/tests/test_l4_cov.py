"""L4 coverage test loader and rule verification."""

import os
import unittest

from specgate.l4_cov import check


def load_tests(loader, tests, _pattern):
    """Load tests from the L4 fixtures directory.

    This function implements the load_tests protocol to allow unittest.discover()
    to find tests that are normally hidden in a fixtures/ subdirectory without
    an __init__.py in the parent tests/ directory.
    """
    suite = unittest.TestSuite()

    # Add the rule verification tests from this module
    suite.addTests(loader.loadTestsFromTestCase(TestL4CoverageRules))

    return suite


class TestL4CoverageRules(unittest.TestCase):
    """Verify L4 rules (SG401) for dynamic context coverage."""

    def setUp(self) -> None:
        """Set up paths for fixture directories."""
        self.fixtures_dir = os.path.join(
            os.path.dirname(__file__), "fixtures", "l4"
        )

    # covers: AC-5
    def test_uncovered_lines_produce_sg401(self) -> None:
        """Verify SG401 rule is produced for uncovered AC lines."""
        fixture_path = os.path.join(self.fixtures_dir, "uncovered")
        self.assertTrue(
            os.path.isdir(fixture_path),
            f"Fixture directory 'uncovered' not found at {fixture_path}",
        )

        ac_ids = {"AC-1"}

        findings = check(ac_ids, [fixture_path], [fixture_path])

        # Verify SG401 is produced for uncovered lines
        sg401_findings = [f for f in findings if f["rule"] == "SG401"]
        self.assertGreater(
            len(sg401_findings),
            0,
            f"Expected rule SG401 in findings for uncovered branches, got: {findings}",
        )

        self.assertEqual([f["line"] for f in sg401_findings], [10])
        self.assertIn("AC-1", sg401_findings[0]["message"])

    def test_relative_paths_same_result(self) -> None:
        """Relative fixture paths give the same exact finding."""
        rel = os.path.relpath(os.path.join(self.fixtures_dir, "uncovered"))
        findings = check({"AC-1"}, [rel], [rel])
        self.assertEqual([f["line"] for f in findings], [10])

    # covers: AC-5
    def test_covered_lines_no_sg401(self) -> None:
        """Verify covered AC lines do not produce SG401."""
        fixture_path = os.path.join(self.fixtures_dir, "covered")
        self.assertTrue(
            os.path.isdir(fixture_path),
            f"Fixture directory 'covered' not found at {fixture_path}",
        )

        ac_ids = {"AC-1"}

        findings = check(ac_ids, [fixture_path], [fixture_path])

        # Verify no SG401 for fully covered AC
        sg401_findings = [f for f in findings if f["rule"] == "SG401"]
        self.assertEqual(
            len(sg401_findings),
            0,
            f"Fully covered AC should not produce SG401, but got: {sg401_findings}",
        )

    # covers: AC-5
    def test_stats_count_every_implementation_line_checked(self) -> None:
        """validate_positive has three executable lines (7, 8, 10) in both fixtures."""
        for fixture, sg401 in (("covered", []), ("uncovered", [10])):
            path = os.path.join(self.fixtures_dir, fixture)
            stats: dict[str, int] = {}
            findings = check({"AC-1"}, [path], [path], stats=stats)
            self.assertEqual(stats, {"lines": 3}, fixture)
            self.assertEqual([f["line"] for f in findings], sg401, fixture)

    def test_findings_deterministic(self) -> None:
        """Verify findings are sorted and deterministic."""
        fixture_path = os.path.join(self.fixtures_dir, "uncovered")

        ac_ids = {"AC-1"}

        findings1 = check(ac_ids, [fixture_path], [fixture_path])
        findings2 = check(ac_ids, [fixture_path], [fixture_path])

        # Convert to comparable form
        f1_str = [(f["rule"], f["file"], f["line"]) for f in findings1]
        f2_str = [(f["rule"], f["file"], f["line"]) for f in findings2]

        self.assertEqual(
            f1_str,
            f2_str,
            "Findings should be deterministically ordered across runs",
        )

    def test_findings_sorted_by_file_and_line(self) -> None:
        """Verify findings are sorted by file and line number."""
        fixture_path = os.path.join(self.fixtures_dir, "uncovered")

        ac_ids = {"AC-1"}

        findings = check(ac_ids, [fixture_path], [fixture_path])

        # Check sorting
        for i in range(len(findings) - 1):
            curr = (findings[i]["file"], findings[i]["line"])
            next_f = (findings[i + 1]["file"], findings[i + 1]["line"])
            self.assertLessEqual(
                curr,
                next_f,
                f"Findings not sorted: {curr} >= {next_f}",
            )


if __name__ == "__main__":
    unittest.main()
