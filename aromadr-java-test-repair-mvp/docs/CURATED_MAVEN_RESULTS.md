# Curated Maven Results

Date: 2026-07-23

This note summarizes the current curated Maven experiment used as a lightweight
alternative before downloading the much larger DataTD dataset.

## Dataset

The local curated dataset currently contains these repositories:

- `apache/commons-cli`
- `apache/commons-codec`
- `apache/commons-csv`
- `apache/commons-io`
- `apache/commons-lang`
- `apache/commons-text`
- `apache/commons-collections`
- `google/gson`
- `JodaOrg/joda-time`

`gson` is a multi-module Maven repository, so the scanner reports more Maven
projects/modules than repositories.

## Scan Configuration

The scan used:

```bash
AROMADR_API_URL=http://localhost:3000
python3 -m test_repair_mvp \
  --scan-dataset <project> \
  --dataset-maven-strategy fast \
  --dataset-candidate-mode test-compile \
  --dataset-maven-repo ../datasets/.m2/repository \
  --dataset-timeout-seconds 600
```

The projects were scanned individually and then aggregated with:

```bash
python3 scripts/aggregate_dataset_scans.py <scan-dirs> \
  --output-dir .mvp_runs/curated-maven-expanded-aggregate
```

## Aggregate Result

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

## Project-Level Result

| Repository | Test Files | Smelly Files | Repair Candidates | Compile | Tests Pass | Total Smells |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `commons-cli` | 48 | 43 | 43 | yes | yes | 1323 |
| `commons-codec` | 78 | 72 | 72 | yes | yes | 3391 |
| `commons-csv` | 40 | 32 | 32 | yes | yes | 2033 |
| `commons-io` | 247 | 226 | 226 | yes | yes | 9818 |
| `commons-collections` | 300 | 239 | 239 | yes | yes | 11359 |
| `commons-lang` | 321 | 280 | 0 | no | no | 31573 |
| `commons-text` | 101 | 82 | 0 | timeout | no | 6941 |
| `gson` | 134 | 131 | 0 | no | no | 1797 |
| `joda-time` | 2 | 1 | 0 | no | no | 28 |

## Top Smell Types

```text
AssertionRoulette: 40343
MagicNumberTest: 9645
DuplicateAssert: 7104
UnknownTest: 4976
MissingAssertion: 2784
ConditionalTest: 2443
ExceptionHandling: 673
IgnoredTest: 126
EmptyTest: 105
```

## Notes

- This result is already substantially larger than the original 3-task MVP.
- The scan used real AromaDr for all 1271 Java test files.
- 612 candidate repair tests are available from projects whose tests compile
  and pass under the fast Maven screening strategy.
- Some repositories produced smell data but no repair candidates because their
  Maven test compilation did not pass in the current local environment.
- Additional lightweight repositories can still be added, but GitHub downloads
  from China were unstable during this run.

The raw local reports are under:

```text
aromadr-java-test-repair-mvp/.mvp_runs/curated-maven-expanded-aggregate/
```
