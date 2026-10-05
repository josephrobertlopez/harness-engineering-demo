#!/bin/bash
set -euo pipefail

# PreToolUse hook: before a Bash `git commit`, run specgate L0-L2 on staged files.
# Exit 0 = allow, exit 2 = block (stderr is shown to the model).

# jq is needed to parse the payload. Without it we cannot tell whether this is a
# commit, so allow rather than block every Bash call.
if ! command -v jq >/dev/null 2>&1; then
  echo "specgate hook: warning: 'jq' not found on PATH; cannot tell whether this is a commit, allowing" >&2
  exit 0
fi

input=$(cat)
tool_name=$(jq -r '.tool_name // empty' <<<"$input")
command=$(jq -r '.tool_input.command // empty' <<<"$input")

[[ "$tool_name" == "Bash" ]] || exit 0

# Drop quoted strings so `echo "git commit"` is ignored, then match `git commit`
# and `git -C dir commit` (any git options) at the start of a command.
unquoted=$(sed -E "s/\"[^\"]*\"//g; s/'[^']*'//g" <<<"$command")
pattern='(^|[;&|(])[[:space:]]*git([[:space:]]+-[Cc][[:space:]]+[^[:space:]]+|[[:space:]]+-[^[:space:]]+)*[[:space:]]+commit([[:space:]]|$)'
if ! grep -Eq "$pattern" <<<"$unquoted"; then
  exit 0
fi

# It is a commit: the gate itself must be available.
if ! command -v specgate >/dev/null 2>&1; then
  echo "specgate hook: required tool 'specgate' not found on PATH; cannot check commit" >&2
  exit 2
fi

rc=0
output=$(
  unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE
  specgate check --layers L0-L2 --staged 2>&1
) || rc=$?

if [[ $rc -ne 0 ]]; then
  echo "specgate hook: commit blocked, 'specgate check --layers L0-L2 --staged' exited $rc" >&2
  echo "$output" >&2
  exit 2
fi

exit 0
