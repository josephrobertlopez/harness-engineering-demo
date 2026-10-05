## ADDED Requirements

### Requirement: L0 validates PRD structure
The system SHALL validate PRD frontmatter against the PRD schema and report a finding for every malformed or duplicate acceptance criterion. (AC-1)

#### Scenario: Malformed ACs are reported
- **WHEN** a PRD has a bad AC id, a duplicate id, or an AC missing given, when, then or tests
- **THEN** layer L0 reports a finding for each defect

#### Scenario: Well-formed PRD passes
- **WHEN** a PRD frontmatter matches the schema
- **THEN** layer L0 reports no findings

### Requirement: L1 enforces static hygiene
The system SHALL run lint, type, dead-code and banned-token checks over the source and report each violation. (AC-2)

#### Scenario: Unused import and banned tokens
- **WHEN** source contains an unused import or a banned token such as TODO
- **THEN** layer L1 reports a violation for each

### Requirement: L2 links every AC to code and tests
The system SHALL require that every AC has an implements marker and a covers marker, that markers name known ACs, and that covering tests contain assertions. (AC-3)

#### Scenario: Missing or unknown markers
- **WHEN** an AC lacks a marker, a marker names an unknown AC, or a covering test has no asserts
- **THEN** layer L2 reports rule SG201 to SG205 for the defect

### Requirement: L3 runs the covering tests
The system SHALL run every test tagged with a covers marker and fail any AC that has a non-passing test. (AC-4)

#### Scenario: Failing or skipped test
- **WHEN** a covering test fails or is skipped
- **THEN** layer L3 reports SG301 and writes JUnit with an ac property per test

### Requirement: L4 requires AC code to be executed
The system SHALL fail when a line marked as implementing an AC is not executed by that AC's tests. (AC-5)

#### Scenario: Unexecuted implementation line
- **WHEN** an implements-marked line is never run by its covering tests
- **THEN** layer L4 reports SG401

### Requirement: L5 requires tests to catch mutations
The system SHALL mutate AC code with a fixed seed and fail when any mutant survives. (AC-6)

#### Scenario: Weak test lets a mutant survive
- **WHEN** a mutated AC line still passes its tests
- **THEN** layer L5 reports SG501

#### Scenario: Strong test kills the mutant
- **WHEN** every mutant is killed by the tests
- **THEN** layer L5 reports no findings

### Requirement: L6 debate vetoes only when checkable
The system SHALL run a prover, a refuter and three judges, and SHALL fail only on a majority veto confirmed by deterministic recheck, or on malformed output, or on a cache miss without a token. (AC-7)

#### Scenario: Unconfirmed veto
- **WHEN** a judge vetoes with a claim the deterministic recheck cannot confirm
- **THEN** the veto is ignored and logged

#### Scenario: Confirmed majority veto
- **WHEN** a majority of judges veto with a confirmed file, line and claim
- **THEN** layer L6 fails

#### Scenario: Bad output
- **WHEN** a judge returns invalid JSON
- **THEN** layer L6 fails

### Requirement: Pull requests carry a knowledge-transfer doc
The system SHALL fail a pull request that does not add or modify `docs/kt/**` or a docs markdown file, and SHALL lint the KT markdown. (AC-8)

#### Scenario: No docs change
- **WHEN** a pull request changes only code
- **THEN** the kt-docs workflow fails

#### Scenario: KT doc present
- **WHEN** a pull request modifies a file under docs/kt
- **THEN** the kt-docs workflow passes
