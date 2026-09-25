# Tasks — add-cli-mcp

## 1. Core Server Implementation

- [x] 1.1 Implement MCP server initialization and protocol handshake (protocol version `2025-06-18`)
- [x] 1.2 Implement tool registry and dispatch mechanism
- [x] 1.3 Implement argument validation and error response formatting
- [x] 1.4 Implement timeout enforcement (10-second limit)
- [x] 1.5 Implement output truncation (8000 characters with `[truncated]` marker)

## 2. Tool Implementations

- [x] 2.1 Implement `git_status` tool (runs `git status --porcelain=v1 --branch`)
- [x] 2.2 Implement `git_log` tool (accepts `limit` 1–50, default 10)
- [x] 2.3 Implement `git_diff_stat` tool (runs `git diff --stat`)
- [x] 2.4 Implement `rg_search` tool (pattern + optional path, fixed flags)

## 3. Security Layer

- [x] 3.1 Implement root directory isolation (validate all paths stay within `--root`)
- [x] 3.2 Implement path escape prevention (reject `../` and absolute paths)
- [x] 3.3 Implement read-only enforcement (no write operations)
- [x] 3.4 Implement flag injection protection for ripgrep (use `-e` and `--`)
- [x] 3.5 Implement argument list execution (no shell invocation)

## 4. Test: git_status

- [x] 4.1 Test scenario: git_status_no_arguments
- [x] 4.2 Test scenario: git_status_with_arguments_fails
- [x] 4.3 Test scenario: git_status_in_git_repo
- [x] 4.4 Test scenario: git_status_not_in_git_repo

## 5. Test: git_log

- [x] 5.1 Test scenario: git_log_default_limit
- [x] 5.2 Test scenario: git_log_with_valid_limit_1
- [x] 5.3 Test scenario: git_log_with_valid_limit_50
- [x] 5.4 Test scenario: git_log_with_invalid_limit_0
- [x] 5.5 Test scenario: git_log_with_invalid_limit_51
- [x] 5.6 Test scenario: git_log_with_non_integer_limit
- [x] 5.7 Test scenario: git_log_with_null_limit
- [x] 5.8 Test scenario: git_log_in_non_git_repo

## 6. Test: git_diff_stat

- [x] 6.1 Test scenario: git_diff_stat_no_arguments
- [x] 6.2 Test scenario: git_diff_stat_with_arguments_fails
- [x] 6.3 Test scenario: git_diff_stat_with_changes
- [x] 6.4 Test scenario: git_diff_stat_no_changes
- [x] 6.5 Test scenario: git_diff_stat_not_in_git_repo

## 7. Test: rg_search

- [x] 7.1 Test scenario: rg_search_with_pattern_only
- [x] 7.2 Test scenario: rg_search_with_pattern_and_path
- [x] 7.3 Test scenario: rg_search_pattern_starting_with_dash
- [x] 7.4 Test scenario: rg_search_no_matches_exit_1
- [x] 7.5 Test scenario: rg_search_with_matches
- [x] 7.6 Test scenario: rg_search_with_invalid_flags
- [x] 7.7 Test scenario: rg_search_output_truncated

## 8. Test: Error Handling

- [x] 8.1 Test scenario: error_missing_binary
- [x] 8.2 Test scenario: error_timeout_10_seconds
- [x] 8.3 Test scenario: error_path_escape_attempt
- [x] 8.4 Test scenario: error_mcp_unknown_tool
- [x] 8.5 Test scenario: error_mcp_unknown_method
- [x] 8.6 Test scenario: error_mcp_unparseable_json
- [x] 8.7 Test scenario: error_format_isError_true_with_reason

## 9. Test: Path Isolation

- [x] 9.1 Test scenario: path_validation_within_root
- [x] 9.2 Test scenario: path_validation_parent_directory_escape
- [x] 9.3 Test scenario: path_validation_absolute_path
- [x] 9.4 Test scenario: path_validation_symlink_escape
- [x] 9.5 Test scenario: rg_search_default_path_to_root

## 10. Test: Output Limits

- [x] 10.1 Test scenario: output_under_8000_characters
- [x] 10.2 Test scenario: output_exactly_8000_characters
- [x] 10.3 Test scenario: output_exceeds_8000_characters
- [x] 10.4 Test scenario: output_truncated_marker_appended

## 11. Test: Timeout Enforcement

- [x] 11.1 Test scenario: command_completes_under_10_seconds
- [x] 11.2 Test scenario: command_timeout_at_10_seconds
- [x] 11.3 Test scenario: timeout_returns_isError_true

## 12. Test: No Shell Execution

- [x] 12.1 Test scenario: shell_metacharacters_treated_as_literals
- [x] 12.2 Test scenario: no_environment_variable_expansion
- [x] 12.3 Test scenario: no_command_chaining

## 13. Test: Read-Only Enforcement

- [x] 13.1 Test scenario: git_tools_do_not_modify_repository
- [x] 13.2 Test scenario: write_operations_fail_with_error

## 14. Test: MCP Protocol Compliance

- [x] 14.1 Test scenario: mcp_initialize_advertises_version_2025_06_18
- [x] 14.2 Test scenario: mcp_error_code_32602_for_unknown_tool
- [x] 14.3 Test scenario: mcp_error_code_32601_for_unknown_method
- [x] 14.4 Test scenario: mcp_error_code_32700_for_unparseable_json

## 15. Test: Server Registration

- [x] 15.1 Test scenario: registration_via_claude_mcp_add_command
- [x] 15.2 Test scenario: registration_via_mcp_json_config
- [x] 15.3 Test scenario: registration_fails_if_server_not_found
- [x] 15.4 Test scenario: server_starts_with_root_directory

## 16. Documentation and Examples

- [x] 16.1 Write README with installation instructions
- [x] 16.2 Write configuration examples (.mcp.json)
- [x] 16.3 Document error messages and troubleshooting
- [x] 16.4 Write user guide for using the CLI tools through Claude
