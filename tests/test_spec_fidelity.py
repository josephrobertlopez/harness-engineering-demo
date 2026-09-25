"""Track 50's judge, and the claims the track's lessons make about it.

Lesson 4 quotes the judge's output for six deliberate breakages. Those
quotes are asserted here, so a change to the judge that makes a lesson lie
fails CI instead of confusing a learner.

The adversarial-review cases are here too: each way a first version of the
judge could be gamed (a tag in a comment, a test that asserts nothing, a
dropped requirement hidden in another's Trace line) and each way it cried
wolf on faithful work (a hard-wrapped PRD, a `# never float()` comment).

The rubric tests guard the exercises themselves: a vague term the ticket
never uses teaches nothing, a stakeholder fact already stated in the ticket
needs no interrogation, and a fact pattern that accepts its own negation
checks nothing. Every value must discriminate.
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


def rubric(ex: Path) -> dict:
    return json.loads((ex / "rubric.json").read_text(encoding="utf-8"))


class Workspace(unittest.TestCase):
    """A fresh copy of exercise 1's solution, made the way lesson 4 says."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="track50-"))
        self.ws = self.tmp / "ws"
        starter.start("01", self.ws, with_solution=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def edit(self, rel: str, old: str, new: str) -> None:
        path = self.ws / rel
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text, f"the edit no longer applies to {rel}")
        path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")

    def write(self, rel: str, text: str) -> None:
        (self.ws / rel).write_text(text, encoding="utf-8", newline="\n")

    def judge(self, run_tests: bool = False, **kw):
        return fidelity.judge(self.ws, run_tests=run_tests, **kw)

    def assertGreen(self, **kw):
        got = findings(self.judge(**kw))
        self.assertEqual(got, [], got)

    def assertFinding(self, fragment: str, **kw):
        got = findings(self.judge(**kw))
        self.assertTrue(any(fragment in f for f in got), f"no finding containing {fragment!r}: {got}")


SPEC_01 = "openspec/changes/add-fx-convert/specs/fx/spec.md"
TESTS_01 = "impl/tests/test_app.py"


