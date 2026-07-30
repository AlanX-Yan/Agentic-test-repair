# DataTD Windows Completion Plan

Date: 2026-07-28
Repository: https://github.com/AlanX-Yan/Agentic-test-repair
Main project directory: `aromadr-java-test-repair-mvp/`
Target machine: Windows
Dataset now available locally: DataTD, about 30 GB

This document is for continuing the project on Windows with Codex. It explains
what is already done, what remains before the project can be considered
complete, and the recommended order of work.

## 1. Current Project Status

The project is already beyond the initial MVP stage.

Completed:

- The proposal direction has been adjusted to focus on Java programs.
- AromaDr is integrated as the real test-smell detector.
- A full local repair loop exists:
  - generate Java/JUnit tests
  - compile/run tests
  - detect smells with AromaDr
  - generate repair feedback
  - repair tests
  - repeat until accepted or max iterations reached
- The MVP benchmark has 3 demo tasks and all 3 are accepted after repair.
- A Maven dataset scanner has been implemented.
- Batch AromaDr scanning has been implemented for Maven projects.
- A curated Maven project experiment has already been run.
- The curated experiment validated the pipeline on real Maven projects before
  DataTD was available.

Important limitation:

- The current repair agent is still deterministic/template-based.
- A real coding-agent backend has not been integrated yet.
- The dataset scanner identifies repair candidates, but the full repair loop has
  not yet been run systematically on DataTD.

## 2. Latest Known Curated Maven Result

This was the temporary experiment before DataTD was downloaded.

Curated repositories:

- `apache/commons-cli`
- `apache/commons-codec`
- `apache/commons-csv`
- `apache/commons-io`
- `apache/commons-lang`
- `apache/commons-text`
- `apache/commons-collections`
- `google/gson`
- `JodaOrg/joda-time`

Aggregate result:

```text
Maven projects/modules scanned: 16
Projects/modules with Java tests: 13
Projects/modules where tests compile: 5
Projects/modules where tests pass: 5
Test files scanned: 1271
Smelly test files: 1106
Candidate repair tests: 612
AromaDr available for files: 1271
```

Interpretation:

- This result proves the scanner and AromaDr batch pipeline work.
- The 612 number means repair candidates, not completed repairs.
- Some smelly files were excluded because their project/module did not compile,
  failed tests, or timed out in the local Maven screening step.

## 3. Windows Environment Checklist

Before running DataTD experiments, confirm these are installed on Windows.

Required:

- Git
- Python 3.10 or newer
- Java JDK, preferably JDK 17
- Maven 3.9.x
- Docker Desktop
- AromaDr Docker image/container

Recommended:

- VS Code
- Git Bash or Windows Terminal
- Enough disk space for:
  - DataTD: about 30 GB
  - Maven dependencies: possibly 10-30 GB more
  - scan outputs: several GB depending on run size

Useful commands:

```powershell
git --version
python --version
java -version
mvn -version
docker --version
docker ps
```

Expected AromaDr setup:

```powershell
docker start aromadr
```

If the container does not exist yet:

```powershell
docker run -d --name aromadr -p 3000:3000 -p 8000:8000 publioblenilio/aromadr
```

Then verify AromaDr is reachable at:

```text
http://localhost:3000
```

## 4. Recommended Windows Directory Layout

Use a layout like this:

```text
Agentic-test-repair/
  README.md
  DATATD_WINDOWS_COMPLETION_PLAN.md
  PROJECT_HANDOFF_WINDOWS.md
  aromadr-java-test-repair-mvp/
    test_repair_mvp/
    scripts/
    demo/
    docs/
    .mvp_runs/
  datasets/
    DataTD/
      ...
    .m2/
      repository/
```

Notes:

- `datasets/` should stay local and should not be committed to GitHub.
- `.mvp_runs/` should stay local and should not be committed unless a small
  summarized artifact is intentionally copied into `docs/`.
- The real DataTD raw files should not be pushed to GitHub.

## 5. Immediate First Task on Windows

First, make sure the current repository is synced.

```powershell
git clone https://github.com/AlanX-Yan/Agentic-test-repair.git
cd Agentic-test-repair
```

If the repo already exists:

```powershell
git pull
```

Then enter the MVP directory:

```powershell
cd aromadr-java-test-repair-mvp
```

Run the local demo to verify the Python module works:

```powershell
python -m test_repair_mvp
```

Run the 3-task benchmark:

```powershell
python -m test_repair_mvp --benchmark demo/config/benchmark.json --run-dir .mvp_runs/benchmark-windows
```

With AromaDr running:

