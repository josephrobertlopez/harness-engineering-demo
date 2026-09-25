# Implementation Tasks: CLI MCP Server

## 1. Tool Availability and Setup

- [ ] 1.1 Test: Server exposes exactly four tools at startup
- [ ] 1.2 Test: Server starts with --root directory parameter
- [ ] 1.3 Test: Server listens on stdin for newline-delimited JSON-RPC messages
- [ ] 1.4 Test: Server advertises protocol version 2025-06-18

## 2. Tool-Specific Signatures

- [ ] 2.1 Test: git_log executes `git log --oneline -n <limit>` with limit=5
- [ ] 2.2 Test: git_log uses default limit=10 when not specified
- [ ] 2.3 Test: git_diff_stat executes `git diff --stat` with no parameters allowed
- [ ] 2.4 Test: rg_search executes with pattern and optional path
- [ ] 2.5 Test: rg_search uses default path=. when path not specified

## 3. Tool Invocation and Output

- [ ] 3.1 Test: Invoking an available tool returns output from the corresponding command
- [ ] 3.2 Test: Tool output is returned in result object
- [ ] 3.3 Test: Output under 8000 characters is returned in full
- [ ] 3.4 Test: Output exactly at 8000 characters is returned without [truncated] marker
- [ ] 3.5 Test: Output over 8000 characters is truncated and [truncated] marker appended

## 4. Error Handling and Exit Codes

- [ ] 4.1 Test: ripgrep exit code 1 (no matches) returns normal result without isError
- [ ] 4.2 Test: ripgrep exit code 2 (error) returns result with isError: true
- [ ] 4.3 Test: Tool execution failure returns result with isError: true and reason text
- [ ] 4.4 Test: Tool timeout (10+ seconds) terminates execution
- [ ] 4.5 Test: Unknown tool name returns JSON-RPC error -32602
- [ ] 4.6 Test: Write operation (git_push) returns error -32602

## 5. Security: Shell Injection Prevention

- [ ] 5.1 Test: Shell metacharacters in rg_search pattern are not interpreted as shell syntax
- [ ] 5.2 Test: Path traversal characters (..) in rg_search path are not evaluated by shell
- [ ] 5.3 Test: Command injection attempt via argument (e.g., $(rm -rf /)) is passed literally to ripgrep

## 6. Security: Path Validation

- [ ] 6.1 Test: --root directory constraint is enforced at startup
- [ ] 6.2 Test: rg_search with path outside root is rejected with error "path escapes the root"
- [ ] 6.3 Test: Path like ../../../etc/passwd is validated and rejected if outside root
- [ ] 6.4 Test: Paths with .. are resolved and validated against root

## 7. Protocol: JSON-RPC 2.0

- [ ] 7.1 Test: Valid JSON-RPC request receives JSON-RPC response
- [ ] 7.2 Test: Malformed JSON on stdin returns error -32700 (parse error)
- [ ] 7.3 Test: Unparseable JSON returns error -32700
- [ ] 7.4 Test: JSON-RPC response includes correct id field from request

## 8. Registration Methods

- [ ] 8.1 Test: Server can be registered via `claude mcp add cli-tools -- python /path/server.py --root /repo`
- [ ] 8.2 Test: Server can be registered via `.mcp.json` configuration file with same command
- [ ] 8.3 Test: Both registration methods result in server being available to Claude Code

## 9. Integration and Edge Cases

- [ ] 9.1 Test: Multiple concurrent tool invocations are handled correctly
- [ ] 9.2 Test: Tool invocation after timeout completes successfully (timeout doesn't leave residual state)
- [ ] 9.3 Test: Large output (near 8000 chars) is truncated without corruption
- [ ] 9.4 Test: Empty rg_search results return normal result (not error)
- [ ] 9.5 Test: Tool names are case-sensitive (git_log works, but GIT_LOG returns -32602)
