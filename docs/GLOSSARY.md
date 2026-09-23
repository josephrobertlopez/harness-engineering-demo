# Glossary

Terms used in this repo and in the WikiSkill paper. Where a term means
something specific *here* that differs from common usage, that is noted.

## The three layers

**Raw store** — `workspace/raw/`, immutable execution traces. The Inference Agent writes one `.trace.json` per task per rollout, recording what tools were called and what the agent said at each step.

**Wiki** — `workspace/wiki/`, compounding patterns extracted from the raw traces. The Wiki Maintainer samples failures across families, roots out the causes, and applies incremental patches to `.md` pages. The wiki is never rolled back.

**Skills** — `workspace/skills/`, executable procedures injected into the prompt. A skill is a markdown file with frontmatter (`name`, `description`) and a body that the model reads. Skills change with every acceptance; the wiki persists.

## The loop and its participants

**Iteration** — one complete cycle through the seven phases: `rollout_train`, `wiki_update`, `propose`, `apply_candidate`, `eval_val`, `gate_decision`, `commit`.

**Inference Agent** — runs the train split under the current skills and produces raw traces. Takes no wiki handle (structural guarantee). Uses the smallest model by default (`claude-haiku-4-5`).

**Wiki Maintainer** — reads sampled traces, identifies failure patterns, patches the wiki. Uses a mid-size model (`claude-sonnet-5`). Never writes to `skills/` or `.state/`.

**Skill Proposer** — reads the pattern index and the impact ledger, proposes one atomic new skill or change. Uses the largest model (`claude-opus-5`). Never reads the raw traces directly.

**Gate** — validates the candidate skill set against a held-out split and accepts only a strict improvement. Compares candidate against both the incumbent and the stored `R_best`; ties are rejected.

## The decision and its outcome

**R_best** — the best validation score ever achieved. Updated when a skill is accepted; used by the gate as one of two baselines (the other is the incumbent's score).

**Validation score** (val) — a single number in [0, 1] measuring how well a skill set performs on the held-out validation split. Both incumbent and candidate are re-measured in the same batch.

**Gate decision** — accept if `val_candidate > max(val_incumbent, R_best) + gate_margin`; otherwise reject with a reason (no_improvement, below_margin, or budget violation).

**Rollback** — does not exist. The candidate lives in its own content-addressed snapshot; rejection simply never points HEAD at it. No undo path means no undo bug.

## State and addressing

**Skill-set sha** — an eight-character content hash of the skills collection. Traces are bucketed by sha so the incumbent and candidate rollouts of the same task cannot overwrite each other.

**HEAD.json** — a pointer file containing `{"sha": "..."}`. Points at the current accepted skill set. Moves only after a gate acceptance is durable.

**Snapshot** — an immutable skill set stored in `.state/skillsets/<sha>/`. The skill proposer creates a new one every iteration; the gate decides which one HEAD should point at.

## Splitting and scoring

**Train split** — tasks the Inference Agent rolls out with every iteration, used to produce traces for the Wiki Maintainer to learn from.

**Validation split** — held-out tasks used by the gate to accept or reject skill proposals. Shown to the Skill Proposer (in the pattern index) but never to the Inference Agent.

**Test split** — held-out tasks never shown to any agent. Measures true generalization. Run separately from the main loop: `python -m wikiskill.cli eval --split test --skills accepted`.

**Baseline** — the validation or test score with no skills at all. Shows the gap the evolving skills must bridge.

## Persistence and recovery

**Journal** — `workspace/.state/journal.jsonl`, append-only log of completed phases. One JSON line per entry. When the loop restarts, it replays from the first phase that has no journal entry, achieving idempotent resume.

**Resume** — restarting the loop after a crash. The journal is the single source of truth; every phase is idempotent so re-running them produces the same result.

**Last committed** — the highest iteration that reached the `commit` phase (the last one). Resume starts from `last_committed() + 1` to avoid silently skipping work.

## Constraints and tradeoffs

**Budget check** — before evaluation, oversized proposals are rejected if they exceed `skill_budget_bytes` or `skillset_budget_bytes`. Rejection costs zero evaluation tokens and is recorded in the impact ledger.

**Gate margin** — `--gate-margin N` adds a conservative bias: the candidate must exceed the baseline by at least N points, not just 0.00001. Helps when sampling variance is high.

**Temperature** — set to `null` on Opus 5 and Sonnet 5 (they error if set). Haiku 4.5 accepts it. Affects reproducibility on cold (non-cached) runs.

**Skill-budget-bytes** — ceiling on a single skill's size. Prevents dilution of the inference prompt.

**Skillset-budget-bytes** — ceiling on the combined size of all skills. Ensures the prompt does not grow unbounded.

## Implementation details specific to this repo

**Mock backend** — fully deterministic. Answers correctly only if the injected skills cover the task's quirk (detected by matching `[[QUIRK:<family>]]` markers). Used in CI and for offline development.

**Claude-cli backend** — default. Reuses the Claude Code login, no API key. Shells out to `claude -p` (single-shot, no tool schemas). Requires four isolation flags: `--system-prompt` (replace, not append), `--tools ""` (disable all), `--restricted`, `--strict-mcp-config`.

**Anthropic backend** — uses the SDK directly. Takes `ANTHROPIC_API_KEY` or an `ant auth login` profile. Branches on model family because Opus 5 / Sonnet 5 and Haiku 4.5 take incompatible thinking parameters.

**Text protocol** — `THOUGHT: ... ACTION: ... ANSWER: ...` the model outputs; the harness parses it. Identical across all three backends, because the default backend (claude-cli) does not support native tool use.

---

For more on the invariants, read `CLAUDE.md`. For architecture, read `docs/ARCHITECTURE.md`.
