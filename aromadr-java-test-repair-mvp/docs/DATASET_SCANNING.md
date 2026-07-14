# Maven Dataset Scanning

The dataset scanner prepares the project for extended experiments on real Maven
datasets such as DataTD. It scans a directory of Maven projects, checks whether
their tests compile and pass, runs batch test-smell detection on Java test files,
and writes candidate reports for the repair loop.

## Command

From `aromadr-java-test-repair-mvp/`:

```bash
python3 -m test_repair_mvp \
  --scan-dataset demo/dataset_sample \
  --dataset-report-dir .mvp_runs/dataset-scan-sample
```

With real AromaDr running:

```bash
AROMADR_API_URL=http://localhost:3000 python3 -m test_repair_mvp \
  --scan-dataset demo/dataset_sample \
  --dataset-report-dir .mvp_runs/dataset-scan-sample-aromadr
```

For fast structure-only scans that skip Maven execution:

```bash
python3 -m test_repair_mvp \
  --scan-dataset /path/to/maven/dataset \
  --dataset-skip-maven
```

## Outputs

The scanner writes:

- `dataset_scan_summary.json`: aggregate counts and smell-type distribution.
- `projects.csv`: one row per Maven project.
- `test_files.csv`: one row per Java test file.
- `candidate_tests.csv`: test files that compile, pass, and contain smells.
- `dataset_candidate_report.md`: Markdown summary for quick inspection.

## Candidate Rule

A test file is currently marked as a repair candidate when:

1. Its project contains a `pom.xml`.
2. The project has Java test files under `src/test/java`.
3. `mvn test-compile` succeeds.
4. `mvn test` succeeds.
5. The detector reports at least one smell.

When `AROMADR_API_URL` is set and reachable, the scanner uses AromaDr through the
same detector adapter as the repair loop. If AromaDr is unavailable, it falls
back to the lightweight local detector so dataset plumbing can still be tested.
