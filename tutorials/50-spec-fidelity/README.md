# Track 50 — From a vague ticket to a faithful build

**~3 hours for all three exercises. Graded offline; a live Claude is how you
do the work.**

Every exercise starts where real work starts: a Jira ticket that says
"should be fast", "make it safe", "remember stuff". You turn it into a PRD
with Claude and review that PRD against OpenSpec's rules. Then you derive an
OpenSpec change and build it. Last, a judge decides whether what you built
is *faithful* to what was asked — nothing dropped, nothing invented.

```
ticket.md ──interrogate──▶ prd.md ──review──▶ openspec/changes/<id>/ ──apply──▶ impl/
  vague        (Claude asks,     (OpenSpec-      proposal · design ·           code + one test
               you answer as     ready?)         tasks · spec deltas           per scenario
               the PO)
                                         ▲                                     │
                                         └──────── the judge: does each ───────┘
                                                   arrow preserve the one before it?
```

| # | Exercise | You build | Ticket |
|---|---|---|---|
| 1 | [Docker REST function](exercises/01-docker-rest/README.md) | a containerised `GET /convert` currency function | OPS-1432 |
| 2 | [LangChain chatbot](exercises/02-langchain-chatbot/README.md) | a help-centre bot grounded on an FAQ, with memory and guardrails | SUP-88 |
| 3 | [MCP server for CLIs](exercises/03-mcp-cli-tools/README.md) | a stdio MCP server exposing four read-only `git`/`rg` tools to Claude Code | DEVX-311 |

They get harder in a specific way. In 1 the vague words hide numbers. In 2
they hide a safety property that is easy to fake with a prompt line. In 3
they hide a whole attack surface.

## Where the judging comes from

