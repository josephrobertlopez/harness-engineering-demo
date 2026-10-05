---
name: specgate
description: Multi-layer acceptance testing framework that validates specifications through 7 layers (L0-L6), from schema to adversarial debate. The CLI runs L0-L5; L6 is the library function `run_debate()`. Works with OpenSpec specs and BMAD product requirements.
allowed-tools: Bash(specgate:*)
license: MIT
compatibility: Requires specgate CLI
metadata:
  author: harness-engineering
  version: "0.1.0"
  generatedBy: "specgate-0.1.0"
---

# specgate: Multi-Layer Acceptance Testing

Specgate is a 7-layer (L0-L6) acceptance testing framework (the CLI runs L0-L5; L6 is the library function `run_debate()`) that validates specifications from schema integrity through adversarial scrutiny.

## When to Use Each Layer

### L0: Schema Validation
**Use when:** Starting a new spec, modifying AC structure, or validating against the PRD schema.

Verifies that your spec conforms to the JSON schema defined in `schema/prd.schema.json`. This is the foundation—if schema fails, nothing else can run.

### L1: Static Analysis
**Use when:** Before trusting any code or docs that carry AC markers.

Runs static checks over the Python and Markdown files in the change:
- `ruff` lint findings
- `mypy` type errors
- `vulture` dead code
- banned tokens
- `markdownlint` on the PRD (and KT docs)

### L2: Trace Generation
**Use when:** Mapping requirements to implementation, understanding marker gaps.

Scans `# implements: AC-k` and `# covers: AC-k` markers with the AST and reports SG201-SG205: a covered AC with no implementation, an implemented AC with no covering test, a marker naming an unknown AC, a covering test with no assert, an implementing function with an empty body. When the layers pass, the CLI writes `trace.json` mapping each AC to its markers.

### L3: Execution Tests
**Use when:** Validating that the implementation runs and fulfills the ACs.

Runs all tests tagged with `# covers: AC-k` and checks that they pass. Proves the implementation actually works.

### L4: Coverage Analysis
**Use when:** Assessing how thoroughly ACs are tested.

Measures how much of the code implementing each AC is actually exercised by its tests. Identifies code paths that are untested.

### L5: Mutation Testing
**Use when:** Verifying that tests would catch real bugs.

Mutates the implementation (introduces small bugs) and checks that the tests fail. Proves your tests aren't just passing accidentally—they actually guard against breakage.

### L6: Debate
**Use when:** Before shipping, engaging adversarial review of the specification itself.

The highest layer, available only as the library function `run_debate()`. A prover, a refuter and three judges question whether the ACs truly capture intent:
- Are assumptions grounded?
- Are edge cases covered?
- Would this catch real bugs?
- Is the language precise?

**Status:** L6 is calibrated locally and is NOT run by the CLI or CI. `--layers L6` exits 2 with "L6 is not run by the CLI; use run_debate()"; a range that extends to L6 warns on stderr and runs L0-L5. See `docs/kt/specgate/README.md`.

## Marker Convention: Linking Code to Spec

Specgate requires explicit markers in your code and tests to build the trace.

### In Source Code: `# implements: AC-k`

Any code that implements acceptance criterion k should be marked:

```python
# implements: AC-1
def validate_user_email(email: str) -> bool:
    """Validates email format per AC-1 requirements."""
    return "@" in email and "." in email
```

Use once per logical implementation. Multiple implementations of the same AC are allowed (e.g., validation in API layer and database layer).

### In Tests: `# covers: AC-k`

Any test that validates acceptance criterion k should be marked:

```python
# covers: AC-1
def test_email_validation_accepts_valid_format():
    assert validate_user_email("user@example.com") is True
```

Use once per test. One test can cover multiple ACs:

```python
# covers: AC-1, AC-2
def test_email_validation_rejects_invalid_format():
    assert validate_user_email("invalid") is False
    assert validate_user_email("user@") is False
```

## BMAD PRD to OpenSpec Spec Mapping

