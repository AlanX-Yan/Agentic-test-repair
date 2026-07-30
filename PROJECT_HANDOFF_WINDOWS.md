# Project Handoff Notes for Windows

Date: 2026-07-20
Repository: https://github.com/AlanX-Yan/Agentic-test-repair
Current branch: `main`
Latest pushed commit: `1364a7b Add Maven dataset scanner`

This file summarizes the project history, current progress, important local
details, and the next steps for continuing development on Windows.

## 1. Research Direction

The project was adjusted based on Professor Mattia Fazzini's suggestion:

- Focus on Java programs.
- Use JUnit tests.
- Use AromaDr as the main test-smell detector.
- Build an agentic repair loop that improves generated tests using smell
  feedback.

The current research idea is:

```text
Generate Java/JUnit tests
-> Compile and run tests
-> Detect test smells with AromaDr
-> Convert build/test/smell feedback into repair instructions
-> Repair tests
-> Repeat until accepted
```

The revised proposal files are in:

```text
docs/proposal/
  Goal-Driven_Test_Repair_Proposal_Improved.docx
  Goal-Driven_Test_Repair_Proposal_Improved.html
  build_improved_proposal.py
```

## 2. Conversation and Advisor Context

Professor Fazzini first suggested changing the project toward Java analysis and
AromaDr:

```text
The proposal is interesting. I suggest we work on this so that we are able to
analyze Java programs ... I suggest using the tool from this work to detect test
smells: AromaDr: A Language-Independent Tool for Detecting Test Smells.
```

After the first MVP update, the professor replied:

```text
the direction looks good and the results look good.
We have a big dataset of Maven projects (DataTD: a dataset of java projects
including test doubles). This dataset was not built with test smells in mind but
might be a good place where to find projects with tests and that can compile.
Which dataset were you considering using in the extended experiments?
```

Meaning:

- He approved the project direction and initial results.
- He suggested DataTD as a possible large Maven dataset.
- He wants to know what dataset will be used for extended experiments.

Recommended response direction:

```text
I added a Maven dataset-scanning pipeline before moving to a larger dataset. It
can scan Maven projects, check whether tests compile and pass, run AromaDr batch
detection, and generate candidate repair reports. DataTD sounds like a very good
fit. Could I get access to DataTD or instructions for using it? Also, would you
prefer a short written progress report or a brief oral update?
```

## 3. Current Completed Work

### 3.1 MVP Repair Loop

Implemented under:

```text
aromadr-java-test-repair-mvp/test_repair_mvp/
```

Key files:

- `agents.py`: deterministic demo coding agent and smell-specific repair logic.
- `harness.py`: Java execution harness for `javac-demo`, Maven, and Gradle paths.
- `detectors.py`: AromaDr HTTP/command adapter plus lightweight fallback detector.
- `feedback.py`: master evaluator and smell-to-feedback generator.
- `orchestrator.py`: generate -> execute -> detect -> evaluate -> repair loop.
- `benchmark.py`: multi-task before/after evaluation.
- `reporting.py`: writes per-iteration artifacts and final reports.
- `models.py`: shared dataclasses.
- `cli.py`: command-line entry point.

Current repair logic handles the main AromaDr smells observed so far:

- `UnknownTest`
- `MagicNumberTest`
- `AssertionRoulette`
- `ExceptionHandling`

### 3.2 AromaDr Integration

The preferred AromaDr path is HTTP:

```text
AROMADR_API_URL=http://localhost:3000
POST /file-test-smells/detect
```

The detector sends:

```json
{
  "language": "java",
  "framework": "junit",
  "testFileContent": "..."
}
```

It parses AromaDr's response shape:

```text
testSuites[].tests[].testSmells[]
```

If AromaDr is unavailable, the project falls back to a lightweight detector so
the pipeline remains demoable.

### 3.3 Benchmark Demo

Current benchmark tasks:

- `demo/java_project`: simple calculator Java demo using local JUnit-style stubs.
- `demo/string_project`: string sanitizer Java demo using local JUnit-style stubs.
- `demo/maven_calculator_project`: real Maven/JUnit project.

Benchmark config:

```text
aromadr-java-test-repair-mvp/demo/config/benchmark.json
```

Latest known result with AromaDr running locally through Docker:

```text
Tasks: 3
Accepted: 3
Initial smells: 15
Final smells: 0
Smell delta: 15
Initial passed: 2
Final passed: 3
```

### 3.4 Maven Dataset Scanner

Implemented after the professor mentioned DataTD.

