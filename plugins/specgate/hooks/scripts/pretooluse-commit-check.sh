#!/bin/bash
set -euo pipefail

# Read stdin and extract tool_name and command from JSON
input=$(cat)
tool_name=$(echo "$input" | jq -r '.tool_name // empty')
command=$(echo "$input" | jq -r '.tool_input.command // empty')

# Only act when tool_name is Bash and command contains "git commit"
if [[ "$tool_name" != "Bash" ]] || [[ ! "$command" =~ git\ commit ]]; then
  exit 0  # Not a git commit, skip check
fi

# Run specgate check on staged files for layers L0-L2
# Unset GIT_* vars to avoid hook context interference
output=$(
  unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE
  specgate check --layers L0-L2 --staged 2>&1
)
rc=$?

if [[ $rc -ne 0 ]]; then
  echo "$output" >&2
  exit 2
fi

exit 0