```powershell
$env:AROMADR_API_URL="http://localhost:3000"
python -m test_repair_mvp --benchmark demo/config/benchmark.json --run-dir .mvp_runs/benchmark-windows-aromadr
```

Success criterion:

- The benchmark completes.
- AromaDr is reported as available.
- The report is written under `.mvp_runs/benchmark-windows-aromadr/`.

## 6. DataTD Work Still Required

The project is not complete until the following items are done.

### Task 1: Inspect DataTD Structure

Goal:

- Understand how the 30 GB DataTD dataset is organized.

What to check:

- Does DataTD contain cloned Maven repositories directly?
- Does it contain compressed archives?
- Does it contain metadata files listing project names, commits, URLs, or build
  commands?
- Are projects nested one level deep or multiple levels deep?
- Are there duplicate modules?

Suggested commands:

```powershell
Get-ChildItem ..\datasets\DataTD | Select-Object -First 30
Get-ChildItem ..\datasets\DataTD -Recurse -Filter pom.xml | Measure-Object
Get-ChildItem ..\datasets\DataTD -Recurse -Filter pom.xml | Select-Object -First 20
```

Expected output:

- A short note describing the dataset layout.
- A count of discovered `pom.xml` files.
- A decision about the actual scan root path.

Completion criterion:

- We know the correct path to pass into `--scan-dataset`.

### Task 2: Run a Fast Structure-Only DataTD Scan

Goal:

- Confirm that the scanner can traverse DataTD before running expensive Maven
  builds.

Command:

```powershell
$env:AROMADR_API_URL="http://localhost:3000"
python -m test_repair_mvp `
  --scan-dataset ..\datasets\DataTD `
  --dataset-report-dir .mvp_runs\datatd-structure-scan `
  --dataset-skip-maven
```

Expected outputs:

```text
.mvp_runs/datatd-structure-scan/dataset_scan_summary.json
.mvp_runs/datatd-structure-scan/projects.csv
.mvp_runs/datatd-structure-scan/test_files.csv
.mvp_runs/datatd-structure-scan/candidate_tests.csv
.mvp_runs/datatd-structure-scan/dataset_candidate_report.md
```

Completion criterion:

- The scan finishes without crashing.
- The report shows how many Maven projects/modules and Java test files exist.

### Task 3: Run a Small DataTD Pilot Scan

Goal:

- Avoid waiting many hours before confirming the full setup works.

Approach:

- Select 5-10 DataTD Maven projects/modules.
- Copy or point the scanner to a small subset.
- Run Maven screening and AromaDr detection on that subset.

Recommended command:

```powershell
$env:AROMADR_API_URL="http://localhost:3000"
python -m test_repair_mvp `
  --scan-dataset ..\datasets\DataTD-small `
  --dataset-report-dir .mvp_runs\datatd-pilot `
  --dataset-maven-strategy fast `
  --dataset-candidate-mode test-compile `
  --dataset-maven-repo ..\datasets\.m2\repository `
  --dataset-timeout-seconds 600
```

Completion criterion:

- At least several projects are scanned.
- The report includes:
  - projects/modules scanned
  - projects/modules with Java tests
  - projects/modules where tests compile
  - smelly test files
  - candidate repair tests
  - AromaDr availability count

### Task 4: Run the Full DataTD Batch Scan

Goal:

- Produce the main dataset-level result requested by the advisor.

Recommended command:

```powershell
$env:AROMADR_API_URL="http://localhost:3000"
python -m test_repair_mvp `
  --scan-dataset ..\datasets\DataTD `
  --dataset-report-dir .mvp_runs\datatd-full-scan `
  --dataset-maven-strategy fast `
  --dataset-candidate-mode test-compile `
  --dataset-maven-repo ..\datasets\.m2\repository `
  --dataset-timeout-seconds 600
```

If the full run is too slow:

- Split DataTD into batches.
- Run the scanner on each batch separately.
- Aggregate later using `scripts/aggregate_dataset_scans.py`.

Example aggregation:

```powershell
python scripts/aggregate_dataset_scans.py `
  .mvp_runs\datatd-batch-001 `
  .mvp_runs\datatd-batch-002 `
  .mvp_runs\datatd-batch-003 `
  --output-dir .mvp_runs\datatd-aggregate
```

Completion criterion:

- There is one final aggregate report for DataTD.
- The report can answer:
  - how many Maven projects/modules were scanned
  - how many had Java tests
  - how many compiled
  - how many passed tests
  - how many test files were scanned
  - how many had AromaDr smells
  - how many became repair candidates
  - top smell types

### Task 5: Explain Non-Candidate Smelly Files

Goal:

- Answer Professor Fazzini's question more rigorously:
  why do some smelly files not become repair candidates?

Need to produce a breakdown like:

```text
Smelly files total: N
Repair candidates: M
Excluded smelly files: N - M

