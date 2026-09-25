# CLI Tools MCP Server

MCP server for git and ripgrep access from Claude Code.

## Installation

```bash
python impl/mcp_server.py --root /path/to/repository
```

## Usage

### Registration via CLI

```bash
claude mcp add cli-tools -- python /absolute/path/to/impl/mcp_server.py --root /path/to/repo
```

### Registration via .mcp.json

Create a `.mcp.json` file in your project:

```json
{
  "name": "cli-tools",
  "command": ["python", "/absolute/path/to/impl/mcp_server.py", "--root", "/path/to/repository"],
  "description": "MCP server for git and ripgrep access"
}
```

## Supported Tools

### git_status
Shows working directory status in porcelain format.

```
Scenario: git_status_no_arguments
- WHEN Claude invokes `git_status` with no arguments
- THEN it runs `git status --porcelain=v1 --branch`
```

### git_log
Shows commit history with configurable limit (1-50, default 10).

```
Scenario: git_log_default_limit
- WHEN Claude invokes `git_log` without arguments
- THEN it runs `git log --oneline -n 10`
```

### git_diff_stat
Shows summary of working directory changes.

```
Scenario: git_diff_stat_no_arguments
- WHEN Claude invokes `git_diff_stat` with no arguments
- THEN it runs `git diff --stat`
```

### rg_search
Searches for patterns in files with ripgrep.

```
Scenario: rg_search_pattern_only
- WHEN Claude invokes `rg_search` with pattern `foo`
- THEN it searches from the root directory
```

## Error Handling

All tool errors return `{isError: true, reason: "<message>"}`.

### Error Cases

- **Missing binary**: Returns error if git or ripgrep not installed
- **Timeout**: Command times out after 10 seconds
- **Path escape**: Paths outside root directory are rejected
- **Invalid arguments**: Bad arguments return descriptive errors

## Security

- **No shell execution**: Commands run as argument arrays only
- **Read-only**: All git operations are read-only
- **Path isolation**: Commands confined to `--root` directory
- **Output limits**: Output truncated at 8000 characters
- **Injection protection**: Patterns protected with `-e` and `--`

## Testing

```bash
cd impl
python -m unittest discover -s tests -t .
```

## Protocol

- **MCP Protocol Version**: `2025-06-18`
- **Transport**: stdio
- **Error Codes**:
  - `-32602`: Unknown tool
  - `-32601`: Unknown method
  - `-32700`: Unparseable JSON
