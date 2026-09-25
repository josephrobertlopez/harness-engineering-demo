# Exercise 1 — OPS-1432: a Dockerised REST function

**~50 minutes.** You get [`ticket.md`](ticket.md). You hand in `prd.md`,
`openspec/changes/<id>/` and `impl/` — a stdlib Python HTTP function that
converts currency amounts, packaged as a Docker image.

This is the gentlest of the three. Every vague word in the ticket hides a
concrete answer; your job is to ask for it.

| file | what it is | Claude sees it? |
|---|---|---|
| `ticket.md` | the Jira ticket, as filed | yes |
| `stakeholder-answers.md` | what the PO says when asked | **no** — you are the PO |
| `rubric.json` | what the deterministic judge checks | yes |
| `HARNESS.md` | constraints for the `harness-enforcer` | yes |
| `solution/` | the reference answer | **no** — until you are done |

## Work backwards first (15 min)

[Lesson 4](../../lesson-04-work-backwards.md) walks this exercise's solution
end to end — two full threads and six ways to break it. Do that first. The
short version:

```bash
python tutorials/50-spec-fidelity/start.py 01 ~/fidelity/backwards --with-solution
python tutorials/50-spec-fidelity/spec_fidelity.py ~/fidelity/backwards
```

Then answer these from the solution alone, without the lesson:

1. Which requirement has no words at all in the ticket? (There are two.)
2. The ticket says "handle errors properly". How many distinct error
   responses did that become, and which stakeholder answer defined them?
3. Why is `amount` in the response a string, and which test would fail if
   it were a JSON number?

## Then forward (35 min)

```bash
python tutorials/50-spec-fidelity/start.py 01 ~/fidelity/ops-1432
cd ~/fidelity/ops-1432 && claude
```

Follow [lesson 3](../../lesson-03-the-loop.md), judging after each step:

| step | you produce | judge |
|---|---|---|
| 1. interrogate | a list of answered questions | — |
| 2. PRD + review | `prd.md` | `--stage prd` |
| 3. propose | `openspec/changes/<id>/` | `--stage spec` |
| 4. build, test-first | `impl/app.py`, `impl/rates.json`, `impl/Dockerfile`, `impl/tests/` | all stages |
| 5. agent judge | a `harness-enforcer` report | — |

### Hints for this ticket

- **"Should be fast"** has no latency number behind it. Ask what "fast"
  *protects against* and you get a design constraint instead.
- **"Use the usual rates"**: ask where they live, who updates them, and
  whether a request may fetch them.
- **Money**: if you do not ask how results are rounded, you will not find
  out. Finance will.
- **"Secure"** and **"runs anywhere"** both resolve to container facts.
  One of them resolves to a *non-goal* — write that down; a deliberate
  absence is not a gap.

### Run it for real

The judge does not need Docker. You should still see it work once:

```bash
cd impl
docker build -t fx .
docker run --rm -p 8080:8080 fx
curl 'localhost:8080/convert?amount=100&from=GBP&to=EUR'
# {"amount": "100.00", "from": "GBP", "to": "EUR", "rate": "1.164557", "result": "116.46"}
curl -X POST localhost:8080/convert           # 405
docker run --rm fx id                         # uid=10001(fx) ... not root
```

If `docker build` fails with `429 Too Many Requests` pulling
`python:3.12-slim`, Docker Hub is rate-limiting anonymous pulls. `docker
login`, or pull `mirror.gcr.io/library/python:3.12-slim` and tag it
`python:3.12-slim`.

## Traps in this exercise

**Using `float` anywhere.** `0.135` has no exact binary representation, so
a float implementation passes most tests and fails the one finance cares
about. `rubric.json` forbids `float(` in `app.py` for this reason.

**Rounding the rate, then multiplying.** The rate is *shown* to 6 places;
the result is computed from the unrounded rate. On a large invoice the
difference is a cent — enough to fail an audit.

**Testing over a socket.** Keep the request handling a pure function
(`handle(method, target) -> (status, body)`) and the HTTP server a thin
shell around it. Every scenario is then a plain unit test with no port, no
Docker and no flakiness.

**The Dockerfile comment that trips the linter.** An early version of this
exercise's rubric flagged `pip install` *inside a comment*. The rule now
matches only `RUN` lines. If your own rule cries wolf, fix the rule — a
false positive teaches people to ignore the checker.

## Resources

- OpenSpec: [concepts](https://github.com/Fission-AI/OpenSpec/blob/main/docs/concepts.md),
  [getting started](https://github.com/Fission-AI/OpenSpec/blob/main/docs/getting-started.md)
- Python: [`decimal`](https://docs.python.org/3/library/decimal.html) (rounding modes),
  [`http.server`](https://docs.python.org/3/library/http.server.html)
- Docker: [Dockerfile reference](https://docs.docker.com/reference/dockerfile/)
  (`USER`, `EXPOSE`, `HEALTHCHECK`)
- Habitat-Thinking: [habitat engineering](https://habitat-thinking.github.io/ai-literacy-superpowers/plugins/ai-literacy-superpowers/explanation/habitat-engineering/),
  [`HARNESS.md`](https://habitat-thinking.github.io/ai-literacy-superpowers/plugins/ai-literacy-superpowers/explanation/harness-md/)
- In this repo: the [Interrogator](../../../../personas/spec-interrogator.persona.md)
  and [Adversary](../../../../personas/spec-adversary.persona.md) personas

## Checking your work

```bash
python tutorials/50-spec-fidelity/spec_fidelity.py ~/fidelity/ops-1432
python tutorials/check.py 50-spec-fidelity/01     # grades this folder, if you copy your work here
```
