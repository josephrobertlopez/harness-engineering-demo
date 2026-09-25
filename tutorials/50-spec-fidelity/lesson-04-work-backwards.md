# Lesson 4 — Work backwards from the solution first

Each exercise ships a finished chain in `solution/`: PRD, OpenSpec change,
implementation, tests. Before you write your own, read that chain **from
the end to the start**. Every artifact there exists because of one before
it, and reading backwards is the fastest way to see why each one is there.

This lesson walks exercise 1. Each exercise README has a shorter walk of
its own.

## 1. Get a copy you can break

```bash
python tutorials/50-spec-fidelity/start.py 01 ~/fidelity/backwards --with-solution
cd ~/fidelity/backwards
python <repo>/tutorials/50-spec-fidelity/spec_fidelity.py .
```

```
### PRD is OpenSpec-ready — PASS
### OpenSpec change is valid and traces to the PRD — PASS
### Implementation is faithful to the spec — PASS
---
Summary: 3 passed, 0 failed, 0 unchecked
```

That is the finish line. Everything below explains how it got there.

## 2. Walk one thread from test to ticket

Pick the test that looks most arbitrary. In exercise 1 that is this one:

```python
def test_tie_down(self):
    """Scenario: Tie rounds down to even"""
    _, body = self.app.handle("GET", "/convert?amount=0.125&from=USD&to=USD")
    self.assertEqual(body["result"], "0.12")
```

Why would anyone convert USD to USD? Follow the tag:

| step | where | what you find |
|---|---|---|
| test → scenario | `grep -rn "Tie rounds down to even" openspec/` | `#### Scenario: Tie rounds down to even` under `### Requirement: Half-to-even rounding` |
| scenario → requirement | same file, a few lines up | `The service SHALL round result ... using round-half-to-even` and `Trace: PRD-2` |
| requirement → PRD | `prd.md`, `### PRD-2` | "Round the way finance audits" — `Source: stakeholder-answers.md Q3` |
| PRD → answer | the stakeholder file, Q3 | "banker's rounding … Finance audits against that." |
| answer → ticket | `ticket.md` | **nothing.** The ticket never mentions rounding. |

The requirement finance audits against has no words in the ticket. It
exists only because someone asked "how is the result rounded?". A
developer who did not ask would have used `round()` — which in Python *is*
half-to-even for floats, would have passed a casual test, and would still
have been wrong the first time a float could not represent the tie exactly.
The USD→USD conversion is simply the cleanest way to put an exact tie in
front of the code.

## 3. Walk one thread from ticket to test

Now go the other way, from the vaguest phrase in the ticket:

> Should be fast

| step | where | what you find |
|---|---|---|
| ticket → PRD | `prd.md`, Open questions | "Should be fast" → PRD-3 (no per-request I/O). Resolved with the PO. |
| PRD → requirement | `Trace: PRD-3` | `Rates loaded once at startup` — MUST NOT read the file or call the network while serving |
| requirement → scenario | | `Rates file removed after startup` |
| scenario → test | `test_rates_file_removed_after_startup` | copies the rates file, starts the app, **deletes the file**, converts |

"Fast" became a *structural* property with a test that cannot pass by
accident. Nobody could name a latency number, so the PRD's Non-goals say so
out loud rather than inventing one.

Do this walk for two more threads of your choice before moving on. You are
looking for the moment where a vague word became something checkable.

## 4. Break it on purpose

Each change below takes a few seconds. Run the judge after each, read the
finding, then undo it (or re-run `start.py` into a fresh folder). The
outputs shown are what the judge actually prints.

**a. Drop a trace.** In the spec, delete the line `Trace: PRD-7`.

```
- ...spec.md:121 'Health check' -- no 'Trace: PRD-<n>' line -- trace it to the PRD, or cut it (gold-plating)
- prd.md -- PRD-7 is not traced by any spec requirement -- it was dropped
```

One edit, two findings: the requirement is now an orphan *and* the PRD
item is unaccounted for. Both directions matter.

