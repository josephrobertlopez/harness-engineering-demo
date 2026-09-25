"""Track 50's judge, and the claims the track's lessons make about it.

Lesson 4 quotes the judge's output for six deliberate breakages. Those
quotes are asserted here, so a change to the judge that makes a lesson lie
fails CI instead of confusing a learner.

The rubric tests guard the exercises themselves: a vague term the ticket
never uses teaches nothing, and a stakeholder fact already stated in the
ticket needs no interrogation to find. Every value must discriminate.
"""

import importlib.util
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from tests import context  # noqa: F401

REPO = Path(__file__).resolve().parents[1]
TRACK = REPO / "tutorials" / "50-spec-fidelity"
EXERCISES = sorted(d for d in (TRACK / "exercises").iterdir() if d.is_dir())


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"track50_{name}", TRACK / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    # Registered before exec: @dataclass looks its own module up by name.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


fidelity = _load("spec_fidelity")
starter = _load("start")


def findings(results) -> list[str]:
    return [str(f) for r in results for f in r.findings]


class Workspace(unittest.TestCase):
    """A fresh copy of exercise 1's solution, made the way lesson 4 says."""

    exercise = "01"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="track50-"))
        self.ws = self.tmp / "ws"
        starter.start(self.exercise, self.ws, with_solution=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def edit(self, rel: str, old: str, new: str) -> None:
        path = self.ws / rel
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text, f"lesson 4's edit no longer applies to {rel}")
        path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")

    def judge(self, run_tests: bool = False):
        return fidelity.judge(self.ws, run_tests=run_tests)


SPEC_01 = "openspec/changes/add-fx-convert/specs/fx/spec.md"


class TestLessonFourBreakages(Workspace):
    def test_copy_starts_green(self):
        self.assertTrue(all(r.ok for r in self.judge()))

    def test_a_dropped_trace_is_reported_both_ways(self):
        self.edit(SPEC_01, "Trace: PRD-7\n", "")
        got = findings(self.judge())
        self.assertTrue(any("'Health check' -- traces to no PRD requirement" in f for f in got), got)
        self.assertTrue(any("PRD-7 is not traced by any spec requirement" in f for f in got), got)

    def test_b_renamed_scenario_is_reported_both_ways(self):
        self.edit(SPEC_01, "#### Scenario: Tie rounds down to even", "#### Scenario: Tie rounds to even")
        got = findings(self.judge())
        self.assertIn("impl/tests -- no test names 'Scenario: Tie rounds to even' (requirement 'Half-to-even rounding')", got)
        self.assertTrue(any("names 'Scenario: Tie rounds down to even', which the spec does not contain" in f for f in got))

    def test_c_half_up_fails_only_through_the_tests(self):
        path = self.ws / "impl" / "app.py"
        path.write_text(path.read_text(encoding="utf-8").replace("ROUND_HALF_EVEN", "ROUND_HALF_UP"), encoding="utf-8")
        got = findings(self.judge(run_tests=True))
        self.assertEqual(len(got), 1, got)
        self.assertIn("'0.13' != '0.12'", got[0])

    def test_d_root_user_breaks_the_rubric_rule(self):
        self.edit("impl/Dockerfile", "USER fx\n", "USER root\n")
        self.assertEqual(
            findings(self.judge()),
            ["impl/Dockerfile -- container runs as non-root: expected /^USER (?!root\\b|0\\b)\\S+/"],
        )

    def test_e_vague_word_blocks_later_stages(self):
        self.edit("prd.md", "MUST NOT read the file", "MUST NOT read the file, so it is fast,")
        results = self.judge()
        self.assertEqual(findings(results), ["prd.md PRD-3 -- vague term 'fast' -- replace it with the number or behaviour it stands for"])
        self.assertEqual([bool(r.skipped) for r in results], [False, True, True])

    def test_f_gold_plating_is_invisible_to_the_deterministic_judge(self):
        """The lesson's point: this one needs the agent-backed constraint.

        If the judge ever learns to catch it, lesson 4 step f is wrong and
        must be rewritten -- this test is how you find out.
        """
        self.edit(
            "impl/app.py",
            '        if url.path == "/convert":',
            '        if url.path == "/currencies":\n'
            '            return 200, {"currencies": sorted(self.rates)}\n'
            '        if url.path == "/convert":',
        )
        self.assertTrue(all(r.ok for r in self.judge(run_tests=True)))


