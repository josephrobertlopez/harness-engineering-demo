# Lesson 3 — The seven anti-patterns

The rubric tells you an output is bad and roughly how. These tell you **why the
model produced it**, which is what you need to stop it recurring.

The framework's central claim: nearly every one of these is a
**constant/variable confusion** — a value treated as fixed when the domain
requires it to be parameterised.

## The seven

### AP1 — Constant/Variable Confusion
`const BASE_REVENUE = 16800` works for the client in the conversation and
produces a nonsense delta for the next one. **Why:** trained on codebases
where most values genuinely are constants. **Hits:** T.

### AP2 — Import Pollution
`import { SIGNALS } from './data/signals'` always loads one client's data;
it should be `getClientSignals(activeClientId)`. **Why:** a static import is
the shortest path to working code. **Hits:** Π.

### AP3 — Hardcoded Vocabulary Leakage
The name of one specific customer, `Northwind`, hardcoded inside a
component described as generic. **Why:** it
writes what it sees in the conversation. **Hits:** T.

### AP4 — Developer-Facing Text in User-Facing UI
A tooltip reading `Provider: AlphaSense. Swap via setActiveProvider().`
**Why:** no distinction between audiences. **Hits:** T and M.

### AP5 — Non-Functional UI Elements
`cursor: 'pointer'` on a span with no `onClick`. **Why:** it generates what
the thing *looks like*, not what it *does*. **Hits:** H.

### AP6 — Stale Cache / Module-Level State
A module-level `let currentConfig` memoised with no variant key. **Why:**
memoisation applied without a runtime-varying cache key. **Hits:** Π.

### AP7 — Overclaiming / Inflated Metrics
The focal company rated 5/5 on every dimension. **Why:** positive bias and
no adversarial self-critique instinct. **Hits:** T.

## Greppable detection

You do not need to read carefully for most of these:

```bash
grep -rn "cursor: 'pointer'" src/ | grep -v onClick   # AP5 candidates
grep -rn "^\s*let " src/ --include=*.ts               # AP6 candidates (module scope)
```

And two questions that catch the rest:

- **AP1/AP2:** *"What if this input were different? Would the output change
  correctly?"*
- **AP7:** *"Is any entity rated maximum on every dimension?"* If so, be
  suspicious — real things have weaknesses.

## Why this belongs in a prompting track

Each anti-pattern has a *prompt-side* counter, and naming it is how you write
one that works:

| | Instead of | Write |
|---|---|---|
| AP1 | "write clean code" | "every client-varying value must be a parameter, not a constant" |
| AP3 | "make it generic" | "no customer name may appear outside `config/`" |
| AP7 | "be objective" | "every entity must have at least one dimension scored below 4, with a reason" |

Generic quality adjectives do nothing. A named prohibition with a scope does.
That is also the difference between the skills that worked and the skills
that did not in [Track 30](../30-skill-authoring/README.md).

---

Next: [Lesson 4 — Specificity, measured](lesson-04-specificity.md)