Key file:

```text
aromadr-java-test-repair-mvp/test_repair_mvp/dataset_scanner.py
```

Documentation:

```text
aromadr-java-test-repair-mvp/docs/DATASET_SCANNING.md
```

The scanner can:

- Discover Maven projects by finding `pom.xml`.
- Find Java test files under `src/test/java`.
- Run `mvn test-compile`.
- Run `mvn test`.
- Batch-scan test files with AromaDr or fallback detector.
- Produce candidate repair reports.

Candidate rule:

```text
Maven project
+ Java tests exist
+ mvn test-compile succeeds
+ mvn test succeeds
+ detector reports at least one smell
= candidate repair test
```

Generated output files:

```text
dataset_scan_summary.json
projects.csv
test_files.csv
candidate_tests.csv
dataset_candidate_report.md
```

Sample dataset added for verification:

```text
aromadr-java-test-repair-mvp/demo/dataset_sample/smelly_maven_project/
```

Known sample scanner result with real AromaDr:

```text
Maven projects scanned: 1
Projects with Java tests: 1
Projects where tests compile: 1
Projects where tests pass: 1
Test files scanned: 1
Smelly test files: 1
Candidate repair tests: 1
AromaDr available for files: 1
Total smells: 8
AssertionRoulette: 3
MagicNumberTest: 3
GenericTestName: 1
OverlyBroadTest: 1
```

## 4. Current GitHub State

The local repository was pushed to GitHub.

Current confirmed state:

```text
main == origin/main
latest commit: 1364a7b Add Maven dataset scanner
```

Recent commits:

```text
1364a7b Add Maven dataset scanner
53a57d6 Update README.md
d00f3d3 Update README to reflect changes in proposal wording
0deec5e Initial agentic test repair prototype
```

## 5. What Was Not Pushed

The public GitHub repository intentionally excludes local tools, cloned external
repos, and generated artifacts.

Ignored but saved locally on the Mac:

```text
tools/
external/aromadr/
aromadr-java-test-repair-mvp/.mvp_runs/
rendered_proposal/
demo_mcp/
```

Meaning:

- `tools/` had local Maven/Docker downloads.
- `external/aromadr/` had the AromaDr GitHub clone.
- `.mvp_runs/` had benchmark outputs and repair artifacts.
- These are not required in GitHub and should not be committed.

On Windows, these will need to be recreated if needed.

## 6. Windows Setup Checklist

Install:

1. Git
2. Java 17+
3. Python 3.10+ or 3.11+
4. Maven
5. Docker Desktop

Recommended checks in PowerShell:

```powershell
git --version
java -version
python --version
mvn -version
docker --version
```

Clone the project:

```powershell
git clone https://github.com/AlanX-Yan/Agentic-test-repair.git
cd Agentic-test-repair\aromadr-java-test-repair-mvp
```

If Maven is not globally available, either install Maven globally or set:

```powershell
$env:MAVEN_BIN="C:\path\to\apache-maven\bin\mvn.cmd"
```

## 7. Running AromaDr on Windows

Use Docker:

```powershell
docker run -d --name aromadr -p 3000:3000 -p 8000:8000 publioblenilio/aromadr
```

If the container already exists but is stopped:

```powershell
docker start aromadr
```

Check:

```powershell
docker ps --filter name=aromadr
curl http://localhost:3000
```

The root URL may return `Cannot GET /`; that is okay. The API used by the
project is:

```text
http://localhost:3000/file-test-smells/detect
```

## 8. Run Commands on Windows

From:

```powershell
cd Agentic-test-repair\aromadr-java-test-repair-mvp
```

Run default MVP demo:

```powershell
python -m test_repair_mvp
```

Run benchmark without real AromaDr:

```powershell
python -m test_repair_mvp --benchmark demo/config/benchmark.json --run-dir .mvp_runs/benchmark
```

Run benchmark with real AromaDr:

```powershell
$env:AROMADR_API_URL="http://localhost:3000"
python -m test_repair_mvp --benchmark demo/config/benchmark.json --run-dir .mvp_runs/benchmark-aromadr
```

Run Maven dataset scanner on sample dataset:

```powershell
python -m test_repair_mvp --scan-dataset demo/dataset_sample --dataset-report-dir .mvp_runs/dataset-scan-sample
```

Run Maven dataset scanner with AromaDr:

```powershell
$env:AROMADR_API_URL="http://localhost:3000"
python -m test_repair_mvp --scan-dataset demo/dataset_sample --dataset-report-dir .mvp_runs/dataset-scan-sample-aromadr
```