class TestJudgeRules(Workspace):
    def test_shall_only_in_header_gets_the_specific_hint(self):
        self.edit(SPEC_01, "### Requirement: Health check\n\nThe service SHALL answer", "### Requirement: Health check SHALL work\n\nThe service answers")
        self.assertTrue(any("only in the header" in f for f in findings(self.judge())))

    def test_requirement_outside_a_delta_section_is_reported(self):
        self.edit(SPEC_01, "## ADDED Requirements", "## Requirements\n\n### Requirement: Stray\nThe service SHALL x.\n\n## ADDED Requirements")
        self.assertTrue(any("'Stray' is outside a delta section" in f for f in findings(self.judge())))

    def test_scenario_without_then_is_reported(self):
        self.edit(SPEC_01, "- **THEN** the status is 200 and the body is `{\"status\": \"ok\"}`", "- **AND** nothing else")
        self.assertTrue(any("'Health check responds' needs WHEN and THEN" in f for f in findings(self.judge())))

    def test_vague_word_inside_code_is_not_flagged(self):
        """A checker that cries wolf gets ignored."""
        self.edit("prd.md", "The service SHALL answer `GET /healthz`", "The service SHALL answer `GET /healthz` (`fast` path)")
        self.assertTrue(all(r.ok for r in self.judge()))

    def test_unresolved_open_question_is_reported(self):
        self.edit("prd.md", "None open. Resolved during review:", "- Who owns rates.json? TBD")
        self.assertTrue(any("unresolved" in f for f in findings(self.judge())))

    def test_unticked_task_is_reported(self):
        self.edit("openspec/changes/add-fx-convert/tasks.md", "- [x] 3.1", "- [ ] 3.1")
        self.assertTrue(any("unticked: 3.1" in f for f in findings(self.judge())))

    def test_two_active_changes_are_ambiguous(self):
        (self.ws / "openspec" / "changes" / "second-change").mkdir()
        self.assertTrue(any("exactly one active change" in f for f in findings(self.judge())))

    def test_archive_is_not_an_active_change(self):
        (self.ws / "openspec" / "changes" / "archive").mkdir()
        self.assertTrue(all(r.ok for r in self.judge()))

    def test_report_uses_the_enforcer_shape(self):
        text = fidelity.report(self.judge())
        self.assertTrue(text.startswith("## Constraint Results"))
        self.assertIn("Summary: 3 passed, 0 failed, 0 unchecked", text)


