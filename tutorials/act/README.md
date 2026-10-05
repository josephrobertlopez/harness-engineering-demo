# Running GitHub Actions Locally with act

**~20 minutes. Requires Docker and act installed.**

## What act is

act runs GitHub Actions workflows in Docker containers that imitate GitHub's Ubuntu and Windows runners. It catches failures before pushing, saves CI minutes, and lets you debug jobs locally.

## Installing act

On Linux or macOS with Homebrew:

```bash
brew install act
```

For other platforms, see [https://github.com/nektos/act#installation](https://github.com/nektos/act#installation).

Verify the install:

```bash
act --version
```

## Runner image mapping

By default, act uses generic container images that may not match GitHub's runner images exactly. For this repo, use the catthehacker images, which more closely resemble ubuntu-latest:

```bash
act push -W .github/workflows/ci.yml --matrix os:ubuntu-latest --matrix python:3.12 -P ubuntu-latest=catthehacker/ubuntu:act-latest
```

The `-P ubuntu-latest=catthehacker/ubuntu:act-latest` flag tells act to use that specific image for ubuntu-latest matrix jobs. The first image pull is slow; subsequent runs are faster.

## Running the test workflow

This repo's test suite runs offline with no API key required. Run the entire test matrix on ubuntu-latest:

```bash
act push -W .github/workflows/ci.yml --matrix os:ubuntu-latest --matrix python:3.12 -P ubuntu-latest=catthehacker/ubuntu:act-latest
```

**Expected output** (final lines):

```
Ran N tests in ...s

OK
```

Then you'll see:

```
✅  Success - Complete job
🏁  Job succeeded
```

Windows-latest cannot run in act locally (Windows containers require a Windows host), so this command filters to ubuntu-latest.

## Running the PR gate workflows

This repo ships two PR gates: `spec-gate.yml` (OpenSpec compliance) and `kt-docs.yml` (Knowledge Transfer doc required).

### spec-gate

Runs on every PR and checks every `openspec/changes/*/prd.md` with `specgate check --change openspec/changes/<name> --layers L0-L5`. Layers L1-L5 look for `# implements:` / `# covers:` markers in the change dir and fall back to the repo root, which is where `plugins/specgate` lives. CI installs specgate itself. Locally, lefthook expects `.venv/bin/specgate`, so create the `.venv` first (`uv venv --python 3.12 && uv pip install -e "plugins/specgate[dev]"`).

```bash
act pull_request -W .github/workflows/spec-gate.yml -P ubuntu-latest=catthehacker/ubuntu:act-latest
```

spec-gate does not read the PR's changed files, so it needs no event fixture. It enforces:
- **L0–L5**: Deterministic checks (PRD schema, static analysis, trace markers, tests, coverage, mutation), plus `trace.json` being byte-identical after regeneration.
- **L6**: Not enforced. The workflow step is a labelled no-op ("L6 debate: run locally, see docs/kt/specgate; not enforced in CI yet"). The CLI does not run L6 and no debate cache is committed.

Local calibration of the L6 panel (`.specgate/evidence/T16/calibration.json`): it caught 5/5 bad fixtures and the L6 panel blocked 0/4 good ones. The same file also records `good_wrongly_blocked: 4`, because an earlier layer (L1, SG101) flagged all four good fixtures.

### kt-docs

Requires every PR to add or change (not delete) a file under `docs/kt/`. Nothing else counts, so a `docs/*.md` edit alone fails. The workflow uses `git diff --name-only --diff-filter=AM` and `grep -Eq '^docs/kt/'`.

```bash
act pull_request -W .github/workflows/kt-docs.yml -e .github/act-events/pr-docs-kt.json -P ubuntu-latest=catthehacker/ubuntu:act-latest
```

The `-e .github/act-events/pr-docs-kt.json` fixture simulates a PR that changed a KT doc. **Expected: exit 0.**

Negative control: the code-only fixture must fail.

```bash
act pull_request -W .github/workflows/kt-docs.yml -e .github/act-events/pr-code-only.json -P ubuntu-latest=catthehacker/ubuntu:act-latest
```

**Expected: FAIL (non-zero exit)** with `kt-docs: FAIL - PR must add or change a file under docs/kt/`. Use this fixture only with kt-docs; it is not a spec-gate input.

## Secrets

No workflow needs a secret today: L6 is a no-op in CI, so `CLAUDE_CODE_OAUTH_TOKEN` is not read. `.secrets` is gitignored in case you add an L6 step later; pass it with `act --secret-file .secrets`.

## Troubleshooting

### Container leftovers

Act leaves behind containers on failure. Clean them up carefully — only the act-named containers, never your other Docker resources:

```bash
docker ps -aq --filter name=act- | xargs -r docker rm -f
```

**Do NOT run a blanket `docker rm -f $(docker ps -aq)`** — this can kill other local clusters like k3d or Kubernetes deployments.

### First image pull is slow

The catthehacker image is ~2 GB. The first pull takes 2–5 minutes. Subsequent runs use the cached image.

### act cannot parse some fromJson matrix expressions

act's GitHub Actions parser has limits. If you hit `fromJson()` errors in a matrix definition, this is a known act limitation, not your setup. Upstream GitHub Actions handles these; act cannot. Work around by running the job with explicit matrix values via `--matrix` flags, as shown above.

## Next steps

Read [the main repo README](../../README.md) to understand the harness architecture and why workflows are structured this way.
