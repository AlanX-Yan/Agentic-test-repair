# AromaDr Java Test Repair MVP

This MVP implements the architecture from the proposal:

1. A coding agent generates Java tests.
2. A Java execution harness compiles and runs them.
3. A detector layer runs AromaDr when configured, with a lightweight fallback for this local demo.
4. A master evaluator checks build status, test status, and smell findings.
5. A feedback generator turns findings into repair instructions.
6. The coding agent repairs the tests and the loop repeats.


## Quick Start

Run from this directory:

```bash
python3 -m test_repair_mvp
```

Expected result:

```text
Goal-driven Java test repair MVP complete
Task: calculator-java-demo
Iterations: 2
Initial smells: 4
Final smells: 0
Final accepted: True
Artifacts: .../.mvp_runs/latest/artifacts
```

Open the generated report:

```bash
cat .mvp_runs/latest/artifacts/report.md
```

Run the proposal-style benchmark evaluation:

```bash
python3 -m test_repair_mvp --benchmark demo/config/benchmark.json --run-dir .mvp_runs/benchmark
```

Current benchmark demo result:

```text
Tasks: 3
Accepted: 3
Initial smells: 12
Final smells: 0
```

With AromaDr running and `AROMADR_API_URL=http://localhost:3000`, the benchmark currently reports:

```text
Tasks: 3
Accepted: 3
Initial smells: 15
Final smells: 0
Smell delta: 15
```

Open aggregate outputs:

```bash
cat .mvp_runs/benchmark/benchmark_report.md
cat .mvp_runs/benchmark/benchmark_results.csv
```

## Maven Dataset Scanner

The MVP now includes a dataset-preparation mode for extended experiments on
Maven project datasets such as DataTD. It discovers Maven projects, checks
whether their tests compile and pass, scans Java test files for smells, and
writes candidate repair reports.

For a smaller alternative to a large dataset, prepare a curated set of real
Maven projects:

```bash
python3 scripts/prepare_curated_maven_dataset.py --tier starter --limit 2
```

Run the included sample dataset:

```bash
python3 -m test_repair_mvp --scan-dataset demo/dataset_sample --dataset-report-dir .mvp_runs/dataset-scan-sample
```

With AromaDr running:

```bash
AROMADR_API_URL="http://localhost:3000" python3 -m test_repair_mvp --scan-dataset demo/dataset_sample --dataset-report-dir .mvp_runs/dataset-scan-sample-aromadr
```

The scanner writes `dataset_scan_summary.json`, `projects.csv`,
`test_files.csv`, `candidate_tests.csv`, and `dataset_candidate_report.md`.

Select a fixed AromaDr-only repair subset and validate the candidate-to-repair
bridge:

```bash
python scripts/select_repair_candidates.py \
  .mvp_runs/datatd-batch40-aromadr/candidate_tests.csv \
  .mvp_runs/datatd-repair-subset/candidate_subset.csv \
  --limit 40 --max-per-project 2

python -m test_repair_mvp \
  --repair-candidates .mvp_runs/datatd-repair-subset/candidate_subset.csv \
  --repair-output-dir .mvp_runs/datatd-repair-baseline \
  --repair-maven-repo ../datatd/.m2/repository
```

With the default `template` backend, the DataTD adapter is baseline-only. With
the explicitly selected `deepseek` backend, eligible candidates enter the
validated repair-and-rollback loop described below.

## DeepSeek Repair Backend

Configure DeepSeek in the PowerShell session that will run the project:

```powershell
$env:DEEPSEEK_API_KEY = Read-Host "DeepSeek API key" -MaskInput
$env:DEEPSEEK_BASE_URL = "https://api.deepseek.com"
$env:DEEPSEEK_MODEL = "deepseek-v4-pro"
```

Run one eligible candidate as an end-to-end smoke test:

```powershell
python -m test_repair_mvp `
  --repair-candidates .mvp_runs/datatd-repair-subset/candidate_subset.csv `
  --repair-output-dir .mvp_runs/deepseek-smoke-1 `
  --repair-maven-repo ../datatd/.m2/repository `
  --coding-backend deepseek `
  --repair-max-attempts 1 `
  --repair-limit 1
```

Only candidates whose baseline compiles, passes tests, has AromaDr available,
and has at least one AromaDr finding are sent to DeepSeek. The model may replace
only the isolated copy of the selected Java test. Rejected changes are saved as
`rejected_test.java` plus `repair.diff`, then rolled back. API metadata and
token-based cost estimates are stored in `model_calls.json`; API keys and raw
authorization headers are never written to artifacts.

### Current DataTD Development Result

The DeepSeek backend has completed a development cohort used to stabilize the
prompt and evaluator:

- 10 candidates screened across 10 Maven projects
- 8 compiled at baseline; 4 passed baseline tests and were API-eligible
- 4 of 4 eligible repairs accepted
- 136 authoritative AromaDr findings reduced to 0
- 6 model calls, 93,651 recorded tokens, approximately USD 0.0606
- original DataTD files remained byte-for-byte unchanged

These are development results, not held-out final evaluation results. Batch
runs support `--repair-offset` plus `--repair-limit` to avoid duplicate calls,
one non-thinking recovery for empty/invalid JSON, and candidate-level failure
isolation.

### Frozen Held-Out Evaluation

The `deepseek-v1` held-out evaluation is complete:

- 17 strictly eligible candidates from 11 projects
- 15 accepted and 2 rejected/rolled back: 88.2% success
- 10 first-attempt successes and 5 feedback-retry successes
- 175 initial AromaDr findings; accepted repairs ended with 0
- 24 model calls, 225,978 tokens, approximately USD 0.1381
- 1 compile regression and 1 test regression, both rejected
- no original DataTD file changed

See `docs/DATATD_RESULTS.md`, `docs/REPAIR_EVALUATION.md`, and
`docs/FAILURE_ANALYSIS.md`. Small path-neutral results are under
`docs/results/`; raw `.mvp_runs` artifacts remain local.

The exact frozen command and hashes are documented in
`docs/EVALUATION_PROTOCOL.md`. Manual review of ten accepted diffs found seven
clean passes, one minor caution, and two repairs that should fail a stricter
human quality gate; see `docs/SEMANTIC_REVIEW.md`.

### DeepSeek V4 Pro Extension Evaluation

Three independently frozen protocols used the same repair semantics and the
`deepseek-v4-pro` model. The final formal evaluation contains exactly 100
strict-eligible candidates:

- 85 accepted and 15 rejected/rolled back: 85.0% automated success
- 484 initial AromaDr findings reduced to 30 in last proposals; all remaining
  findings were in rejected proposals
- 146 model calls, 1,838,056 tokens, estimated USD 0.99152858
- 55 first-attempt successes and 30 feedback-retry successes
- no original DataTD file changed

V3 contributed 57 candidates across Java 8, 11, and 17, selected using exact
commits and Java versions from an advisor-provided DataTD benchmark list. Its
automated result was 46/57 (80.7%) at USD 0.70249373. Manual review found that
the structural gate can still accept semantically weak changes, so 85/100 is
reported specifically as the automated endpoint.

See `docs/EVALUATION_PROTOCOL_V3.md`, `docs/REPAIR_EVALUATION.md`,
`docs/SEMANTIC_REVIEW_V3.md`, and `docs/results/formal-100/`.

## AromaDr Integration

The preferred integration is AromaDr's HTTP API. Start AromaDr separately, then set `AROMADR_API_URL`:

```bash
AROMADR_API_URL="http://localhost:3000" python3 -m test_repair_mvp --benchmark demo/config/benchmark.json --run-dir .mvp_runs/benchmark-aromadr
```

The detector posts each generated JUnit test file to:

```text
POST /file-test-smells/detect
{
  "language": "java",
  "framework": "junit",
  "testFileContent": "..."
}
```

It parses AromaDr's real response shape: `testSuites[].tests[].testSmells[]`, where each smell has `name`, `startLine`, `startColumn`, `endLine`, and `endColumn`.

`AROMADR_CMD` is still supported for command-line experiments. The command can use `{project_root}` and `{test_file}` placeholders:

```bash
AROMADR_CMD="java -jar /path/to/aromadr.jar --project {project_root} --test {test_file}" python3 -m test_repair_mvp
```

The adapter accepts a normalized CSV-like output:

```text
file,line,smell,message
src/test/java/com/example/CalculatorBehaviorTest.java,8,MissingAssertion,No meaningful assertion
```

The command adapter accepts JSON list/object outputs with fields such as `file`, `path`, `line`, `startLine`, `smell_type`, `type`, `smell`, `message`, or `description`.

If AromaDr is not running, the detector records `aroma_dr_available=false` and falls back to the local lightweight JUnit checks so the repair loop remains demoable.

## Project Layout

```text
test_repair_mvp/
  agents.py          template and DeepSeek coding-agent backends
  harness.py         Java execution harness for javac-demo, Maven, and Gradle
  detectors.py       AromaDr adapter plus lightweight local detector
  feedback.py        master evaluator and feedback generator
  orchestrator.py    goal-driven repair loop
  reporting.py       iteration snapshots and final reports
  benchmark.py       multi-task paired before-after evaluation
demo/
  java_project/      calculator Java target used by the demo
  string_project/    string sanitizer Java target used by the benchmark
  maven_calculator_project/ real Maven/JUnit 5 benchmark target
  config/            task and benchmark configuration
docs/
  ARCHITECTURE.md    full architecture and extension plan
  AROMADR_INTEGRATION.md exact AromaDr API wiring notes
  CURATED_MAVEN_DATASET.md smaller real-project dataset workflow
  CURATED_MAVEN_RESULTS.md current curated dataset scan summary
  DATASET_SCANNING.md Maven dataset scanner and candidate report notes
```

## MVP Boundaries

- The template backend is deterministic so bundled demos remain reproducible.
- DeepSeek is the real OpenAI-compatible backend for eligible DataTD repairs.
- The generated tests are JUnit-style, but the local demo uses a tiny JUnit API stub so it can run without downloading dependencies.
- The local detector is not a replacement for AromaDr; it exists so the demo runs when the AromaDr service is not currently available.
- The current deterministic repair templates address the AromaDr smells observed so far: `UnknownTest`, `MagicNumberTest`, `AssertionRoulette`, and `ExceptionHandling`.
- When AromaDr is available, its findings are authoritative for acceptance and feedback; lightweight findings remain diagnostic.
- Candidate repair changes only the authorized test file in an isolated copy; rejected changes are snapshotted and rolled back.
- The 100-candidate held-out evaluation, budget controls, rollback, and final
  result summaries are complete. JaCoCo and PIT remain optional extensions.
