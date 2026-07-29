# DataTD Candidate Selection and Repair Adapter

## Fixed Repair Subset

The second-stage DataTD batch produced 83 rows where
`aromadr_candidate=True`. A deterministic subset of 40 files was selected with:

```powershell
python scripts\select_repair_candidates.py `
  .mvp_runs\datatd-batch40-aromadr\candidate_tests.csv `
  .mvp_runs\datatd-repair-subset\candidate_subset.csv `
  --limit 40 `
  --max-per-project 2
```

The fixed local subset contains:

- 40 candidate test files
- 29 Maven projects
- At most 2 files per project
- 574 AromaDr findings
- All 10 AromaDr smell types observed in the 40-project batch

The selector first covers rare smell types and then fills the subset in
deterministic project order. It only accepts rows with
`aromadr_candidate=True`. The subset CSV remains under `.mvp_runs` because it
contains machine-local DataTD paths.

## CSV-to-Repair-Loop Adapter

Run candidates through the adapter with:

```powershell
$env:AROMADR_API_URL="http://localhost:3000"
python -m test_repair_mvp `
  --repair-candidates .mvp_runs\datatd-repair-subset\candidate_subset.csv `
  --repair-output-dir .mvp_runs\datatd-repair-baseline `
  --repair-maven-repo ..\datatd\.m2\repository `
  --repair-timeout-seconds 600
```

Use `--repair-offset N` and `--repair-limit N` for non-overlapping batches.
Add `--coding-backend deepseek --repair-max-attempts 2` to enable real repair;
the default template backend remains baseline-only for arbitrary DataTD files.

For each candidate, the adapter:

1. Finds the nearest Maven project root.
2. Copies the project into a short, isolated task directory.
3. Excludes generated caches and build outputs while copying.
4. Saves `original_test.java`.
5. Creates a `ProjectTask` for the copied test file.
6. Runs `mvn test-compile`, then `mvn test`.
7. Runs the configured AromaDr and lightweight detectors.
8. Writes the normal repair-loop iteration artifacts.
9. Calls DeepSeek only for a compile/test/AromaDr-eligible candidate.
10. Validates JSON, path, package, and public-class constraints before writing.
11. Re-runs Maven and AromaDr and optionally performs one feedback repair.
12. Accepts the isolated repair or preserves the rejected proposal and rolls back.
13. Isolates candidate-level exceptions so the remaining batch can continue.
14. Verifies the original DataTD source remains unchanged.
15. Writes aggregate JSON, CSV, Markdown, diff, token, and cost artifacts.

Generated aggregate files:

```text
candidate_repair_summary.json
candidate_repair_results.csv
candidate_repair_report.md
```

Per-candidate artifacts and the original snapshot are written below
`tasks/<number>/`.

## Coding Backends and Safety Boundary

The current `TemplateCodingAgent` generates Calculator/String demo templates;
it is not a general DataTD repair implementation. Applying it to arbitrary
DataTD files would overwrite valid tests with unrelated demo source.

With the default template backend, the adapter runs in baseline-only mode:

- it calls the real repair-loop orchestrator;
- it skips initial demo-test generation;
- it sets the repair iteration budget to zero;
- it records Maven and AromaDr baselines;
- it guarantees the isolated test file is unchanged.

With the DeepSeek backend, only the authorized test file in an isolated project
copy may change. The API key and authorization header are never stored.
Empty/invalid JSON receives one non-thinking format-recovery request. A rejected
or exceptional proposal is restored from `original_test.java`; the original
DataTD project is never modified. When AromaDr is available, its findings alone
are authoritative for feedback and acceptance.

## Historical Baseline Smoke Test

The first three fixed-subset candidates were processed successfully:

- candidates: 3
- projects: 3
- compiled: 3
- tests passed: 3
- AromaDr available: 3
- AromaDr findings: 16
- unchanged files: 3

No original DataTD file was modified.

## DeepSeek Development Cohort

On 2026-07-30, the first ten fixed-subset candidates were used to stabilize the
real backend and evaluator:

- candidates screened: 10 across 10 projects
- baseline compiled: 8
- baseline tests passed and API-eligible: 4
- accepted repairs: 4 of 4 eligible
- authoritative AromaDr findings: 136 before, 0 after
- model calls: 6
- recorded tokens: 93,651
- estimated API cost: USD 0.0606
- candidate exceptions in the completed cohorts: 0
- original DataTD files changed: 0

The six ineligible candidates were skipped without an API call. This is a
development result, not a 10/10 repair rate and not a held-out evaluation.