For a very large dataset such as DataTD, start with a smaller subset first:

```powershell
python -m test_repair_mvp --scan-dataset C:\path\to\DataTD_subset --dataset-report-dir .mvp_runs\datatd-subset-scan
```

If Maven checks are too slow, do a quick structure-only scan first:

```powershell
python -m test_repair_mvp --scan-dataset C:\path\to\DataTD_subset --dataset-report-dir .mvp_runs\datatd-quick-scan --dataset-skip-maven
```

## 9. Important DataTD Notes

DataTD is expected to be large. Do not start by running the full dataset.

Because DataTD is around 30GB, the current recommendation is to first use the
curated Maven project workflow:

```powershell
cd Agentic-test-repair\aromadr-java-test-repair-mvp
python scripts\prepare_curated_maven_dataset.py --tier starter --limit 2
python -m test_repair_mvp --scan-dataset ..\datasets\curated_maven --dataset-report-dir .mvp_runs\curated-maven-scan --dataset-maven-strategy fast --dataset-candidate-mode test-compile --dataset-maven-repo ..\datasets\.m2\repository --dataset-timeout-seconds 600
```

With AromaDr:

```powershell
$env:AROMADR_API_URL="http://localhost:3000"
python -m test_repair_mvp --scan-dataset ..\datasets\curated_maven --dataset-report-dir .mvp_runs\curated-maven-scan-aromadr --dataset-maven-strategy fast --dataset-candidate-mode test-compile --dataset-maven-repo ..\datasets\.m2\repository --dataset-timeout-seconds 600
```

The curated starter set currently includes:

```text
commons-cli
commons-codec
commons-csv
commons-io
commons-lang
commons-text
```

Recommended approach:

1. Ask Professor Fazzini for access or usage instructions.
2. Copy or select a small subset first, for example 5 to 10 Maven projects.
3. Run scanner with `--dataset-skip-maven` to check project/test discovery.
4. Run scanner normally on the subset to check compile/test viability.
5. Run scanner with AromaDr to identify smelly test files.
6. Inspect `candidate_tests.csv`.
7. Convert selected candidates into repair tasks.
8. Scale to more projects only after the subset works.

Why this matters:

- Large Maven datasets can take a long time.
- Some projects may require old Java versions.
- Some projects may need external services, databases, or special profiles.
- Some tests may be flaky or too slow.
- Some projects may not compile anymore.

## 10. Next Development Steps

Recommended order:

1. Get DataTD access from Professor Fazzini.
2. Run the dataset scanner on a small DataTD subset.
3. Add a converter from `candidate_tests.csv` to repair task JSON files.
4. Run the existing repair loop on selected real Maven test files.
5. Replace deterministic repair templates with a real coding-agent backend.
6. Add evaluation metrics:
   - compile rate
   - test pass rate
   - smell reduction
   - repair success rate
   - optional coverage with JaCoCo
   - optional mutation score with PIT
7. Expand benchmark size.
8. Prepare progress report or oral update for Professor Fazzini.

## 11. Known Limitations

- The current repair agent is deterministic and template-based.
- The scanner identifies candidate files but does not yet automatically create
  repair task configs from dataset rows.
- Large Maven datasets need batching and timeouts.
- Some Maven projects may require specific JDK versions or Maven profiles.
- The local fallback detector is only for development convenience; AromaDr
  should be used for real experiment results.

## 12. Files to Read First on Windows

Start with:

```text
README.md
aromadr-java-test-repair-mvp/README.md
aromadr-java-test-repair-mvp/docs/ARCHITECTURE.md
aromadr-java-test-repair-mvp/docs/AROMADR_INTEGRATION.md
aromadr-java-test-repair-mvp/docs/DATASET_SCANNING.md
```

Then inspect:

```text
aromadr-java-test-repair-mvp/test_repair_mvp/dataset_scanner.py
aromadr-java-test-repair-mvp/test_repair_mvp/detectors.py
aromadr-java-test-repair-mvp/test_repair_mvp/harness.py
aromadr-java-test-repair-mvp/test_repair_mvp/agents.py
```

## 13. Short Summary

The project is currently past the MVP stage:

- Java/JUnit direction is set.
- AromaDr is integrated.
- Repair loop works on demo tasks.
- Benchmark shows smell reduction from 15 to 0.
- Maven dataset scanner is implemented and pushed.
- The next major step is using DataTD or another Maven dataset for extended
  experiments.
