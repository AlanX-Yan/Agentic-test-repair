# DataTD Windows Pilot Scan Report

Date: 2026-07-29

## Scope

This run validated the DataTD scanner on Windows without starting a full
dataset Maven scan. The full DataTD structure was scanned with Maven disabled,
then eight small, single-module Maven projects were selected for a pilot.

DataTD was supplied as a 31.03 GiB `projects.zip` archive containing 1,070
project directories. The scan root after local extraction was:

```text
<workspace>\datatd\datatd\projects
```

The archive contains 1,070 non-`target` `pom.xml` files and approximately
27,638 Java files below `src/test/java`. On the Windows filesystem, 27,634 were
extractable; 20,024 matched the scanner's `Test.java`, `Tests.java`, or
`TestCase.java` filename rule.

## Environment

- Windows 11, amd64
- Python 3.12.9
- Eclipse Temurin JDK 17.0.19
- Apache Maven 3.9.16
- Git 2.53.0.windows.2
- Docker Desktop 29.6.2 with the Linux/WSL 2 backend
- AromaDr Docker image: `publioblenilio/aromadr:latest`
- AromaDr API: available at `http://localhost:3000`; a Java/JUnit detection
  request returned HTTP 200

## Structure-Only Scan

Command parameters:

```text
--scan-dataset ..\datatd\datatd\projects
--dataset-report-dir .mvp_runs\datatd-structure-scan
--dataset-skip-maven
```

Results:

- Maven projects/modules scanned: 1,070
- Projects/modules with Java tests: 1,045
- Test files scanned: 19,902
- Maven compile/test metrics: not run
- AromaDr available files: 0

All five required local artifacts were generated:
`dataset_scan_summary.json`, `projects.csv`, `test_files.csv`,
`candidate_tests.csv`, and `dataset_candidate_report.md`.

## AromaDr and Maven Pilot

The pilot used eight small, single-module projects with Java 8, 11, or 17
metadata:

1. `marcellogpassos-hierarchical-data-structures`
2. `webcompere-completable-future-retry`
3. `idealo-logstash-logback-http`
4. `coffeelibs-jextract-maven-plugin`
5. `AugustoRavazoli-termenu`
6. `Mercateo-test-clock`
7. `cube8540-validator-core`
8. `gabrie-allaigre-guice-tools`

Command parameters:

```text
AROMADR_API_URL=http://localhost:3000
--scan-dataset ..\datatd\datatd-pilot-source
--dataset-report-dir .mvp_runs\datatd-pilot-aromadr
--dataset-maven-strategy fast
--dataset-candidate-mode test-compile
--dataset-maven-repo ..\datatd\.m2\repository
--dataset-timeout-seconds 600
```

Results:

- Maven projects/modules scanned: 8
- Projects/modules with Java tests: 8
- Projects/modules where tests compile: 7
- Projects/modules where tests pass: 6
- Maven timeouts: 0
- Test files scanned: 22
- Smelly test files: 21
- Repair candidates: 13
- Total smell findings: 137
- AromaDr available files: 22
- Detector: `AromaDr+lightweight` for all 22 files

Source-specific results:

- AromaDr-only findings: 91
- AromaDr-only smelly test files: 19
- AromaDr-only repair candidates: 13
- Lightweight-only findings: 46
- Lightweight-only smelly test files: 16
- Lightweight-only repair candidates: 10

Smell distribution from the configured composite detector:

- `UnknownTest`: 53
- `AssertionRoulette`: 34
- `MissingAssertion`: 31
- `ExcessiveMocking`: 15
- `SleepyTest`: 2
- `ExceptionHandling`: 1
- `IgnoredTest`: 1

The scanner intentionally combines AromaDr findings with the local lightweight
checks, so the 137 total is the configured `AromaDr+lightweight` result rather
than a pure AromaDr-only count. AromaDr itself was available for every file.

## Second-Stage 40-Project Batch

After validating source-specific metrics on the eight-project pilot, a separate
batch of 40 small, single-module DataTD projects was selected. The first pilot
projects were excluded. Selection was stratified using DataTD's Java metadata:
14 Java 8 projects, 14 Java 11 projects, and 12 Java 17 projects. Each selected
project had 1-10 scanner-eligible test files.

The batch reused the same settings:

```text
AROMADR_API_URL=http://localhost:3000
--scan-dataset ..\datatd\datatd-batch40-source
--dataset-report-dir .mvp_runs\datatd-batch40-aromadr
--dataset-maven-strategy fast
--dataset-candidate-mode test-compile
--dataset-maven-repo ..\datatd\.m2\repository
--dataset-timeout-seconds 600
```

Results:

- Maven projects/modules scanned: 40
- Projects/modules with Java tests: 40
- Projects/modules where tests compile: 31
- Projects/modules where tests pass: 23
- Maven timeouts: 0
- Test files scanned: 144
- AromaDr available files: 144
- AromaDr-only smelly test files: 102
- AromaDr-only findings: 807
- AromaDr-only repair candidates: 83
- Lightweight-only smelly test files: 76
- Lightweight-only findings: 200
- Lightweight-only repair candidates: 58
- Combined smelly test files: 115
- Combined findings: 1,007
- Combined repair candidates: 94

AromaDr-only smell distribution:

- `AssertionRoulette`: 408
- `UnknownTest`: 284
- `MagicNumberTest`: 82
- `ConditionalTest`: 6
- `DuplicateAssert`: 6
- `ExceptionHandling`: 6
- `RedundantPrint`: 6
- `EmptyTest`: 4
- `IgnoredTest`: 3
- `SleepyTest`: 2

Build results by DataTD Java-version metadata:

| Java metadata | Projects | Compile | Tests pass |
| --- | ---: | ---: | ---: |
| 8 | 14 | 9 | 3 |
| 11 | 14 | 11 | 10 |
| 17 | 12 | 11 | 10 |

Of the 102 AromaDr-smelly files, 83 became repair candidates. The 19 excluded
files all belonged to projects that failed test compilation. Five compile
failures involved old Lombok annotation processors on JDK 17; other failures
included general compilation errors and an unavailable snapshot dependency.
Eight additional projects compiled but did not pass their tests.

The combined candidate set contained 11 lightweight-only candidates. Future
repair evaluation should therefore filter `candidate_tests.csv` using
`aromadr_candidate=True`, rather than treating every combined candidate as an
AromaDr candidate.

## Problems Found

- The project selected the Unix `mvn` script on Windows. Maven executable
  discovery was updated to use `mvn.cmd`.
- Python discovered paths longer than 260 characters but failed when reading
  them. Detector file reads now use the Windows extended-length path prefix.
- DataTD includes Unix symbolic links under `node_modules/.bin`; Windows tar
  cannot create them. Dataset preparation was completed by extracting the POM
  and test trees, and by excluding irrelevant `node_modules`, `target`, `.git`,
  and `build` trees from pilot extraction.
- `cube8540-validator-core` failed compilation because its Lombok annotation
  processor is incompatible with JDK 17 module access.
- `gabrie-allaigre-guice-tools` compiled, but four tests in
  `ComponentScanTest` errored.
- The published AromaDr image is `linux/arm64/v8` while this machine is amd64.
  Docker Desktop ran it through platform emulation; the API remained available
  for all 22 files.

## Repair Adapter Follow-up

Keep the validated AromaDr container running and scale in controlled batches.
Do not start an unbatched full DataTD Maven scan. Reuse:

```powershell
docker start aromadr
$env:AROMADR_API_URL="http://localhost:3000"
python -m test_repair_mvp `
  --scan-dataset ..\datatd\datatd-pilot-source `
  --dataset-report-dir .mvp_runs\datatd-pilot-aromadr `
  --dataset-maven-strategy fast `
  --dataset-candidate-mode test-compile `
  --dataset-maven-repo ..\datatd\.m2\repository `
  --dataset-timeout-seconds 600
```

A fixed repair subset and CSV-to-repair-loop bridge are now available. The
subset contains 40 files from 29 projects, covers all 10 AromaDr smell types in
the second-stage batch, and limits each project to at most two files.

The original three-candidate run was a historical baseline validation. The
DeepSeek V4 Pro backend has since been integrated behind the same agent
interface. A ten-candidate development cohort produced four strictly eligible
repair attempts; all four compiled, passed tests, and reduced authoritative
AromaDr findings to zero. Original DataTD files remained byte-for-byte
unchanged.

The next research step is to harden budget/resume/reporting controls, freeze the
development configuration, and run candidates not used during prompt
development as a held-out evaluation.