The framing is **habitat engineering**, from the
[ai-literacy-superpowers](https://habitat-thinking.github.io/ai-literacy-superpowers/plugins/ai-literacy-superpowers/explanation/habitat-engineering/)
plugin by Habitat-Thinking: *when an AI produces bad output, the problem is
almost never the AI — it is the environment it is operating in.* A vague
ticket is a poor environment. A PRD, an OpenSpec change and a `HARNESS.md`
are how you improve it before any code exists.

Fidelity is judged in two halves, the same split that plugin uses:

| half | what judges it | runs | checks |
|---|---|---|---|
| **deterministic** | [`spec_fidelity.py`](spec_fidelity.py) | offline, in CI, in a second | structure, tracing, scenario ↔ test coverage, tests pass, exercise rules |
| **agent** | the plugin's `harness-enforcer` agent, reading the exercise's `HARNESS.md` | needs Claude Code + the plugin | does the code *mean* what the spec means? Is anything gold-plated? |

The deterministic judge prints its report in the `harness-enforcer`'s own
format, because it *is* the `Tool:` line of the deterministic constraints in
each `HARNESS.md`. One report covers both halves.

> **About the borrowed tools.** [OpenSpec](https://github.com/Fission-AI/OpenSpec)
> (Fission-AI) and [ai-literacy-superpowers](https://github.com/Habitat-Thinking/ai-literacy-superpowers)
> (Habitat-Thinking) are MIT-licensed projects by other people. This track is
> my reading of them, checked against OpenSpec 1.13.2 and the plugin's
> `main` as of September 2026. Go to the source for anything authoritative.

## Lessons

| # | Lesson | Time |
|---|---|---|
| 1 | [Fidelity, and why the ticket is the environment](lesson-01-fidelity.md) | 10 min |
| 2 | [OpenSpec in ten minutes — and what the judge enforces](lesson-02-openspec.md) | 15 min |
| 3 | [The loop with Claude — prompts for every arrow](lesson-03-the-loop.md) | 20 min |
| 4 | [Work backwards from the solution first](lesson-04-work-backwards.md) | 15 min |

Do lesson 4's walkthrough on exercise 1's solution before you write anything
of your own. Seeing the finished chain first is how you know what each step
is for.

## Prerequisites

| for | you need |
|---|---|
| judging, all exercises | Python 3.12+. Nothing else. |
| doing the work | [Claude Code](https://code.claude.com/docs) |
| the agent half of the judge | `claude plugin marketplace add Habitat-Thinking/ai-literacy-superpowers` then `claude plugin install ai-literacy-superpowers` |
| optional: the real OpenSpec CLI | Node 20.19+, `npm install -g @fission-ai/openspec@latest` |
| exercise 1, to run the image | Docker |
| exercise 2, to run the chain tests | `pip install langchain-core langchain-anthropic` |
| exercise 3, to use it in Claude Code | `git` and `rg` on your PATH |

## Checking your work

```bash
# set up a clean workspace for exercise 1 (outside the repo -- see start.py for why)
python tutorials/50-spec-fidelity/start.py 01 ~/fidelity/ops-1432

# judge it -- any time, any stage
python tutorials/50-spec-fidelity/spec_fidelity.py ~/fidelity/ops-1432
python tutorials/50-spec-fidelity/spec_fidelity.py ~/fidelity/ops-1432 --stage prd

# judge the reference answer (lesson 4)
python tutorials/50-spec-fidelity/spec_fidelity.py tutorials/50-spec-fidelity/exercises/01-docker-rest/solution
```

`python tutorials/check.py 50-spec-fidelity` grades the in-repo exercise
folders, the same way as the other tracks. It fails until you put `prd.md`,
`openspec/` and `impl/` there. Copy them back from your workspace if you
want the tick.

## The honest caveat, up front

The deterministic judge checks *shape and tracing*, not meaning. A PRD can
pass `--stage prd` and still describe the wrong product; a test can name a
scenario and assert something weaker than its THEN clause. It catches the
cheap failures — the dropped requirement, the invented feature, the untested
scenario, the `temperature=` that will 400 in production — so that the
expensive reviewer (the `harness-enforcer`, or a human) spends its attention
on meaning. A green deterministic report is a floor, not a verdict.

## Tested with Haiku

Every exercise was run end to end with **Claude Haiku 4.5 as the
developer**, driven only through the `/fidelity:*` commands, and a second
Haiku as the product owner, answering only what was asked from
`stakeholder-answers.md`. Every tool call was logged and audited: no run
read the stakeholder answers, a rubric, or a `solution/` folder.

| exercise | result | cost | what it taught the track |
|---|---|---|---|
| 01 Docker REST | green | $1.94 | 17 questions; when the judge said a fact was not pinned down, Haiku stopped and asked instead of guessing. The image built and ran as non-root — but answered `HEAD` with 501. The PO had said HEAD is a 405; nobody asked. The rubric now requires it. |
| 02 LangChain chatbot | green | $1.69 | Refusal rules (Luhn, "my password is not working") came through the interview intact. The "is this LangChain?" rule passed on an unused import; it now requires `ChatAnthropic` to be called. |
| 03 MCP server, attempt 1 | blocked | $1.56 | Haiku asked exactly the right question and refused to invent the answer. The trial harness never routed it to the PO — a harness bug, fixed. |
| 03 attempt 2 | green, **broken** | $1.83 | Passed the judge and its own review; no MCP client could use it (replies had no `id`). Its tests shared its misunderstanding. The judge now talks to the server over stdio. |
| 03 attempt 3 | green, **broken** | $1.33 | Echoed ids; Claude Code still refused it (no `capabilities` in `initialize`). The stdio check now validates result shapes, not just ids. |
| 03 attempt 4 | green, connects, **unfaithful** | $1.76 | Worked in Claude Code and with the SDK client — and accepted `limit: 99`. Its spec said "1–50" in prose and had no scenario for the boundary, so nothing tested it. The judge now sends calls the product owner said must fail, each after a control call proving the tool works. |

Two lessons that generalise beyond this track:

- **Tests written by the same model that wrote the code share its
  misunderstandings.** Exercise 3 passed its own suite twice while
  unusable. What caught it was an external check — a real client, or a
  script that behaves like one. That is the promotion ladder in
  `HARNESS.md` doing its job: "Connects in Claude Code" started as
  `unverified` and became deterministic because a trial showed it had to.
- **Prose is not a test.** A requirement that states a range, a limit or
  an exact command without a scenario for its boundary is a requirement
  nothing checks. Attempt 4's spec said "1–50"; its code accepted 99.
- **A weaker model follows "stop and ask" well when the prompt says so
  explicitly** and the judge's finding names what is missing. Haiku never
  once invented a product-owner answer to make the judge pass.

The full record (interviews, PRDs, specs, code, tool-call logs, judge
reports) is on the `claude/haiku-trial-pb8jhh` branch, under `trials/`.

## Traps

**1. Letting Claude read the stakeholder answers.** Then it is not
interrogating the ticket, it is transcribing a file, and you learn nothing
about which questions you would have forgotten to ask. `start.py` keeps them
out of the workspace for this reason — and keeps out `rubric.json` too,
because its facts are the same answers in regex form. The first version of
this track copied it in, and told Claude to read it; an adversarial review
caught that, and a test now fails if any stakeholder fact is readable in a
fresh workspace.

**2. Resolving a vague word by deleting it.** "Should be fast" does not
become an acceptable PRD by removing the sentence. It becomes one when
someone says what fast *means* — in exercise 1 it turns out to be a startup
behaviour, not a latency number, which you only find out by asking.

**3. Tagging a test with a scenario it does not test.** The judge checks
that a `TestCase` method with that docstring exists, asserts *something*,
runs and passes; it cannot check that it asserts the right thing. That is exactly what the
`Spec captures intent` agent constraint is for.

**4. Fixing the spec to match the code.** When the build diverges, the
cheap move is to edit the spec until it describes what you built. The trace
back to `PRD-<n>` is what makes that visible: a requirement that no longer
serves the PRD shows up as an orphan.

---

Next: [Lesson 1 — Fidelity, and why the ticket is the environment](lesson-01-fidelity.md)
