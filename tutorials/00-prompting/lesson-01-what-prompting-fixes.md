# Lesson 1 — What prompting can and cannot fix

## Three categories

Before writing a word of prompt, work out which problem you have.

### 1. The model cannot do it

No prompt fixes a capability gap. If the model cannot reliably do
sixteen-digit arithmetic, "be careful with arithmetic" does not help; giving
it a calculator does. Prompting is not the tool.

### 2. The model can discover it

The environment already contains the answer — an error message, a flag, a
schema, a failing test. Competent models find these. Instructions here are
pure cost: tokens spent, budget consumed, nothing gained.

Measured, on this repo's benchmark with no skills at all:

| quirk | outcome | what revealed it |
|---|---|---|
| `rec_prefix` | passed, 10 steps | `ERROR: no record 'rec-4821'. Ids are canonical uppercase with a REC- prefix.` |
| `page_two` | passed, 8 steps | `{"page": 1, "results": [...], "more_pages": true}` |

Nobody told it. It read the error, and it read the flag.

### 3. The model cannot possibly know

A house convention. A downstream system's expectations. Something decided in
a meeting three years ago. There is no signal in the environment, so no
amount of capability closes the gap.

| quirk | failed as | why it could not know |
|---|---|---|
| `iso_z` | `2026-03-07T06:30:12` | nothing said the consumer wants a trailing Z |
| `round_even` | `40.49` instead of `40.48` | half-up is the common convention; this system wants half-to-even |
| `idem_key` | `REC-4842-reconcile` | the separator is a colon, and nothing says so |

**This is the category prompting is for.** Everything you write should earn
its place here.

## The diagnostic question

> If I gave this task to a competent new engineer with access to the same
> tools and no other context, would they get it right?

- **Yes** → do not write the instruction.
- **No, because they would have to guess a convention** → write it.
- **No, because it is genuinely hard** → you have a capability problem.

## Why the third category is invisible

You will not find these by reading your prompt. You find them by **running
the thing and looking at what broke** — which is why every lesson here ends
in a measurement, and why the harness you are sitting in exists.

---

Next: [Lesson 2 — the rubric](lesson-02-scoring.md)
