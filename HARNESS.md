# Harness — harness-engineering-demo

<!-- This file is the source of truth for the project's harness: what
     conventions exist, how each is enforced, and what periodic checks
     fight entropy. Agents, hooks and CI read it to know what to do.

     Generated with the ai-literacy-superpowers plugin's /harness-init and
     then edited by hand; edit freely. CLAUDE.md remains the explanation of
     *why* each invariant exists -- this file says how each one is checked.

     Inspired by Birgitta Boeckeler's "Harness Engineering":
     https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html -->

## Context

### Stack

- **Primary languages**: Python 3.12+ (CI runs 3.12 and 3.13), standard
  library only; Markdown for docs, tutorials and personas
- **Build system**: none needed; `pyproject.toml` (hatchling) declares
  `dependencies = []` and one optional extra, `api = ["anthropic>=1"]`
- **Test framework**: stdlib `unittest`, run with
  `python -m unittest discover -s tests -t .` — offline, no API key, no
  install step
- **Container strategy**: none for the package; tutorial track 50's
  exercise 1 builds a Docker image as learner work

### Conventions

- **Naming**: modules and functions `snake_case`, classes `PascalCase`,
  module-level constants `UPPER_CASE`. Model ids are complete as written —
  never a date suffix (`claude-sonnet-5`, not `claude-sonnet-5-2026…`).
- **File structure**: the package lives in `src/wikiskill/`, one concern
  per module; the three persistent layers in `src/wikiskill/layers/`, the
  three agents in `src/wikiskill/agents/`, model access in
  `src/wikiskill/backends/`. Only `layers/` writes under `workspace/`.
  Tests in `tests/test_*.py`, one area per file. Tutorials in
  `tutorials/<NN>-<track>/`; persona sources in `personas/*.persona.md`,
  with `personas/export/` generated from them.
- **Error handling**: fail loudly and early — a backend reply that is
  prose, an error or a refusal raises rather than being read as an answer;
  a broken tutorial exercise is reported as a failing exercise, never an
  exception that hides the others. Writes are atomic (`util.py` helpers)
  and always pass `encoding="utf-8"` and an explicit `newline`.
- **Documentation**: comments explain *why*, especially where a
  non-obvious choice is load-bearing; never restate what a line does.
  Every lesson learned the hard way goes in CLAUDE.md's "Scar tissue".
  Every directory a reader is expected to open has a README.md.
  Generated docs are verified against the tool they describe.

### Stakeholders

- Learners working through the tutorial tracks
- Engineers evaluating the WikiSkill method
- The maintainer, who reviews and merges changes

---

## Constraints

<!-- Tool commands assume Python 3.12+ is on PATH as `python`, as CI's
     setup-python provides. On a machine where `python` is older, run them
     with `python3.12`.

     The template's plugin-workflow constraints (adjudicated objections,
     choice stories, consultation records) are omitted deliberately: this
     project does not use that workflow, so they would fail every PR by
     construction. A constraint nothing could pass is noise. -->

### Tests must pass

- **Rule**: The full test suite passes with zero failures on Python 3.12
  and 3.13, on Linux and Windows, before any change is merged
- **Enforcement**: deterministic
- **Tool**: `python -m unittest discover -s tests -t .` (CI: `.github/workflows/ci.yml`)
- **Scope**: pr

### Inference never reaches the wiki

- **Rule**: `InferenceAgent.__init__` takes `(backend, model, max_steps)`
  and nothing else, and `agents/inference.py` does not import
  `layers.wiki` (CLAUDE.md invariant 1: the paper's 63.7% → 60.9%
  ablation)
- **Enforcement**: deterministic
- **Tool**: `python -m unittest tests.test_no_wiki_leak`
- **Scope**: commit

### The wiki has no delete path

- **Rule**: `WikiStore`'s public surface is exactly the declared set; its
  only writers are `apply_patch_ops`, `append_log` and
  `append_skill_impact`, and no method can delete, prune or roll back
  (invariant 2)
- **Enforcement**: deterministic
- **Tool**: `python -m unittest tests.test_invariants.TestWikiHasNoDeletePath`
- **Scope**: commit

### Wiki patches are all-or-nothing, anchors match once