Excluded because project did not compile: A
Excluded because tests failed: B
Excluded because Maven timed out: C
Excluded because unsupported layout or missing test root: D
Excluded because detector/report parsing issue: E
```

Current scanner already records Maven return codes and status in `projects.csv`.
If the existing reports are not enough, add a small analysis script that joins
`test_files.csv` with `projects.csv` and writes:

```text
non_candidate_breakdown.csv
non_candidate_breakdown.md
```

Completion criterion:

- The project can clearly explain the gap between smelly files and repair
  candidates.
- The explanation separates environment/build issues from repair-algorithm
  limitations.

### Task 6: Select a Repair Evaluation Subset

Goal:

- Do not immediately run repair on every candidate in the full dataset.
- Start with a representative subset.

Suggested subset design:

- 30-50 repair candidates total for the first real repair experiment.
- Include multiple projects.
- Include the most common smell types.
- Include both easy and harder cases.

Suggested categories:

- `AssertionRoulette`
- `MagicNumberTest`
- `UnknownTest`
- `ExceptionHandling`
- `MissingAssertion`
- `DuplicateAssert`
- `ConditionalTest`

Need to create:

```text
.mvp_runs/datatd-repair-subset/candidate_subset.csv
```

Completion criterion:

- A fixed subset exists and can be reused.
- The subset selection method is documented.

### Task 7: Connect Dataset Candidates to the Repair Loop

Goal:

- The current scanner identifies candidate test files.
- The next step is to run the repair loop directly on those candidate files.

Current gap:

- The original repair loop is task-config based.
- Dataset candidates come from arbitrary Maven projects.
- We need an adapter that turns a row from `candidate_tests.csv` into a repair
  task.

Needed implementation:

- Add a CLI mode such as:

```text
--repair-candidates path/to/candidate_subset.csv
```

or:

```text
--repair-dataset-candidates path/to/candidate_tests.csv
--repair-limit 50
```

For each candidate:

- Locate project root.
- Locate test file.
- Snapshot original file.
- Run Maven baseline check.
- Run AromaDr on original test.
- Invoke repair agent.
- Apply repaired test.
- Run Maven check again.
- Run AromaDr again.
- Record before/after smells.
- Restore or preserve modified files according to experiment mode.

Completion criterion:

- A command can repair candidates selected from DataTD.
- Per-candidate reports are written.

### Task 8: Add a Real Coding-Agent Backend

Goal:

- Move beyond deterministic repair templates.
- This is important because the proposal is about agentic repair, not only
  hand-written smell templates.

Current state:

- `test_repair_mvp/agents.py` contains deterministic repair logic.
- It handles only selected smell types.

Needed implementation:

- Keep the deterministic agent as a reproducible baseline.
- Add a new coding-agent backend behind the same interface.
- The backend should receive:
  - project context
  - failing test file
  - Maven output
  - AromaDr smell type and line information
  - repair goal
  - constraints, such as preserving behavior and keeping tests passing

Possible CLI design:

```text
--agent deterministic
--agent codex
--agent openai
```

Expected output per repair:

- original test file
- repaired test file
- prompt or structured repair request
- build/test result before and after
- smell count before and after
- final status

Completion criterion:

- At least one real agent backend can repair DataTD candidate tests.
- Deterministic baseline remains available.

### Task 9: Expand Smell-Specific Repair Strategies

Goal:

- Improve repair coverage for the smell types actually common in DataTD.

Already partially supported:

- `UnknownTest`
- `MagicNumberTest`
- `AssertionRoulette`
- `ExceptionHandling`

Need to inspect DataTD top smell distribution, then prioritize.

Likely next smell types:

- `MissingAssertion`
- `DuplicateAssert`
- `ConditionalTest`
- `EmptyTest`
- `IgnoredTest`
- `SleepyTest`
- `RedundantPrint`
- `GenericTestName`

Important:

- Not every smell should be repaired with a simple template.
- Some smells require semantic understanding and should be assigned to the real
  coding-agent backend.

Completion criterion:

- The report can say which smell types are supported by deterministic repair,
  which require the coding agent, and which are out of scope.

### Task 10: Define Final Evaluation Metrics

Goal:

- Make the final result look like a research evaluation, not just a demo.

Required metrics:

- Projects/modules scanned
- Projects/modules with Java tests
- Projects/modules that compile
- Projects/modules whose tests pass
- Test files scanned
- Smelly test files
- Repair candidates
- Repair attempts
- Successful repairs
- Failed repairs
- Skipped repairs
- Smell count before repair
- Smell count after repair
- Smell reduction percentage
- Test pass rate before repair
- Test pass rate after repair
- Build failures caused by repair
- Runtime/timeouts

Recommended grouped tables:

- Overall summary
- Per-project summary
- Per-smell-type summary
- Failure reason summary
- Representative before/after examples

Completion criterion:

- A final `docs/DATATD_RESULTS.md` exists with all key metrics.

### Task 11: Add Reproducibility Controls

Goal:

- Make results credible and repeatable.

Needed:

- Record Java version.
- Record Maven version.
- Record Docker/AromaDr version if possible.
- Record DataTD path or version/metadata.
- Record scanner command.
- Record timeout settings.
- Record candidate mode.
- Record repair agent mode.
- Record random seed if candidate sampling is randomized.

Suggested output:

```text
.mvp_runs/datatd-full-scan/environment.json
.mvp_runs/datatd-repair-run/environment.json
```

Completion criterion:

- Another person can understand exactly how the experiment was run.

### Task 12: Produce Final Advisor-Facing Report

Goal:

- Give Professor Fazzini a concise but convincing progress report.

Suggested final report files:

```text
aromadr-java-test-repair-mvp/docs/DATATD_RESULTS.md
aromadr-java-test-repair-mvp/docs/REPAIR_EVALUATION.md
aromadr-java-test-repair-mvp/docs/FAILURE_ANALYSIS.md
```

The advisor-facing report should include:

- Why DataTD was used
- How many Maven projects/modules were found
- How many had compilable tests
- How AromaDr was used
- How candidates were selected
- How many repairs were attempted
- How many repairs succeeded
- Which smell types were repaired
- Why some smells/files were not repaired
- Limitations
- Next steps

Completion criterion:

- The professor can read the report without needing local files from
  `.mvp_runs/`.

### Task 13: Clean and Push Public Repository

Goal:

- Keep GitHub clean for the professor and outside readers.

Commit:

- source code
- scripts
- small configs
- docs
- summarized results

Do not commit:

- DataTD raw dataset
- `.mvp_runs/` raw outputs unless carefully curated
- Maven dependency cache
- Docker images/containers
- temporary logs
- generated project checkouts

Before pushing:

```powershell
git status
git diff
```

Then:

```powershell
git add README.md aromadr-java-test-repair-mvp docs *.md
git commit -m "Add DataTD experiment workflow and results"
git push
```

Adjust the exact `git add` command based on actual changed files.

Completion criterion:

- GitHub contains enough code/docs for the professor to understand and reproduce
  the work.
- Large local datasets and raw runs remain ignored.

## 7. Recommended Order of Execution

Follow this order on Windows:

1. Verify environment: Python, Java, Maven, Docker, AromaDr.
2. Pull or clone the GitHub repository.
3. Run the 3-task local benchmark with AromaDr.
4. Inspect DataTD folder structure.
5. Run structure-only DataTD scan with `--dataset-skip-maven`.
6. Run a small DataTD pilot scan with Maven enabled.
7. Fix Windows path or Maven issues found by the pilot.
8. Run full DataTD scan, or split into batches and aggregate.
9. Generate non-candidate breakdown.
10. Select a repair subset from DataTD candidates.
11. Add candidate-to-repair-loop adapter.
12. Run deterministic baseline repairs on the subset.
13. Add real coding-agent backend.
14. Run coding-agent repairs on the same subset.
15. Compare deterministic vs coding-agent results.
16. Write `DATATD_RESULTS.md`, `REPAIR_EVALUATION.md`, and
    `FAILURE_ANALYSIS.md`.
17. Clean repo and push public-facing files to GitHub.

## 8. Definition of Project Complete

The project can be considered complete when all of these are true:

- DataTD has been scanned with AromaDr.
- The scan result is summarized in a public Markdown report.
- The project explains why some smelly tests are not repair candidates.
- A subset of DataTD repair candidates has been selected and documented.
- The repair loop has been run on real DataTD candidate tests.
- Results include before/after build status and before/after smell counts.
- A real coding-agent backend has been integrated or clearly separated as the
  next major limitation.
- The final GitHub repository contains clean code, docs, scripts, and summary
  results, but not the 30 GB dataset or raw local caches.

## 9. Most Important Next Step

The single most important next step is:

```text
Run a DataTD pilot scan on 5-10 Maven projects with AromaDr and Maven enabled.
```

Do not start with the full 30 GB dataset experiment immediately. The pilot scan
will reveal Windows path issues, Maven dependency problems, timeout settings,
and AromaDr availability problems before a long full run.

After the pilot works, run the full DataTD scan or split it into batches.
