## 1. Plugin skeleton

- [x] 1.1 Create `plugins/specgate` with the `specgate check` CLI
- [x] 1.2 Add the PRD frontmatter schema `schema/prd.schema.json`

## 2. Gates

- [x] 2.1 L0 schema gate (`l0_schema.py`)
- [x] 2.2 L1 static gate (`l1_static.py`)
- [x] 2.3 L2 trace gate (`l2_trace.py`)
- [x] 2.4 L3 execution gate (`l3_run.py`)
- [x] 2.5 L4 coverage gate (`l4_cov.py`)
- [x] 2.6 L5 mutation gate (`l5_mut.py`)
- [x] 2.7 L6 debate gate (`l6_debate.py`)
- [x] 2.8 Deterministic `trace.json` (`trace.py`)

## 3. Wiring

- [x] 3.1 Local hooks via lefthook
- [x] 3.2 CI workflow `spec-gate.yml`
- [x] 3.3 CI workflow `kt-docs.yml`

## 4. Documentation

- [x] 4.1 Write this change: proposal, PRD, spec, tasks
- [x] 4.2 Write the knowledge-transfer doc `docs/kt/specgate/README.md`