Try the sneakier version too: instead of deleting the line, delete the
whole Health check requirement and change `Trace: PRD-1` to
`Trace: PRD-1, PRD-7`. Every id is still "traced". The judge still says
`PRD-7 is only traced alongside other PRD ids` — a model tidying traces
does exactly this, so every PRD item must have a requirement of its own.

**b. Rename a scenario.** Change `#### Scenario: Tie rounds down to even`
to `#### Scenario: Tie rounds to even`.

```
- impl/tests/test_app.py -- Conversion names 'Scenario: Tie rounds down to even', which the spec does not contain -- stale or invented
- impl/tests -- no test's docstring is 'Scenario: Tie rounds to even' (requirement 'Half-to-even rounding')
```

This is how spec drift looks in real projects: the spec moved, the test did
not, and until now nothing noticed.

**c. Break the behaviour.** In `impl/app.py`, replace every
`ROUND_HALF_EVEN` with `ROUND_HALF_UP`.

```
- impl/tests -- Scenario 'Tie rounds down to even': Conversion.test_tie_down fails: AssertionError: '0.13' != '0.12'
- impl/tests -- Scenario 'Tie a float cannot represent': Conversion.test_tie_a_float_cannot_represent fails: AssertionError: '0.17' != '0.16'
```

Only the tie tests notice, and the judge names the *scenario* each one
proves, not just a test id. That is why the spec has tie scenarios and not
a general "rounds correctly": a value that rounds the same under both rules
proves nothing.

The third tie, 2.675, exists for a different mistake. An adversarial
review of this track found that 0.125 and 0.135 round the same under a
binary float too — so a float implementation passed the original tests,
and the README's claim that it would fail was false. 2.675 (float: 2.67,
Decimal half-even: 2.68) and 0.165 are values where they disagree.

**d. Run as root.** In `impl/Dockerfile`, change `USER fx` to `USER root`.

```
- impl/tests -- Scenario 'Non-root image': Operations.test_non_root_image fails: AssertionError: 'root' unexpectedly found in {'0', 'root'}
- impl/Dockerfile -- the container runs as non-root: expected /^USER (?!root\b|0\b)\S+/
```

Two nets catch it: the scenario's own test, and an exercise-specific rule
from `rubric.json`. The rule checks the *last* `USER` line, because only
that one decides who the container runs as.

**e. Let a vague word back in.** In `prd.md`'s PRD-3, add the words
"so it is fast".

```
- prd.md PRD-3 -- vague term 'fast' -- replace it with the number or behaviour it stands for
### OpenSpec change is valid and traces to the PRD — UNCHECKED
### Implementation is faithful to the spec — UNCHECKED
```

The later stages are skipped, not failed. A spec judged against a broken
PRD produces a wall of findings with one root cause.

**f. Gold-plate it.** In `FxApp.handle`, add a `/currencies` endpoint that
lists the rate table.

```
Summary: 3 passed, 0 failed, 0 unchecked
```

**Green.** Nothing structural broke: every scenario is still tested, every
test still passes. The deterministic judge cannot see a feature nobody
asked for — which is exactly the `No gold-plating` constraint in
`HARNESS.md`, and exactly why it is `Enforcement: agent`. Run step 5 of
lesson 3 against this copy and watch the `harness-enforcer` find it.

## 5. Now go forward

Delete the copy, run `start.py` *without* `--with-solution`, and do the
exercise from `ticket.md`. Resist opening `solution/` again until your own
judge is green. Then compare the two PRDs side by side — especially the
Non-goals. The requirements are usually close. The places where you and the
reference disagree about what is *out* of scope are where the interesting
conversations with a product owner happen.

---

Now pick an exercise: [01 Docker REST](exercises/01-docker-rest/README.md) ·
[02 LangChain chatbot](exercises/02-langchain-chatbot/README.md) ·
[03 MCP CLI tools](exercises/03-mcp-cli-tools/README.md)
