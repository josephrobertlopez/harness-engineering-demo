# Lesson 3 — The loop with Claude: prompts for every arrow

Five steps. Each ends with the judge, so you find a problem at the step
that caused it, not three steps later.

Every prompt in this lesson is also installed as a **slash command** in the
workspace `start.py` creates, so you can type the command instead of
pasting. The commands live in `.claude/commands/fidelity/` — read them,
and change them when they do not fit. They are this lesson in executable
form; the source is [`prompts/`](prompts/).

| step | command | writes |
|---|---|---|
| 1 | `/fidelity:interrogate [your answers]` | `interview.md` (append-only Q&A) |
| 2 | `/fidelity:prd` | `prd.md`, then runs the judge on it |
| 2b | `/fidelity:review-prd` | nothing — an adversarial review |
| 3 | `/fidelity:propose <change-id>` | `openspec/changes/<id>/` |
| 4 | `/fidelity:build` | `impl/`, test-first |
| any | `/fidelity:judge` | nothing — runs the judge and explains each finding |
| 5 | `/fidelity:enforce` | nothing — the agent half, via the plugin if installed |

The commands were exercised end to end with Claude Haiku as the developer
and a second Haiku playing the product owner; see
[the trial notes](README.md#tested-with-haiku).

## Step 0 — Set up a workspace Claude cannot cheat in

```bash
python tutorials/50-spec-fidelity/start.py 01 ~/fidelity/ops-1432
cd ~/fidelity/ops-1432
openspec init --tools claude     # optional; skip if you will write the change by hand
claude
```

Open `~/fidelity/ops-1432.stakeholder-answers.md` in your editor, **not**
in Claude. For this exercise you are the product owner. Claude only gets an
answer when it asks the question.

## Step 1 — Interrogate the ticket

```text
Read personas/spec-interrogator.persona.md and act as that persona.

ticket.md is a Jira ticket I have been assigned. Before anything is
designed, list every assumption it makes but does not state, and ask me
the questions that would resolve them -- success criteria first, then
constraints, then edge cases. Ask in batches of at most five. I am the
product owner; answer nothing yourself.
```

With the command: `/fidelity:interrogate` asks the first batch and starts
`interview.md`; answer with `/fidelity:interrogate 1. ... 2. ...`, and it
records your answers and asks the next batch, until it says
`INTERVIEW COMPLETE`. The interview file is the only source the PRD step is
allowed to use, which is what makes "you never asked" visible later.

Answer from the stakeholder file, **only what was asked**, in your own
words. When Claude asks something the file does not cover, say "no
decision; treat it as a non-goal" and watch where it goes.

Keep a tally of the answers you gave that Claude did *not* ask for. That
tally is the lesson: those are the questions a developer handed this ticket
would have skipped.

## Step 2 — Write the PRD, then review it against OpenSpec

```text
Write prd.md from the ticket and my answers. Sections: Problem, Users,
Requirements, Non-goals, Open questions. Each requirement is
"### PRD-<n>: <title>", states behaviour with SHALL or MUST, has at least
one "WHEN ... THEN ..." acceptance line, and ends with
"Source: <which answer it came from>". Do not use the ticket's vague words
("should", "fast", ... -- list them) inside a requirement. Anything I did
not decide goes in Non-goals or Open questions, not in a requirement.
```

Then judge it, and ask for an adversarial review in the same breath. The
judge command is the one `start.py` printed (`python <path-to-repo>/tutorials/50-spec-fidelity/spec_fidelity.py <workspace>`);
from inside the workspace:

```bash
python /path/to/harness-engineering-demo/tutorials/50-spec-fidelity/spec_fidelity.py . --stage prd
```

`/fidelity:prd` runs it for you and fixes what it can. When a finding says
the PRD "does not pin down" something, that is a question nobody asked:
the command is told to stop and hand it back to you, not to guess. When it
says the PRD "contradicts the product owner", the wording states the
opposite of an answer.

```text
Read personas/spec-adversary.persona.md and act as that persona. Review
prd.md for OpenSpec readiness: for each requirement, name the input or
state it does not cover, any requirement a test could pass without the
behaviour existing, and any pair of requirements that contradict. Do not
propose code. Rank by severity.
```

The judge finds the structural gaps; the Adversary finds the semantic ones.
Fix both, then re-run `--stage prd` until it passes. If the Adversary
raises a question the stakeholder file does not answer, it goes in Open
questions, resolved, or in Non-goals — never silently into a requirement.

> With the ai-literacy-superpowers plugin installed, `/diaboli <path>` runs
> its `advocatus-diaboli` agent in spec mode and writes an objection record
> you disposition one by one. It expects specs under
> `docs/superpowers/specs/`; point it at `prd.md` anyway, or copy the PRD
> there. It is the heavier, recorded version of the Adversary prompt above.

## Step 3 — Propose the OpenSpec change

With OpenSpec installed:

```text
/opsx:propose <change-id>

Derive it from prd.md. One capability. Every requirement traces to a PRD
id; every PRD id is traced. Nothing from Non-goals.
```

Without it, the same instruction plus "write openspec/changes/<id>/ with
proposal.md, design.md, tasks.md and specs/<capability>/spec.md in
OpenSpec's delta format" works — lesson 2 has the format.

Pick a kebab-case, verb-first id: `add-fx-convert`, `add-help-chat`,
`add-cli-mcp`. `/fidelity:propose <change-id>` does the same without
OpenSpec installed.

```bash
python /path/to/harness-engineering-demo/tutorials/50-spec-fidelity/spec_fidelity.py . --stage spec
openspec validate --strict       # if installed
```

Read `design.md` yourself before moving on. It is the only artifact that
records *why* the code will look the way it does, and it is the one the
agent judge compares the code against.

## Step 4 — Build it, test first

```text
Read personas/spec-implementer.persona.md and act as that persona.

Implement openspec/changes/<id>/ in impl/. Where the persona and this
prompt disagree, this prompt wins. Test first: for each "#### Scenario:"
write one test method on a unittest.TestCase class whose docstring's first
line is exactly "Scenario: <scenario name>", run it and watch it fail,
then implement. Tests live in impl/tests/test_*.py, with an empty
impl/tests/__init__.py, and run with
"python -m unittest discover -s tests -t ." from impl/. Tick each task in
tasks.md as it is done. Implement nothing the spec does not ask for; if
you think the spec is missing something, stop and tell me instead.
```

What counts as a tested scenario is strict, because the first version of
the judge was easy to fool: the test must be a `TestCase` method (pytest
functions are not collected), must assert something, and must actually
run and pass. A skipped test is "not exercised" — a finding, unless you
pass `--allow-skips` knowingly.

(`/opsx:apply` does the same job; add the test-first and scenario-tag
instructions to it.)

The last sentence matters most. An implementer who "helpfully" adds
something is the gold-plating the agent judge will flag, and the time to
catch it is before it is written.

```bash
python /path/to/harness-engineering-demo/tutorials/50-spec-fidelity/spec_fidelity.py .   # all three stages
```

## Step 5 — The agent half of the judge

The deterministic judge cannot tell whether a test named
`Scenario: Refused message is not remembered` actually checks the history.
That is the `harness-enforcer`'s job.

```bash
claude plugin marketplace add Habitat-Thinking/ai-literacy-superpowers
claude plugin install ai-literacy-superpowers
```

Then, in Claude Code in the workspace, run `/fidelity:enforce`, or:

```text
Use the harness-enforcer agent to verify every pr-scoped constraint in
HARNESS.md against this folder. Run the deterministic ones first; for the
agent ones, quote the rule and report findings with file:line.
```

`/harness-audit` does this and more (it also checks whether `HARNESS.md`
matches reality, and updates a status section). For a single exercise the
direct prompt is enough.

You are done when:

- `spec_fidelity.py` reports `3 passed, 0 failed, 0 unchecked` **without**
  `--allow-skips`, and
- the enforcer reports no findings on the agent constraints, or you have
  written down why each remaining one is acceptable.

## If a step goes wrong

| symptom | usually means | go back to |
|---|---|---|
| `--stage prd`: "does not pin down X" | you never asked about X | step 1; ask it now |
| `--stage spec`: "PRD-n is not traced" | propose dropped a requirement | step 3; do not delete PRD-n to make it pass |
| `--stage spec`: "traces to no PRD requirement" | propose invented one | step 3; cut it, or add it to the PRD *with a source* |
| `--stage build`: "names a scenario the spec does not contain" | the spec changed after the test was written | re-derive the test from the current scenario |
| enforcer: "asserts less than its THEN" | the test was written to pass, not to check | step 4; rewrite the assertion first |

---

Next: [Lesson 4 — Work backwards from the solution first](lesson-04-work-backwards.md)
