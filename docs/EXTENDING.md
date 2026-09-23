# Pointing this at your own tasks

The bundled benchmark exists so the repo runs on day one. It is not the
point. This is the seam for replacing it.

## What a benchmark has to supply

Three things, all in `src/wikiskill/bench/starter.py` — copy it and edit.

### 1. Tasks

```python
Task(
    task_id="my-thing-0",
    split="train",          # "train" | "val" | "test"
    family="date-format",   # stratification key -- see below
    prompt="What the agent is asked to do.",
    env_spec={...},         # opaque; your environment consumes it
    expected={...},         # whatever your scorer compares against
)
```

`family` matters more than it looks. The Wiki Maintainer samples traces
stratified by family so one noisy area cannot monopolise the wiki. Group
tasks by *the kind of mistake they provoke*, not by topic.

Splits must be **disjoint by construction**. If a val task can be solved by
memorising a train answer, the gate is measuring memorisation and every
number downstream is meaningless.

### 2. An environment

```python
class MyEnv:
    def __init__(self, task: Task) -> None: ...
    def tool_spec(self) -> str:
        """Human-readable tool list, injected into the agent's prompt."""
    def call(self, name: str, args: dict) -> str:
        """Run one tool call, return the observation as text."""
```

Must be **independently constructible per task** — rollouts run in a thread
pool, so an environment sharing mutable state across tasks will corrupt
traces in ways that look like model failures.

### 3. A scorer

```python
def score(task: Task, answer: dict | None) -> tuple[float, str | None]:
    """Return (score in [0,1], one-line failure summary or None)."""
```

**Keep it pure and deterministic.** The gate compares two numbers; if the
scorer is itself an LLM judge, you have put a coin flip inside your
acceptance criterion. Partial credit is good — it gives the maintainer more
signal than a bare pass/fail.

The `failure_summary` is what the Wiki Maintainer reads to root-cause. Make
it name the specific violated expectation, not "wrong answer".

## Wiring it in

`EvolutionLoop.__init__` currently hardcodes the starter bench:

```python
self.tasks = starter.tasks()
self.evaluator = Evaluator(self.inference, self.ws.raw, starter.StarterEnv, ...)
```

and `InferenceAgent.run` calls `starter.score`. Swap those three references.
If you want it selectable at runtime, add a `--bench module:factory` loader —
the protocol is already clean enough that this is a small change.

## Designing tasks the method can actually help with

This is the part worth thinking about before writing any code.

WikiSkill fits a specific failure shape: **recurring, rule-shaped mistakes
that cannot be inferred from the prompt.** Evidence from the live run on the
bundled benchmark — the model *passed* the two quirks the environment
revealed (an error message told it the id format; a `more_pages` flag told it
to paginate) and *failed* all three silent conventions nothing announced.

So:

- **Good task:** a house convention the agent has no way to guess and the
  environment never states. Timestamp format, rounding mode, key separator.
- **Bad task:** something the agent can discover by reading an error. It will
  just solve it, and you learn nothing.
- **Bad task:** something requiring capability rather than knowledge. A skill
  cannot make a model better at arithmetic; it can only tell it which
  convention to apply.

## The one thing the bundled benchmark gets wrong

It converges in **one iteration** — a single "house rules" skill absorbs all
the quirks at once. That demonstrates *a skill helps*. It does not
demonstrate the paper's actual claim, which is that knowledge **compounds
across iterations**.

To exercise that, you need quirks that **interact**: where skill 2 only pays
off once skill 1 exists, so a partial insight has to survive in the wiki from
iteration 3 to iteration 6. Adding five more independent conventions will not
do it — they will collapse into one skill exactly as these did.

If you build such a benchmark, that is the most valuable contribution
anyone could make to this repo.