- **Rule**: A patch batch is applied to an in-memory copy and written only
  if every op succeeds; an anchor that matches more or fewer than once is
  rejected (invariants 3 and 4)
- **Enforcement**: deterministic
- **Tool**: `python -m unittest tests.test_patching`
- **Scope**: commit

### HEAD moves last; rollback never moves it

- **Rule**: The gate decision is journaled before `set_head`; a rejected
  candidate leaves HEAD untouched; a resumed run matches an uninterrupted
  one (invariant 5)
- **Enforcement**: deterministic
- **Tool**: `python -m unittest tests.test_skills_store tests.test_resume`
- **Scope**: pr

### Trace paths carry the skill-set sha

- **Rule**: The same task under two skill sets in one iteration gets two
  distinct trace and step paths (invariant 7)
- **Enforcement**: deterministic
- **Tool**: `python -m unittest tests.test_invariants.TestTracePathsCarryTheSha`
- **Scope**: commit

### skill-impact.md is written by the harness, never a model

- **Rule**: No model output is written to `skill-impact.md` as a claim
  about its own acceptance; the entry is composed by the loop from the
  gate's decision (invariant 6)
- **Enforcement**: agent
- **Tool**: harness-enforcer
- **Scope**: pr

### Only `layers/` writes the persistent layers

- **Rule**: No module outside `src/wikiskill/layers/` writes under
  `workspace/raw/`, `workspace/wiki/` or `workspace/skills/`. Run state
  under `workspace/.state/` is the one known exception: the journal and
  `proposal.json` are written by `loop.py`, the LLM cache by
  `backends/base.py`. CLAUDE.md states the rule without that exception
- **Enforcement**: agent
- **Tool**: harness-enforcer
- **Scope**: pr

### Model parameters come from one table

- **Rule**: Per-model thinking, effort and sampling rules live in
  `config.MODEL_CAPS` and are applied only in
  `backends/anthropic_api.py`; no date-suffixed model ids; no
  `temperature` for the Opus/Sonnet 5 family
- **Enforcement**: deterministic
- **Tool**: `python -m unittest tests.test_backend_params`
- **Scope**: commit

### Stdlib only, offline by default

- **Rule**: `pyproject.toml` declares no runtime dependencies, and the
  full loop runs on the mock backend with networking disabled
- **Enforcement**: deterministic
- **Tool**: `python -c "import tomllib;d=tomllib.load(open('pyproject.toml','rb'));assert d['project']['dependencies']==[]"` and `python -m unittest tests.test_e2e_mock`
- **Scope**: pr

### Persona exports match their sources

- **Rule**: Every file under `personas/export/` is exactly what
  `personas/export.py` generates from `personas/*.persona.md`
- **Enforcement**: deterministic
- **Tool**: `python personas/export.py --check`
- **Scope**: commit

### Docs do not lie

- **Rule**: Every relative Markdown link resolves; every tutorial
  exercise passes with its reference solution and fails cleanly without
  one; the test counts stated in README.md and START-HERE.md equal the
  suite's
- **Enforcement**: deterministic
- **Tool**: `python -m unittest tests.test_tutorials tests.test_invariants.TestDocumentedTestCounts`
- **Scope**: pr

### Track 50's judge stays honest

- **Rule**: The fidelity judge catches every gaming case the adversarial
  review and the Haiku trial found, raises no false positives on faithful
  work, and no stakeholder fact is readable in a learner's workspace
- **Enforcement**: deterministic
- **Tool**: `python -m unittest tests.test_spec_fidelity`
- **Scope**: pr

### LF line endings

- **Rule**: Every tracked text file is stored with LF endings (skill
  snapshots are content-addressed and diffs are compared byte for byte)
- **Enforcement**: deterministic
- **Tool**: `git ls-files --eol | grep -c "^i/crlf"` must print `0` (pinned by `.gitattributes`)
- **Scope**: commit

### Comments explain why

- **Rule**: New comments explain a non-obvious reason; none restates what
  the adjacent line does
- **Enforcement**: agent
- **Tool**: harness-enforcer
- **Scope**: pr

### No secrets in source

- **Rule**: No API keys, tokens, passwords or private keys in committed
  files