class TestLessonFourBreakages(Workspace):
    def test_copy_starts_green(self):
        self.assertGreen(run_tests=True)

    def test_a_dropped_trace_is_reported_both_ways(self):
        self.edit(SPEC_01, "Trace: PRD-7\n", "")
        got = findings(self.judge())
        self.assertTrue(any("'Health check' -- no 'Trace: PRD-<n>' line" in f for f in got), got)
        self.assertIn("prd.md -- PRD-7 is not traced by any spec requirement -- it was dropped", got)

    def test_b_renamed_scenario_is_reported_both_ways(self):
        self.edit(SPEC_01, "#### Scenario: Tie rounds down to even", "#### Scenario: Tie rounds to even")
        got = findings(self.judge())
        self.assertIn("impl/tests -- no test's docstring is 'Scenario: Tie rounds to even' "
                      "(requirement 'Half-to-even rounding')", got)
        self.assertIn("impl/tests/test_app.py -- Conversion names 'Scenario: Tie rounds down to even', "
                      "which the spec does not contain -- stale or invented", got)

    def test_c_half_up_fails_the_tie_scenarios(self):
        self.edit("impl/app.py", "ROUND_HALF_EVEN", "ROUND_HALF_UP")
        got = findings(self.judge(run_tests=True))
        self.assertEqual(len(got), 2, got)
        self.assertIn("impl/tests -- Scenario 'Tie rounds down to even': Conversion.test_tie_down fails: "
                      "AssertionError: '0.13' != '0.12'", got)
        self.assertTrue(any("Scenario 'Tie a float cannot represent'" in f for f in got), got)

    def test_d_root_user_breaks_the_rubric_rule(self):
        self.edit("impl/Dockerfile", "USER fx\n", "USER root\n")
        self.assertEqual(
            findings(self.judge()),
            ["impl/Dockerfile -- the container runs as non-root: expected /^USER (?!root\\b|0\\b)\\S+/"],
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
        self.assertGreen(run_tests=True)


class TestGamingIsCaught(Workspace):
    """Each of these was green under the first version of the judge."""

    def test_float_implementation_fails_the_reference_tests(self):
        """The README says a float version fails the audit case. Prove it,
        with the float( rubric rule out of the way so only the tests judge."""
        self.edit(
            "impl/app.py",
            "        result = (amount * rate).quantize(CENT, rounding=ROUND_HALF_EVEN)",
            "        result = Decimal(repr(round(float(amount) * float(rate), 2))).quantize(CENT)",
        )
        rules = rubric(TRACK / "exercises" / "01-docker-rest")
        rules["impl_rules"] = [r for r in rules["impl_rules"] if "float" not in r["label"]]
        self.write("rubric.json", json.dumps(rules))
        self.assertFinding("Scenario 'Tie a float cannot represent'", run_tests=True)

    def test_float_call_with_a_space_is_a_rule_finding(self):
        self.edit("impl/app.py", 'amount = Decimal(params.get("amount", [""])[0])',
                  'amount = Decimal(float (params.get("amount", ["0"])[0] or 0))')
        self.assertFinding("money is never a float: found 'float ('")

    def test_tagged_test_that_asserts_nothing(self):
        self.edit(TESTS_01, '''        """Scenario: Health check responds"""
        self.assertEqual(FxApp({}).handle("GET", "/healthz"), (200, {"status": "ok"}))''',
                  '''        """Scenario: Health check responds"""
        FxApp({}).handle("GET", "/healthz")''')
        self.assertFinding("Operations.test_health names 'Scenario: Health check responds' but asserts nothing")

    def test_tag_in_a_comment_is_not_a_test(self):
        self.edit(TESTS_01, '''        """Scenario: Health check responds"""''', '''        # TODO Scenario: Health check responds''')
        self.assertFinding("no test's docstring is 'Scenario: Health check responds'")

    def test_pytest_style_function_is_not_collected(self):
        self.edit(TESTS_01, '''        """Scenario: Tie rounds down to even"""''', '''        """Not a scenario test."""''')
        with (self.ws / TESTS_01).open("a", encoding="utf-8") as fh:
            fh.write('\n\ndef test_tie_down():\n    """Scenario: Tie rounds down to even"""\n    assert True\n')
        self.assertFinding("'test_tie_down' is a module-level function -- unittest does not collect it")

    def test_skipped_scenario_is_not_exercised(self):
        self.edit(TESTS_01, "    def test_health(self):", '    @unittest.skip("later")\n    def test_health(self):')
        self.assertFinding("not exercised (skipped): 1 scenario(s) because 'later': 'Health check responds'", run_tests=True)
        results = self.judge(run_tests=True, allow_skips=True)
        self.assertEqual(findings(results), [])
        self.assertTrue(any("Health check responds" in n for r in results for n in r.notes))

    def test_module_level_skip_is_not_exercised(self):
        self.edit(TESTS_01, "import os\n", "import os\nraise __import__('unittest').SkipTest('not today')\n")
        self.assertFinding("not exercised (skipped)", run_tests=True)

    def test_dropped_requirement_hidden_in_another_trace(self):
        spec = (self.ws / SPEC_01).read_text(encoding="utf-8")
        start = spec.index("### Requirement: Health check")
        end = spec.index("### Requirement: Container packaging")
        self.write(SPEC_01, spec[:start] + spec[end:])
        self.edit(SPEC_01, "Trace: PRD-1\n", "Trace: PRD-1, PRD-7\n")
        self.edit(TESTS_01, '''        """Scenario: Health check responds"""''', '''        """Health."""''')
        self.assertFinding("PRD-7 is only traced alongside other PRD ids")

    def test_prd_id_mentioned_in_prose_is_not_a_trace(self):
        self.edit(SPEC_01, "Trace: PRD-7\n", "")
        self.edit(SPEC_01, "The service SHALL answer `GET /healthz`", "Like PRD-7 says, the service SHALL answer `GET /healthz`")
        self.assertFinding("PRD-7 is not traced by any spec requirement")

    def test_duplicate_scenario_names(self):
        self.edit(SPEC_01, "#### Scenario: Unknown path", "#### Scenario: Missing amount")
        self.assertFinding("scenario name 'Missing amount' is also used by")

    def test_last_user_line_decides(self):
        self.edit("impl/Dockerfile", "USER fx\n", "USER fx\nUSER root\n")
        self.assertFinding("the container runs as non-root")

    def test_last_from_line_decides(self):
        self.edit("impl/Dockerfile", "FROM python:3.12-slim\n", "FROM python:3.12-slim AS base\nFROM python:3.13\n")
        self.assertFinding("the final image is built from the one ops approved")

    def test_pip_across_a_line_continuation(self):
        self.edit("impl/Dockerfile", "USER fx\n", "RUN pip3 \\\n    install flask\nUSER fx\n")
        self.assertFinding("no third-party packages: found")

    def test_rates_as_json_numbers(self):
        self.edit("impl/rates.json", '"EUR": "0.92"', '"EUR": 0.92')
        self.assertFinding("rates are strings in the file")

    def test_prd_stating_the_opposite(self):
        self.edit("prd.md", "MUST be JSON strings, never numbers.", "MUST be JSON numbers, parsed from the query string.")
        self.assertFinding("contradicts the product owner on that money values are JSON strings")


class TestNoCryingWolf(Workspace):
    """Each of these is faithful work the first version rejected."""

    def test_trace_after_the_scenarios(self):
        self.edit(SPEC_01, "Trace: PRD-7\n\n#### Scenario: Health check responds\n", "#### Scenario: Health check responds\n")
        self.edit(SPEC_01, "- **THEN** the status is 200 and the body is `{\"status\": \"ok\"}`\n",
                  "- **THEN** the status is 200 and the body is `{\"status\": \"ok\"}`\n\nTrace: PRD-7\n")
        self.assertGreen()

    def test_comment_mentioning_a_forbidden_call(self):
        self.edit("impl/app.py", "CENT = Decimal", "# Never float(): money must round-trip exactly.\nCENT = Decimal")
        self.assertGreen()

    def test_leading_zero_ids_and_alias_headings(self):
        prd = (self.ws / "prd.md").read_text(encoding="utf-8")
        prd = re.sub(r"### PRD-(\d)\b", r"### PRD-0\1", prd).replace("## Non-goals", "## Out of Scope")
        self.write("prd.md", prd.replace("## Requirements", "## Functional Requirements"))
        self.assertGreen()

    def test_hard_wrapped_fact(self):
        self.edit("prd.md", "The service SHALL respond 400 `{\"error\": \"invalid_amount\"}` when `amount`",
                  "The service SHALL respond 400\n`{\"error\": \"invalid_amount\"}` when `amount`")
        self.assertGreen()

    def test_vague_word_in_quotes_or_code_is_not_flagged(self):
        self.edit("prd.md", "The service SHALL answer `GET /healthz`",
                  "Ops asked \"should it be fast?\"; the service SHALL answer `GET /healthz` (`fast` path)")
        self.assertGreen()

    def test_negated_contradiction_is_not_a_contradiction(self):
        self.edit("prd.md", "MUST be JSON strings, never numbers.",
                  "MUST be JSON strings.\n- WHEN a response is serialised THEN no money value appears as JSON floats")
        self.assertGreen()

    def test_same_requirement_name_in_two_capabilities(self):
        spec_dir = self.ws / "openspec/changes/add-fx-convert/specs"
        (spec_dir / "ops").mkdir()
        (spec_dir / "ops" / "spec.md").write_text(
            "## ADDED Requirements\n\n### Requirement: Health check\n\nThe probe SHALL poll `/healthz`.\n\n"
            "Trace: PRD-7\n\n#### Scenario: Probe polls\n\n- **WHEN** ops deploys\n- **THEN** the probe polls\n",
            encoding="utf-8",
        )
        got = findings(self.judge())
        self.assertFalse(any("duplicate requirement" in f for f in got), got)

    def test_archive_is_not_an_active_change(self):
        (self.ws / "openspec" / "changes" / "archive").mkdir()
        self.assertGreen()


class TestJudgeRules(Workspace):
    def test_shall_only_in_header_gets_the_specific_hint(self):
        self.edit(SPEC_01, "### Requirement: Health check\n\nThe service SHALL answer",
                  "### Requirement: Health check SHALL work\n\nThe service answers")
        self.assertFinding("only in the header")

    def test_requirement_outside_a_delta_section_is_reported(self):
        self.edit(SPEC_01, "## ADDED Requirements", "## Requirements\n\n### Requirement: Stray\nThe service SHALL x.\n\n## ADDED Requirements")
        self.assertFinding("'Stray' is outside a delta section")

    def test_scenario_without_then_is_reported(self):
        self.edit(SPEC_01, "- **THEN** the status is 200 and the body is `{\"status\": \"ok\"}`", "- **AND** nothing else")
        self.assertFinding("'Health check responds' needs WHEN and THEN")

    def test_unresolved_open_question_is_reported(self):
        self.edit("prd.md", "None open. Resolved during review:", "- Who owns rates.json? TBD")
        self.assertFinding("unresolved")

    def test_unticked_task_is_reported(self):
        self.edit("openspec/changes/add-fx-convert/tasks.md", "- [x] 3.1", "- [ ] 3.1")
        self.assertFinding("unticked: 3.1")

    def test_two_active_changes_are_ambiguous(self):
        (self.ws / "openspec" / "changes" / "second-change").mkdir()
        self.assertFinding("exactly one active change")

    def test_missing_init_is_one_clear_finding(self):
        (self.ws / "impl" / "tests" / "__init__.py").unlink()
        got = [f for f in findings(self.judge(run_tests=True)) if "impl/tests" in f]
        self.assertEqual(got, ["impl/tests -- no __init__.py -- unittest discovery needs tests/ to be a package (an empty file is enough)"])

    def test_misnamed_test_file_is_one_clear_finding(self):
        (self.ws / TESTS_01).rename(self.ws / "impl" / "tests" / "app_test.py")
        got = [f for f in findings(self.judge(run_tests=True)) if "impl/tests" in f]
        self.assertEqual(got, ["impl/tests -- no test_*.py files (found app_test.py) -- unittest discovers test_*.py only"])

    def test_report_uses_the_enforcer_shape(self):
        text = fidelity.report(self.judge())
        self.assertTrue(text.startswith("## Constraint Results"))
        self.assertIn("Summary: 3 passed, 0 failed, 0 unchecked", text)

    def test_exit_zero(self):
        (self.ws / "prd.md").unlink()
        self.assertEqual(fidelity.main([str(self.ws), "--no-tests", "--exit-zero"]), 0)
        self.assertEqual(fidelity.main([str(self.ws), "--no-tests"]), 1)


class TestMcpSmoke(unittest.TestCase):
    """Found by a Haiku trial: a server whose own tests passed and which no
    MCP client could use. The judge now talks to it over stdio."""

    RULE = next(r for r in rubric(TRACK / "exercises" / "03-mcp-cli-tools")["impl_rules"] if "mcp_smoke" in r)

    def test_reference_server_passes(self):
        impl = TRACK / "exercises" / "03-mcp-cli-tools" / "solution" / "impl"
        problems, notes = fidelity.mcp_smoke(impl, self.RULE)
        self.assertEqual(problems, [])
        # A note is only acceptable for a CLI this machine lacks -- CI
        # runners have git but not rg, and a test that assumed otherwise
        # passed locally and failed every CI job.
        for note in notes:
            binary = "rg" if note.startswith("rg_") else "git"
            with self.subTest(note=note):
                self.assertIsNone(shutil.which(binary), note)

    def test_reply_without_id_is_caught(self):
        tmp = Path(tempfile.mkdtemp(prefix="track50-mcp-"))
        try:
            (tmp / "server.py").write_text(
                "import json, sys\n"
                "for line in sys.stdin:\n"
                "    msg = json.loads(line)\n"
                "    print(json.dumps({'protocolVersion': '2025-06-18', 'capabilities': {}}), flush=True)\n",
                encoding="utf-8",
            )
            problems, _ = fidelity.mcp_smoke(tmp, self.RULE)
            self.assertTrue(any("no id" in p for p in problems), problems)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_initialize_without_capabilities_is_caught(self):
        """The second Haiku server echoed ids and still failed in Claude Code."""
        tmp = Path(tempfile.mkdtemp(prefix="track50-mcp-"))
        try:
            (tmp / "server.py").write_text(
                "import json, sys\n"
                "for line in sys.stdin:\n"
                "    m = json.loads(line)\n"
                "    if 'id' not in m: continue\n"
                "    r = {'protocolVersion': '2025-06-18', 'serverInfo': {'name': 'x', 'version': '1'}}\n"
                "    if m['method'] == 'tools/call': r = {'isError': True, 'reason': 'no repo'}\n"
                "    print(json.dumps({'jsonrpc': '2.0', 'id': m['id'], 'result': r}), flush=True)\n",
                encoding="utf-8",
            )
            problems, _ = fidelity.mcp_smoke(tmp, self.RULE)
            self.assertTrue(any("capabilities" in p for p in problems), problems)
            self.assertTrue(any("result.content must be a list" in p for p in problems), problems)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    @unittest.skipUnless(shutil.which("git"), "git not installed")
    def test_unvalidated_limit_is_caught(self):
        """The fourth Haiku server spoke perfect MCP and accepted limit=99."""
        tmp = Path(tempfile.mkdtemp(prefix="track50-mcp-"))
        try:
            (tmp / "server.py").write_text(
                "import json, subprocess, sys\n"
                "root = sys.argv[sys.argv.index('--root') + 1]\n"
                "TOOLS = [{'name': n, 'inputSchema': {'type': 'object'}} for n in ('git_status', 'git_log', 'git_diff_stat', 'rg_search')]\n"
                "def ok(t): return {'content': [{'type': 'text', 'text': t}], 'isError': False}\n"
                "for line in sys.stdin:\n"
                "    m = json.loads(line)\n"
                "    if 'id' not in m: continue\n"
                "    if m['method'] == 'initialize':\n"
                "        r = {'protocolVersion': '2025-06-18', 'capabilities': {'tools': {}}, 'serverInfo': {'name': 'x', 'version': '1'}}\n"
                "    elif m['method'] == 'tools/list': r = {'tools': TOOLS}\n"
                "    else:\n"
                "        name, args = m['params']['name'], m['params'].get('arguments', {})\n"
                "        if name == 'git_log':\n"
                "            p = subprocess.run(['git', 'log', '--oneline', '-n', str(args.get('limit', 10))], cwd=root, capture_output=True, text=True)\n"
                "            r = ok(p.stdout)\n"
                "        elif name in ('git_status', 'git_diff_stat'): r = ok('')\n"
                "        else: r = {'content': [{'type': 'text', 'text': 'nope'}], 'isError': True}\n"
                "    print(json.dumps({'jsonrpc': '2.0', 'id': m['id'], 'result': r}), flush=True)\n",
                encoding="utf-8",
            )
            problems, _ = fidelity.mcp_smoke(tmp, self.RULE)
            self.assertTrue(any('git_log {"limit": 51} was accepted' in p for p in problems), problems)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_answering_a_notification_is_caught(self):
        tmp = Path(tempfile.mkdtemp(prefix="track50-mcp-"))
        try:
            (tmp / "server.py").write_text(
                "import json, sys\n"
                "TOOLS = [{'name': n, 'inputSchema': {}} for n in ('git_status', 'git_log', 'git_diff_stat', 'rg_search')]\n"
                "for line in sys.stdin:\n"
                "    m = json.loads(line)\n"
                "    r = {'protocolVersion': '2025-06-18'} if m['method'] == 'initialize' else {'tools': TOOLS}\n"
                "    out = {'jsonrpc': '2.0', 'id': m.get('id', 99), 'result': r}\n"
                "    if m['method'] == 'tools/call':\n"
                "        out = {'jsonrpc': '2.0', 'id': m['id'], 'error': {'code': -32602, 'message': 'x'}}\n"
                "    print(json.dumps(out), flush=True)\n",
                encoding="utf-8",
            )
            problems, _ = fidelity.mcp_smoke(tmp, self.RULE)
            self.assertTrue(any("answered a notification" in p for p in problems), problems)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestRubricsDiscriminate(unittest.TestCase):
    def test_three_exercises(self):
        self.assertEqual([d.name[:2] for d in EXERCISES], ["01", "02", "03"])

    def test_every_vague_term_is_in_the_ticket(self):
        for ex in EXERCISES:
            ticket = (ex / "ticket.md").read_text(encoding="utf-8")
            for term in rubric(ex)["vague_terms"]:
                with self.subTest(exercise=ex.name, term=term):
                    self.assertRegex(ticket, re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE))

    def test_no_stakeholder_fact_is_already_in_the_ticket(self):
        """If the ticket already says it, asking for it teaches nothing."""
        for ex in EXERCISES:
            ticket = fidelity.flatten((ex / "ticket.md").read_text(encoding="utf-8"))
            for fact in rubric(ex)["prd_facts"]:
                with self.subTest(exercise=ex.name, fact=fact["label"]):
                    self.assertEqual(fidelity.fact_verdict(fact, ticket), "missing")

    def test_every_fact_cites_an_answer_that_exists(self):
        for ex in EXERCISES:
            answers = (ex / "stakeholder-answers.md").read_text(encoding="utf-8")
            for fact in rubric(ex)["prd_facts"]:
                for q in re.findall(r"Q\d+", fact["source"]):
                    with self.subTest(exercise=ex.name, source=q):
                        self.assertIn(f"**{q}.", answers)

    def test_examples_pass_and_counterexamples_fail(self):
        """The rubric tests itself: a fact that accepts its own negation, or
        rejects a faithful rephrasing, is a broken fact."""
        for ex in EXERCISES:
            for fact in rubric(ex)["prd_facts"]:
                for text in fact.get("examples", []):
                    with self.subTest(exercise=ex.name, fact=fact["label"], example=text[:50]):
                        self.assertEqual(fidelity.fact_verdict(fact, fidelity.flatten(text)), "ok")
                for text in fact.get("counterexamples", []):
                    with self.subTest(exercise=ex.name, fact=fact["label"], counterexample=text[:50]):
                        self.assertNotEqual(fidelity.fact_verdict(fact, fidelity.flatten(text)), "ok")

    def test_every_fact_is_needed(self):
        """Removing the sentences that state a fact must fail the reference PRD."""
        for ex in EXERCISES:
            prd = (ex / "solution" / "prd.md").read_text(encoding="utf-8")
            reqs = fidelity.prd_requirements(prd)
            stated = fidelity.flatten("\n\n".join(body for _, body in reqs.values()))
            for fact in rubric(ex)["prd_facts"]:
                with self.subTest(exercise=ex.name, fact=fact["label"]):
                    self.assertEqual(fidelity.fact_verdict(fact, stated), "ok", "the reference PRD does not state it")
                    without = "\n".join(
                        u for u in stated.splitlines()
                        if not any(re.search(p, u, re.IGNORECASE) for p in fact["any_of"])
                    )
                    self.assertEqual(fidelity.fact_verdict(fact, without), "missing")


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
                self.assertNotIn("rubric.json", names)
                self.assertTrue((self.tmp / f"{ex.name}.stakeholder-answers.md").is_file())
                self.assertTrue((ws / "openspec" / "config.yaml").is_file())
                self.assertTrue((ws / ".claude" / "commands" / "fidelity" / "prd.md").is_file())
                self.assertFalse(fidelity.judge(ws, run_tests=False)[0].ok)

    def test_no_stakeholder_fact_is_readable_in_the_workspace(self):
        """The review's first critical finding: rubric.json and HARNESS.md
        used to hand Claude the answers it was supposed to ask for."""
        for ex in EXERCISES:
            ws = self.tmp / f"leak-{ex.name}"
            starter.start(ex.name[:2], ws)
            everything = fidelity.flatten("\n\n".join(
                p.read_text(encoding="utf-8") for p in sorted(ws.rglob("*"))
                if p.is_file() and "personas" not in p.parts
            ))
            for fact in rubric(ex)["prd_facts"]:
                with self.subTest(exercise=ex.name, fact=fact["label"]):
                    hits = [m.group(0) for p in fact["any_of"] for m in [re.search(p, everything, re.IGNORECASE)] if m]
                    self.assertEqual(hits, [], f"the workspace states {fact['label']}")

    def test_with_solution_is_green(self):
        for ex in EXERCISES:
            with self.subTest(exercise=ex.name):
                ws = self.tmp / f"sol-{ex.name}"
                starter.start(ex.name[:2], ws, with_solution=True)
                self.assertEqual(findings(fidelity.judge(ws, run_tests=False)), [])

    def test_refuses_a_workspace_inside_the_repo(self):
        with self.assertRaises(SystemExit):
            starter.main(["01", str(TRACK / "exercises" / "01-docker-rest" / "scratch")])
        self.assertFalse((TRACK / "exercises" / "01-docker-rest" / "scratch").exists())

    def test_commands_are_filled_in(self):
        ws = self.tmp / "cmds"
        starter.start("02", ws)
        for cmd in (ws / ".claude" / "commands" / "fidelity").glob("*.md"):
            with self.subTest(command=cmd.name):
                self.assertNotIn("{{", cmd.read_text(encoding="utf-8"))
        self.assertIn('"has memory"', (ws / ".claude" / "commands" / "fidelity" / "prd.md").read_text(encoding="utf-8"))

    def test_commands_that_run_the_judge_exit_zero(self):
        """Claude Code aborts a slash command whose `!` line exits non-zero."""
        for prompt in (TRACK / "prompts").glob("*.md"):
            for line in prompt.read_text(encoding="utf-8").splitlines():
                if line.startswith("!`"):
                    with self.subTest(prompt=prompt.name):
                        self.assertIn("--exit-zero", line)

    def test_openspec_rules_are_quoted(self):
        """Unquoted, a rule containing ': ' is a YAML mapping and OpenSpec
        silently drops every rule for that artifact."""
        for line in (TRACK / "openspec-config.yaml").read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("- ") and ": " in line:
                with self.subTest(line=line):
                    self.assertRegex(line.strip(), r"^- '.*'$")


if __name__ == "__main__":
    unittest.main()