A BMAD PRD defines **acceptance criteria (ACs)**. Each AC becomes an **AC in the OpenSpec spec**, creating a direct mapping:

```
BMAD PRD
├─ User Story
│  └─ AC-1: "User can sign up with email"
│  └─ AC-2: "Email must be valid format"
│  └─ AC-3: "Duplicate emails are rejected"
│
↓ maps to ↓

OpenSpec Spec
├─ Feature
│  └─ AC-1
│  │  ├─ description: "User can sign up with email"
│  │  ├─ examples: [...]
│  │  └─ implementation: (code marked "# implements: AC-1")
│  │     └─ tests: (marked "# covers: AC-1")
│  ├─ AC-2
│  │  └─ ...
│  └─ AC-3
│     └─ ...
```

### The Mapping in Practice

1. **PM writes PRD** (BMAD): "User can sign up with email, and email must be valid format"
   - This becomes ACs: AC-1, AC-2, etc.

2. **Architect/Dev writes spec** (OpenSpec): Expands each AC into detailed requirements
   - AC-1: "email must be valid format"
   - AC-2: "duplicate emails rejected"
   - AC-3: "signup flow completes in <2s"

3. **Dev implements**: Code marked with `# implements: AC-k`
   - Each AC has code implementing it

4. **QA writes tests**: Tests marked with `# covers: AC-k`
   - Each AC has tests validating it

5. **specgate check** (trace.json): Connects all three
   - Shows which code implements which AC
   - Shows which tests cover which AC
   - Identifies gaps (ACs with no impl, impl with no tests)

## Running the Layers

### Run the deterministic layers on a change:
```bash
specgate check --change openspec/changes/<feature> --layers L0-L5
```

### Run specific layers:
```bash
specgate check --layers L0-L2
specgate check --layers L3
specgate check --layers L4-L5
```

### Run only staged changes:
```bash
specgate check --layers L0-L2 --staged
```

### Write the trace somewhere specific:
```bash
specgate check --change openspec/changes/<feature> --layers L0-L5 --output /tmp/trace.json
```

`check` is the only subcommand (`--change`, `--layers`, `--staged`, `--output`). There is no `specgate trace` or `specgate debate`.

## Exit Codes

- `0`: All requested layers passed
- `10`: L0 failed (schema validation)
- `11`: L1 failed (static analysis)
- `12`: L2 failed (trace generation)
- `13`: L3 failed (execution tests)
- `14`: L4 failed (coverage analysis)
- `15`: L5 failed (mutation testing)
- `2`: bad arguments

L6 (debate) is not run by the CLI: `--layers L6` exits 2, and a range such as `L0-L6` warns on stderr and runs L0-L5.

## Key Concepts

### Acceptance Criteria (AC)
A single, testable requirement of the spec. Example:
- "Email must be valid format (RFC 5322)"
- "Signup completes in under 2 seconds"
- "User receives confirmation email within 60 seconds"

### Trace
A JSON artifact mapping ACs to implementation and tests:
```json
{
  "AC-1": {
    "id": "AC-1",
    "implements": [
      {"file": "src/auth.py", "function": "validate_user_email", "line": 45}
    ],
    "covers": [
      {"file": "tests/test_auth.py", "function": "test_email_validation_accepts_valid_format", "line": 10}
    ]
  }
}
```

It is keyed by AC id. An empty `implements` or `covers` list is a gap.

### Coverage Gap
An AC with no tests, or tests with no implementation. Specgate flags both.

### Mutation
A small, deliberate bug injected into the code (e.g., changing `>` to `<`). If tests don't fail on the mutation, the tests aren't actually validating that code.

## Integration with Your Workflow

Specgate integrates with OpenSpec and BMAD:
- **OpenSpec** handles spec storage, versioning, and diff
- **BMAD** (BMad Method) handles PRD → spec conversion and product thinking
- **specgate** validates that the spec→implementation→test chain is complete and sound

Use `/opsx:explore` to think through spec changes, `/opsx:propose` to create a change, and `/specgate:check` to validate it through the gates before shipping.
