# Implementation Tasks

## 1. Tool Exposure and Discovery

- [x] 1.1 Test scenario: tools/list returns four tools (PRD-1, PRD-10)
- [x] 1.2 Test scenario: unknown tool returns error code -32602 (PRD-1)
- [x] 1.3 Test scenario: unknown MCP method returns error code -32601 (PRD-10)
- [x] 1.4 Test scenario: unparseable JSON returns error code -32700 (PRD-10)

## 2. Tool Parameters and Validation

- [x] 2.1 Test scenario: rg_search with valid pattern and path (PRD-2)
- [x] 2.2 Test scenario: rg_search rejects unknown parameter (PRD-2)
- [x] 2.3 Test scenario: git_log with limit=1 (PRD-2)
- [x] 2.4 Test scenario: git_log with limit=50 (PRD-2)
- [x] 2.5 Test scenario: git_log with default limit (PRD-2)
- [x] 2.6 Test scenario: rg command invocation uses correct syntax (PRD-2)

## 3. Timeout Enforcement

- [x] 3.1 Test scenario: rg_search timeout after 10 seconds (PRD-3)
- [x] 3.2 Test scenario: git_log timeout after 10 seconds (PRD-3)
- [x] 3.3 Test scenario: git_status timeout after 10 seconds (PRD-3)
- [x] 3.4 Test scenario: git_diff_stat timeout after 10 seconds (PRD-3)

## 4. Output Truncation

- [x] 4.1 Test scenario: successful output truncated at 8000 characters (PRD-4)
- [x] 4.2 Test scenario: error messages truncated at 8000 characters (PRD-4)
- [x] 4.3 Test scenario: truncation includes [truncated] marker (PRD-4)

## 5. Error Handling

- [x] 5.1 Test scenario: invalid rg pattern returns isError: true (PRD-5)
- [x] 5.2 Test scenario: git_status error when not in repository (PRD-5)
- [x] 5.3 Test scenario: rg_search exit code 1 treated as success (PRD-5)
- [x] 5.4 Test scenario: error response includes text explanation (PRD-5)

## 6. Path Validation and Security

- [x] 6.1 Test scenario: rg_search rejects path with ../ (PRD-6)
- [x] 6.2 Test scenario: rg_search rejects absolute path outside root (PRD-6)
- [x] 6.3 Test scenario: no shell invocation for patterns with - (PRD-7)
- [x] 6.4 Test scenario: no shell invocation for patterns with ; (PRD-7)
- [x] 6.5 Test scenario: no shell invocation for patterns with $ (PRD-7)

## 7. Server Configuration and Deployment

- [x] 7.1 Test scenario: server accepts --root flag (PRD-8)
- [x] 7.2 Test scenario: server operates within --root directory (PRD-8)
- [x] 7.3 Test scenario: claude mcp add configuration works (PRD-9)
- [x] 7.4 Test scenario: .mcp.json configuration works (PRD-9)

## 8. MCP Protocol Compliance

- [x] 8.1 Test scenario: server communicates over stdio (PRD-10)
- [x] 8.2 Test scenario: server uses protocol version 2025-06-18 (PRD-10)
- [x] 8.3 Test scenario: server responds to initialize method (PRD-10)
- [x] 8.4 Test scenario: server responds to ping method (PRD-10)
