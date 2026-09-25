# Harness — SUP-88 help centre chatbot

<!-- Read by the ai-literacy-superpowers harness-enforcer agent
     (/harness-audit, or "use the harness-enforcer to verify the pr-scoped
     constraints in <this file>"). Deterministic constraints run the Tool
     line; agent constraints are judged by the enforcer reading the Rule.

     Tool paths are relative to the repository root. Replace EXERCISE with
     `tutorials/50-spec-fidelity/exercises/02-langchain-chatbot` to judge
     your own work, or append `/solution` to judge the reference answer. -->

## Context

### Stack

- **Primary languages**: Python 3.12
- **Frameworks**: `langchain-core`, `langchain-anthropic` (`ChatAnthropic`)
- **Test framework**: `unittest`, run from `impl/`; chain tests use
  `FakeListChatModel` and skip when LangChain is not installed
- **Container strategy**: none

### Conventions

- **Spec first**: `prd.md` → `openspec/changes/<id>/` → `impl/`.
- **Traceability**: every spec requirement carries `Trace: PRD-<n>`; every
  test names its scenario with `Scenario: <exact scenario name>`.
- **Policy is stdlib**: every rule the PRD states lives in `policy.py`,
  which imports nothing from LangChain; `chatbot.py` only wires it.
- **Model ids are complete as written** — never a date suffix.

---

## Constraints

### PRD is OpenSpec-ready

- **Rule**: Every requirement in `prd.md` has a `PRD-<n>` ID, a SHALL or
  MUST, a WHEN/THEN acceptance, none of the ticket's vague words, and every
  fact from `stakeholder-answers.md` is pinned down.
- **Enforcement**: deterministic
- **Tool**: `python tutorials/50-spec-fidelity/spec_fidelity.py EXERCISE --stage prd`
- **Scope**: commit

### OpenSpec change is valid and traced

- **Rule**: One active change; valid proposal; every requirement in a delta
  section with SHALL/MUST and a WHEN/THEN scenario; PRD ↔ spec tracing
  complete in both directions.
- **Enforcement**: deterministic
- **Tool**: `python tutorials/50-spec-fidelity/spec_fidelity.py EXERCISE --stage spec`
  (and `openspec validate --strict` if the OpenSpec CLI is installed)
- **Scope**: pr

### Every scenario is tested, and tests pass

- **Rule**: Scenario ↔ test tagging complete in both directions; every task
  ticked; tests pass; `chatbot.py` imports `langchain_core`; the model id
  is exactly `claude-sonnet-5`; no `temperature=` anywhere; no API key in
  source. The judge prints how many tests were skipped — run once with
  LangChain installed before you call it done.
- **Enforcement**: deterministic
- **Tool**: `python tutorials/50-spec-fidelity/spec_fidelity.py EXERCISE --stage build`
- **Scope**: pr

### Spec captures intent

- **Rule**: The change states the **problem** (tier-1 deflection), the
  **approach** (design.md) and the **outcome** (scenarios), and `impl/`
  delivers it. In particular: the sensitive-data check runs *before* the
  chain is invoked, not as a prompt instruction; a refused message never
  reaches the history object; an unmatched question never invokes the
  model. A test that names a scenario but asserts less than its THEN
  clause is divergence.
- **Enforcement**: agent
- **Tool**: harness-enforcer
- **Scope**: pr

### Grounding is structural, not hopeful

- **Rule**: The prompt sent to the model contains exactly one FAQ entry —
  the retrieved one — and the system prompt forbids answering beyond it.
  No code path sends the whole FAQ, or no entry, to the model.
- **Enforcement**: agent
- **Tool**: harness-enforcer
- **Scope**: pr

### No gold-plating

- **Rule**: `impl/` adds no web UI, streaming, persistence, embeddings,
  vector store, or other feature the PRD lists as a non-goal, and no
  dependency beyond `langchain-core` and `langchain-anthropic`.
- **Enforcement**: agent
- **Tool**: harness-enforcer
- **Scope**: pr

### Answers are actually grounded

- **Rule**: Against the real model, each of the five FAQ questions gets an
  answer consistent with its entry, and none invents a time limit or price.
- **Enforcement**: unverified
- **Tool**: none yet — needs `ANTHROPIC_API_KEY` and costs money. Run
  `python chatbot.py` by hand; promote with `/harness-constrain` when you
  have an eval set.
- **Scope**: manual
