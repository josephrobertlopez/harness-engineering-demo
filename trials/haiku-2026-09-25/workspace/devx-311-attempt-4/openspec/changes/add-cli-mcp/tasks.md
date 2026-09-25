# Tasks: CLI tools MCP server

## 1. Expose CLI tools

- [x] 1.1 Test: Tools list returns exactly four tools
- [x] 1.2 Test: git_status executes
- [x] 1.3 Test: git_log executes with limit parameter
- [x] 1.4 Test: git_diff_stat executes
- [x] 1.5 Test: rg_search executes with pattern
- [x] 1.6 Test: Unknown tool returns error -32602

## 2. MCP protocol integration

- [x] 2.1 Test: MCP activation via claude mcp add command
- [x] 2.2 Test: MCP activation via .mcp.json file
- [x] 2.3 Test: tools/list method returns schemas

## 3. Security: prevent shell injection

- [x] 3.1 Test: Pattern starting with dash is searched as literal
- [x] 3.2 Test: Path with shell metacharacters is literal
- [x] 3.3 Test: Write operations are not exposed

## 4. Resource limits

- [x] 4.1 Test: Command timeout after 10 seconds
- [x] 4.2 Test: Output truncated when exceeding 8000 characters
- [x] 4.3 Test: Output exactly 8000 characters returns without marker

## 5. Tool parameters and defaults

- [x] 5.1 Test: git_log without limit uses default 10
- [x] 5.2 Test: git_log with limit 1 returns 1 entry
- [x] 5.3 Test: git_log with limit 50 returns 50 entries
- [x] 5.4 Test: rg_search without path uses default current directory
- [x] 5.5 Test: rg_search with path searches that directory

## 6. Root directory and path boundaries

- [x] 6.1 Test: Commands run in specified root directory
- [x] 6.2 Test: Relative path outside root is rejected
- [x] 6.3 Test: Absolute path outside root is rejected

## 7. Ripgrep invocation

- [x] 7.1 Test: Pattern passed with -e flag
- [x] 7.2 Test: Dash separator before path prevents option interpretation
- [x] 7.3 Test: Pattern starting with dash is searched as literal

## 8. Error handling

- [x] 8.1 Test: Tool failure returns isError flag
- [x] 8.2 Test: rg exit code 1 no matches is success
- [x] 8.3 Test: Unknown tool name returns JSON-RPC error -32602
- [x] 8.4 Test: Unknown method returns JSON-RPC error -32601
- [x] 8.5 Test: Unparseable JSON returns JSON-RPC error -32700
