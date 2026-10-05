---
feature: specgate
acs:
  - id: AC-1
    given: "a PRD whose frontmatter has a bad AC id, a duplicate id, or an AC missing given, when, then or tests"
    when: "specgate runs layer L0"
    then: "L0 reports a finding for each defect, and a well-formed PRD produces none"
    tests:
      - "test_l0_schema.test_bad_id_fixture"
      - "test_l0_schema.test_dup_id_fixture"
      - "test_l0_schema.test_missing_then_fixture"
      - "test_l0_schema.test_no_tests_fixture"
      - "test_l0_schema.test_good_fixture"
  - id: AC-2
    given: "source files with an unused import, banned tokens such as TODO, or type and dead-code errors"
    when: "specgate runs layer L1"
    then: "L1 reports each violation from ruff, mypy, vulture or the banned-token scan"
    tests:
      - "test_l1_static.test_bad_f401_fixture"
      - "test_l1_static.test_bad_tokens_fixture"
      - "test_l1_static.test_mypy_with_injected_runner"
      - "test_l1_static.test_vulture_with_injected_runner"
  - id: AC-3
    given: "a PRD AC with no implements marker, no covers marker, an unknown AC in a marker, or a covering test with no asserts"
    when: "specgate runs layer L2"
    then: "L2 reports rule SG201 to SG205 for the matching defect"
    tests:
      - "test_l2_trace.test_sg201_rule_produced"
      - "test_l2_trace.test_sg202_rule_produced"
      - "test_l2_trace.test_sg203_rule_produced"
      - "test_l2_trace.test_sg204_rule_produced"
      - "test_l2_trace.test_sg205_rule_produced"
  - id: AC-4
    given: "tests tagged with covers markers where one test fails or is skipped"
    when: "specgate runs layer L3"
    then: "L3 reports SG301 for the AC with the non-passing test and writes JUnit with an ac property per test"
    tests:
      - "test_l3_run.test_sg301_failing_test_produces_rule"
      - "test_l3_run.test_sg301_skipped_test_produces_rule"
      - "test_l3_run.test_junit_parses_and_has_ac_properties"
  - id: AC-5
    given: "implementation lines marked for an AC that its covering tests never execute"
    when: "specgate runs layer L4"
    then: "L4 reports SG401 for the unexecuted lines"
    tests:
      - "test_l4_cov.test_uncovered_lines_produce_sg401"
      - "test_l4_cov.test_covered_lines_no_sg401"
  - id: AC-6
    given: "a weak test that still passes after the AC code is mutated"
    when: "specgate runs layer L5 with a fixed seed"
    then: "L5 reports SG501 for the surviving mutant, and a strong test produces none"
    tests:
      - "test_l5_mut.test_weak_fixture_produces_sg501"
      - "test_l5_mut.test_strong_fixture_produces_no_sg501"
      - "test_l5_mut.test_results_deterministic_weak"
  - id: AC-7
    given: "judges that veto a spec, or return bad JSON, or a debate with no cache and no API token"
    when: "specgate runs layer L6"
    then: "a veto fails only when a majority confirms it by deterministic recheck, an unconfirmed veto is ignored and logged, and bad output or a cache miss without a token fails"
    tests:
      - "test_l6_debate.test_run_debate_unconfirmed_veto_ignored"
      - "test_l6_debate.test_run_debate_confirmed_majority_veto_fails"
      - "test_l6_debate.test_run_debate_bad_json_fails"
      - "test_l6_debate.test_run_debate_cache_miss_no_token_fails"
  - id: AC-8
    given: "a pull request that changes code but touches nothing under docs"
    when: "the kt-docs workflow runs"
    then: "it fails unless the PR adds or modifies docs/kt/** or a docs markdown file, and the KT markdown passes the L1 lint"
    tests:
      - "kt-docs.yml::Require a KT doc change"
      - "test_l1_static.test_markdownlint_with_injected_runner"
---

# PRD: specgate

## Problem

A passing test suite does not show that the requested behavior exists. Nothing ties each requirement to a test, so requirements and tests drift apart.

## Goal

Make the tie mechanical. A feature merges only if every acceptance criterion is specified, implemented, covered, executed, and mutation-checked.

## Users

- Contributors adding a feature to this repo.
- Reviewers who need evidence, not claims, that each AC is tested.

## Acceptance criteria

The ACs live in the frontmatter above so layer L0 can validate them against `plugins/specgate/schema/prd.schema.json`. One AC per layer, L0 to L6, plus the knowledge-transfer docs rule.