class TestRubricsDiscriminate(unittest.TestCase):
    def test_three_exercises(self):
        self.assertEqual([d.name[:2] for d in EXERCISES], ["01", "02", "03"])

    def test_every_vague_term_is_in_the_ticket(self):
        for ex in EXERCISES:
            rubric = json.loads((ex / "rubric.json").read_text(encoding="utf-8"))
            ticket = (ex / "ticket.md").read_text(encoding="utf-8")
            for term in rubric["vague_terms"]:
                with self.subTest(exercise=ex.name, term=term):
                    self.assertRegex(ticket, re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE))

    def test_no_stakeholder_fact_is_already_in_the_ticket(self):
        """If the ticket already says it, asking for it teaches nothing."""
        for ex in EXERCISES:
            rubric = json.loads((ex / "rubric.json").read_text(encoding="utf-8"))
            ticket = (ex / "ticket.md").read_text(encoding="utf-8")
            for fact in rubric["prd_facts"]:
                with self.subTest(exercise=ex.name, fact=fact["label"]):
                    for pattern in fact["any_of"]:
                        self.assertIsNone(re.search(pattern, ticket, re.IGNORECASE))

    def test_every_fact_cites_an_answer_that_exists(self):
        for ex in EXERCISES:
            rubric = json.loads((ex / "rubric.json").read_text(encoding="utf-8"))
            answers = (ex / "stakeholder-answers.md").read_text(encoding="utf-8")
            for fact in rubric["prd_facts"]:
                for q in re.findall(r"Q\d+", fact["source"]):
                    with self.subTest(exercise=ex.name, source=q):
                        self.assertIn(f"**{q}.", answers)

    def test_every_fact_is_needed(self):
        """Removing the fact's sentence from the reference PRD must fail it.

        Checked by blanking every requirement line that matches the fact,
        then re-judging -- a fact that still passes was not really checked.
        """
        for ex in EXERCISES:
            rubric = json.loads((ex / "rubric.json").read_text(encoding="utf-8"))
            prd = (ex / "solution" / "prd.md").read_text(encoding="utf-8")
            for fact in rubric["prd_facts"]:
                with self.subTest(exercise=ex.name, fact=fact["label"]):
                    stripped = "\n".join(
                        "" if any(re.search(p, line, re.IGNORECASE) for p in fact["any_of"]) else line
                        for line in prd.splitlines()
                    )
                    tmp = Path(tempfile.mkdtemp(prefix="track50-fact-"))
                    try:
                        shutil.copyfile(ex / "rubric.json", tmp / "rubric.json")
                        (tmp / "prd.md").write_text(stripped, encoding="utf-8")
                        result = fidelity.judge_prd(tmp, rubric)
                        self.assertTrue(
                            any(fact["label"] in str(f) for f in result.findings),
                            f"removing it did not trip the fact check: {[str(f) for f in result.findings]}",
                        )
                    finally:
                        shutil.rmtree(tmp, ignore_errors=True)


class TestStart(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="track50-start-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_workspace_hides_the_answers(self):
        for ex in EXERCISES:
            with self.subTest(exercise=ex.name):
                ws = self.tmp / ex.name
                starter.start(ex.name[:2], ws)
                names = {p.name for p in ws.rglob("*")}
                self.assertNotIn("solution", names)
                self.assertNotIn("stakeholder-answers.md", names)
                self.assertTrue((self.tmp / f"{ex.name}.stakeholder-answers.md").is_file())
                self.assertTrue((ws / "openspec" / "config.yaml").is_file())
                self.assertNotIn("EXERCISE", (ws / "HARNESS.md").read_text(encoding="utf-8").split("-->", 1)[1])
                self.assertFalse(fidelity.judge(ws, run_tests=False)[0].ok)

    def test_with_solution_is_green(self):
        for ex in EXERCISES:
            with self.subTest(exercise=ex.name):
                ws = self.tmp / f"sol-{ex.name}"
                starter.start(ex.name[:2], ws, with_solution=True)
                self.assertTrue(all(r.ok for r in fidelity.judge(ws, run_tests=False)))

    def test_refuses_a_workspace_inside_the_repo(self):
        with self.assertRaises(SystemExit):
            starter.main(["01", str(TRACK / "exercises" / "01-docker-rest" / "scratch")])
        self.assertFalse((TRACK / "exercises" / "01-docker-rest" / "scratch").exists())

    def test_openspec_rules_are_quoted(self):
        """Unquoted, a rule containing ': ' is a YAML mapping and OpenSpec
        silently drops every rule for that artifact."""
        for line in (TRACK / "openspec-config.yaml").read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("- ") and ": " in line:
                with self.subTest(line=line):
                    self.assertRegex(line.strip(), r"^- '.*'$")


if __name__ == "__main__":
    unittest.main()
