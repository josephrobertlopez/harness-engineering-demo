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
Ran 159 tests in 22.696s

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

Runs on every PR and checks that PRD ACs map to OpenSpec specs with at least one test each, for layers L0–L6.

```bash
act pull_request -W .github/workflows/spec-gate.yml -e .github/act-events/pr-code-only.json -P ubuntu-latest=catthehacker/ubuntu:act-latest
```

The `-e .github/act-events/pr-code-only.json` fixture simulates a PR that changes code but not docs. This gate enforces:
- **L0–L5**: Deterministic checks (PRD exists, specs trace to PRD, tests trace to specs).
- **L6**: Replay of the committed `debate.cache.json` to verify debate conclusions are stable (requires `CLAUDE_CODE_OAUTH_TOKEN`; most local runs need no token).

### kt-docs

Ensures every PR adds or modifies a Knowledge Transfer doc (anything under `docs/kt/` or a top-level `docs/*.md` file).

```bash
act pull_request -W .github/workflows/kt-docs.yml -e .github/act-events/pr-docs-kt.json -P ubuntu-latest=catthehacker/ubuntu:act-latest
```

The `-e .github/act-events/pr-docs-kt.json` fixture simulates a PR that changed a KT doc.

## Secrets: CLAUDE_CODE_OAUTH_TOKEN

The spec-gate L6 layer replays a committed debate cache, which usually requires no token. If you need to regenerate the cache, create a `.secrets` file (gitignored) with your token:

```bash
echo "CLAUDE_CODE_OAUTH_TOKEN=your_token_here" > .secrets
```

Then pass it to act:

```bash
act pull_request -W .github/workflows/spec-gate.yml -e .github/act-events/pr-code-only.json --secret-file .secrets -P ubuntu-latest=catthehacker/ubuntu:act-latest
```

Most local runs can skip this — the gate replays the committed cache and passes without a token.

## Troubleshooting

### Port or container leftovers

Act leaves behind containers on failure. Clean them up carefully — only the act-named containers, never your other Docker resources:

```bash
docker ps -aq --filter name=act- | xargs -r docker rm -f
```

**Do NOT run a blanket `docker rm -f $(docker ps -aq)`** — this can kill other local clusters like k3d or Kubernetes deployments.

If port 34567 is in use (from a prior act run):

```bash
fuser -k 34567/tcp
```

Then retry your act command.

### First image pull is slow

The catthehacker image is ~2 GB. The first pull takes 2–5 minutes. Subsequent runs use the cached image.

### act cannot parse some fromJson matrix expressions

act's GitHub Actions parser has limits. If you hit `fromJson()` errors in a matrix definition, this is a known act limitation, not your setup. Upstream GitHub Actions handles these; act cannot. Work around by running the job with explicit matrix values via `--matrix` flags, as shown above.

## Next steps

Read [the main repo README](../../README.md) to understand the harness architecture and why workflows are structured this way.
