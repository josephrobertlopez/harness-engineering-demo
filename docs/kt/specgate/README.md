# specgate: knowledge transfer

## The problem

A green test suite proves the tests pass. It does not prove they test what the product owner asked for. Requirements live in one document, tests in another, and nothing forces them to stay in step.

specgate closes that gap. Every requirement is an acceptance criterion (AC) with an id such as `AC-3`. A feature cannot merge until each AC is specified, implemented, covered by a test, executed, and shown to catch bugs.

## The flow

```mermaid
flowchart LR
    A["BMAD PRD<br/>prd.md: AC-1..AC-n"] --> B["OpenSpec spec<br/>one Requirement per AC"]
    B --> C["Tests<br/># covers: AC-k"]
    C --> D["Gates L0 to L6"]
    D --> E["CI<br/>spec-gate.yml, kt-docs.yml"]
    S["Source<br/># implements: AC-k"] --> D
```

| Gate | Question it answers | Deterministic |
|---|---|---|
| L0 schema | Is the PRD well formed against `schema/prd.schema.json`? | yes |
| L1 static | Does the code pass lint, types, dead-code and banned-token checks? | yes |
| L2 trace | Does every AC have an `implements` and a `covers` marker, with real asserts? | yes |
| L3 run | Do all the covering tests pass? | yes |
| L4 coverage | Do the AC's tests actually execute the AC's code? | yes |
| L5 mutation | If the AC's code is broken on purpose, does a test fail? | yes, fixed seed |
| L6 debate | Do adversarial judges find a real flaw in the spec? | no, but a veto only counts if a deterministic recheck confirms it |

Gates run in order and stop at the first red one. The exit code is `10 + layer number`, so exit 13 means L3 failed.

The marker convention is the glue:

```python
# implements: AC-1
def validate_email(email): ...

# covers: AC-1
def test_validate_email_rejects_garbage(): ...
```

## How to add a feature

The change directory is `openspec/changes/<feature>/`. Use `openspec/changes/specgate/` as a worked example.

1. Write `prd.md` with frontmatter listing `feature` and `acs`. Each AC has `id`, `given`, `when`, `then`, and `tests` (at least one).
2. Write `proposal.md`, `tasks.md`, and `specs/<feature>/spec.md`, with one `### Requirement:` and at least one `#### Scenario:` per AC.
3. Write the tests first. Mark each with `# covers: AC-k`.
4. Write the code. Mark it with `# implements: AC-k`.
5. Add or change a file under `docs/kt/<feature>/`. The `kt-docs` check fails the PR unless the diff has an added or changed (not deleted) file under `docs/kt/`.
6. Run the gates locally (next section) until they are green.

## Running it locally

Install once:

```bash
uv venv --python 3.12 && uv pip install -e "plugins/specgate[dev]"
```

Check a change:

```bash
.venv/bin/specgate check --change openspec/changes/specgate --layers L0-L5
npx -y @fission-ai/openspec@1.14.0 validate specgate --strict
```

Run the unit tests of the plugin itself:

```bash
cd plugins/specgate && ../../.venv/bin/python -m unittest discover -s tests -t .
```

L6 (debate) is not enforced in CI. The `specgate` CLI does not run it (`--layers L6` exits 2 with "L6 is not run by the CLI; use run_debate()") and no debate cache is committed, so CI replays nothing. The debate code lives in `plugins/specgate/src/specgate/` and is exercised by the plugin's unit tests. CI shows "L6 debate: run locally, see docs/kt/specgate; not enforced in CI yet".

Calibration, run locally (`.specgate/evidence/T16/calibration.json`, not committed to CI): the panel caught 5/5 bad fixtures and the L6 panel blocked 0/4 good ones. Caveat: the same file records `good_wrongly_blocked: 4`, because an earlier layer (L1, rule SG101) flagged all four good fixtures. So only the L6 result is 0/4; the end-to-end result in that artifact is not.

lefthook (`lefthook.yml`) runs `.venv/bin/specgate`, so create the `.venv` first.

To run the same workflows CI runs, use `act`. See [tutorials/act/README.md](../../../tutorials/act/README.md) for the setup and the exact commands.

## Where things live

| Path | What |
|---|---|
| `plugins/specgate/src/specgate/` | one module per gate, plus `cli.py` and `trace.py` |
| `plugins/specgate/schema/prd.schema.json` | the PRD frontmatter schema |
| `openspec/changes/<feature>/` | PRD, proposal, spec, tasks |
| `.github/workflows/spec-gate.yml` | CI for L0 to L5 (L6 is a labelled no-op) |
| `.github/workflows/kt-docs.yml` | CI rule: every PR adds or changes a file under `docs/kt/` |
