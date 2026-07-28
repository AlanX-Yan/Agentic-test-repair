# Curated Maven Dataset

Use this path before downloading a very large dataset such as DataTD. The goal
is to get high-quality early experiment results from real Java/Maven projects
that are smaller, easier to inspect, and easier to debug.

## Why This Dataset First

DataTD is useful, but it is large. A curated Maven dataset lets us validate the
full experimental pipeline first:

```text
clone real Maven projects
-> check mvn test-compile
-> check mvn test
-> run AromaDr batch smell detection
-> generate candidate_tests.csv
-> choose repair targets
```

Once this works on 5 to 10 projects, the same scanner can scale to DataTD or a
DataTD subset.

## Prepare Projects

From `aromadr-java-test-repair-mvp/`:

```bash
python3 scripts/prepare_curated_maven_dataset.py --tier starter
```

On Windows PowerShell:

```powershell
python scripts\prepare_curated_maven_dataset.py --tier starter
```

By default, projects are cloned into:

```text
../datasets/curated_maven/
```

This directory is ignored by Git because the cloned projects and Maven caches
can become large.

## Start Small

Clone only two projects first:

```bash
python3 scripts/prepare_curated_maven_dataset.py --tier starter --limit 2
```

Clone specific projects:

```bash
python3 scripts/prepare_curated_maven_dataset.py --only commons-cli --only commons-codec
```

## Scan Without AromaDr

```bash
python3 -m test_repair_mvp \
  --scan-dataset ../datasets/curated_maven \
  --dataset-report-dir .mvp_runs/curated-maven-scan \
  --dataset-maven-strategy fast \
  --dataset-candidate-mode test-compile \
  --dataset-timeout-seconds 600
```

## Scan With AromaDr

Start AromaDr:

```bash
docker start aromadr
```

Or create the container if needed:

```bash
docker run -d --name aromadr -p 3000:3000 -p 8000:8000 publioblenilio/aromadr
```

Then scan:

```bash
AROMADR_API_URL=http://localhost:3000 python3 -m test_repair_mvp \
  --scan-dataset ../datasets/curated_maven \
  --dataset-report-dir .mvp_runs/curated-maven-scan-aromadr \
  --dataset-maven-strategy fast \
  --dataset-candidate-mode test-compile \
  --dataset-timeout-seconds 600
```

On Windows PowerShell:

```powershell
$env:AROMADR_API_URL="http://localhost:3000"
python -m test_repair_mvp --scan-dataset ..\datasets\curated_maven --dataset-report-dir .mvp_runs\curated-maven-scan-aromadr
```

The scanner uses a shared Maven local repository under the report directory by
default. This avoids redownloading the same dependencies for every project. For
a persistent cache across runs, provide one explicitly:

```bash
python3 -m test_repair_mvp \
  --scan-dataset ../datasets/curated_maven \
  --dataset-report-dir .mvp_runs/curated-maven-scan \
  --dataset-maven-strategy fast \
  --dataset-candidate-mode test-compile \
  --dataset-maven-repo ../datasets/.m2/repository \
  --dataset-timeout-seconds 600
```

`--dataset-maven-strategy fast` uses direct Maven plugin goals for screening
instead of the full Maven lifecycle. This avoids project governance checks such
as RAT, build-plan checks, javadoc, and release checks that are not relevant to
test-smell candidate selection.

For curated discovery, `--dataset-candidate-mode test-compile` is recommended.
It marks a file as a candidate when its project test sources compile and the
file has smells. After that smaller candidate set is identified, selected files
can be checked with stricter full test execution.

For very quick discovery, skip Maven first:

```bash
python3 -m test_repair_mvp \
  --scan-dataset ../datasets/curated_maven \
  --dataset-report-dir .mvp_runs/curated-maven-quick-scan \
  --dataset-skip-maven
```

## Current Project List

Starter projects:

- `apache/commons-cli`
- `apache/commons-codec`
- `apache/commons-csv`
- `apache/commons-io`
- `apache/commons-lang`
- `apache/commons-text`

Extended projects:

- `apache/commons-collections`
- `apache/commons-compress`
- `google/gson`
- `JodaOrg/joda-time`

## Reports To Inspect

After scanning, inspect:

```text
.mvp_runs/curated-maven-scan-aromadr/dataset_candidate_report.md
.mvp_runs/curated-maven-scan-aromadr/candidate_tests.csv
.mvp_runs/curated-maven-scan-aromadr/projects.csv
```

The most important file is `candidate_tests.csv`; it tells us which test files
compile, pass, and contain smells worth repairing.