- **Enforcement**: unverified
- **Tool**: none yet — gitleaks is not installed; promote with
  `/harness-constrain` after `go install github.com/gitleaks/gitleaks/v8@latest`
  or `brew install gitleaks`
- **Scope**: commit

### Consistent formatting

- **Rule**: Source files pass the project's formatter without changes
- **Enforcement**: unverified
- **Tool**: none yet — no formatter is configured, by choice so far;
  ruff is the likely candidate if one is adopted
- **Scope**: commit

---

## Garbage Collection

### Documentation freshness

- **What it checks**: Whether README files, docs/ and tutorials reference
  files, functions, flags or conventions that no longer exist
- **Frequency**: weekly
- **Enforcement**: agent
- **Tool**: harness-gc agent
- **Auto-fix**: false

### Upstream facts in tutorials

- **What it checks**: Whether the external facts track 50 states are
  still true — OpenSpec CLI version and `validate` behaviour, MCP Python
  SDK API (`MCPServer`), LangChain doc URLs, ai-literacy-superpowers
  commands and agent names, Claude model ids
- **Frequency**: monthly
- **Enforcement**: agent
- **Tool**: harness-gc agent
- **Auto-fix**: false

### Commit history record

- **What it checks**: Whether `docs/COMMIT-HISTORY.md` lags `git log` by
  more than two commits (one by design, one for the merge commit GitHub
  adds when a PR lands)
- **Frequency**: weekly
- **Enforcement**: deterministic
- **Tool**: `python -c "import re,subprocess;n=int(subprocess.check_output(['git','rev-list','--count','HEAD']));d=open('docs/COMMIT-HISTORY.md',encoding='utf-8').read();m=int(re.search(r'(\d+) commit\(s\)',d).group(1));assert m>=n-2"`; fix with `python scripts/gen_commit_history.py`
- **Auto-fix**: false

### Snapshot staleness

- **What it checks**: Whether the most recent harness health snapshot in
  `observability/snapshots/` is less than 30 days old
- **Frequency**: weekly
- **Enforcement**: deterministic
- **Tool**: file date check
- **Auto-fix**: false

### Observability archive

- **What it checks**: Whether snapshots older than 6 months exist in
  `observability/snapshots/` and should move to `observability/archive/`
- **Frequency**: monthly
- **Enforcement**: deterministic
- **Tool**: file date check
- **Auto-fix**: true (move to archive directory)

### Reflection-driven regression detection

- **What it checks**: Whether CLAUDE.md's "Scar tissue" (this project's
  reflection log) records a recurring failure pattern that no constraint
  above covers
- **Frequency**: monthly
- **Enforcement**: agent
- **Tool**: harness-gc agent
- **Auto-fix**: false

---

## Affordances

<!-- Not yet configured. Run /harness-init and select this feature to set up. -->

---

## Observability

- Snapshot cadence: monthly

### Operating cadence

- Harness audit (/harness-audit): quarterly (90 days)
- AI literacy assessment (/assess): quarterly (90 days)
- Reflection review and promotion: monthly (30 days)
- Cost capture (/cost-capture): quarterly (90 days)

### Health thresholds

- Minimum enforcement ratio for Healthy: 70%
- Consecutive zero-finding GC snapshots before alert: 3
- Unpromoted reflection age before learning flow is stalled: 60 days
- Consecutive declining trend snapshots before alert: 3

### Regression detection

- Cadence non-compliance threshold: 2 or more activities overdue
- Reflection drought threshold: 4 consecutive weeks with zero reflections

---

## Read-side filtering

Readers of `REFLECTION_LOG.md` bound their default intake to keep
per-read cost flat as the log grows. Defaults:

- **Bounded entry count**: 50
- **Bounded day window**: 90 days
- **Default policy**: read the more inclusive of the two

This project keeps its reflections in CLAUDE.md's "Scar tissue" rather
than a separate `REFLECTION_LOG.md`; readers apply the same bounds there.

---

## Status

<!-- Auto-updated by /harness-audit — do not edit manually -->

Last audit: never
Constraints enforced: 15/17
Garbage collection active: 6/6
Drift detected: not yet audited
