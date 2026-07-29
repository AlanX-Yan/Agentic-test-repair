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

For real open-source projects, use a longer timeout and a shared Maven cache:

```bash
python3 -m test_repair_mvp \
  --scan-dataset /path/to/maven/dataset \
  --dataset-report-dir .mvp_runs/dataset-scan \
  --dataset-maven-strategy fast \
  --dataset-candidate-mode test-compile \
  --dataset-maven-repo /path/to/shared/.m2/repository \
  --dataset-timeout-seconds 600
```

## Outputs

The scanner writes:

- `dataset_scan_summary.json`: aggregate counts and smell-type distribution.
- `projects.csv`: one row per Maven project.
- `test_files.csv`: one row per Java test file, including separate AromaDr and
  lightweight counts, types, and candidate flags.
- `candidate_tests.csv`: test files that compile, pass, and contain smells.
- `dataset_candidate_report.md`: Markdown summary for quick inspection.

The summary preserves combined detector fields for backward compatibility and
also reports source-specific fields:

- `aromadr_total_smells`, `aromadr_smell_types`,
  `aromadr_smelly_test_file_count`, and `aromadr_candidate_test_count`
- `lightweight_total_smells`, `lightweight_smell_types`,
  `lightweight_smelly_test_file_count`, and
  `lightweight_candidate_test_count`

For advisor-facing DataTD results and repair-subset selection, use the
AromaDr-only fields. The combined fields describe the complete configured
detector pipeline and may include additional local heuristic findings.

## Candidate Rule

By default, a test file is marked as a repair candidate when:

1. Its project contains a `pom.xml`.
2. The project has Java test files under `src/test/java`.
3. `mvn test-compile` succeeds.
4. `mvn test` succeeds.
5. The detector reports at least one smell.

For large or noisy real-world datasets, use:

```text
--dataset-candidate-mode test-compile
```

This marks files as candidates when their project tests compile and at least one
smell is detected, even if the full test command needs additional per-project
configuration.

When `AROMADR_API_URL` is set and reachable, the scanner uses AromaDr through the
same detector adapter as the repair loop. If AromaDr is unavailable, it falls
back to the lightweight local detector so dataset plumbing can still be tested.

When AromaDr is available, the current composite detector keeps both AromaDr
and lightweight findings. In `test_files.csv`, `aromadr_candidate=True` means
the file satisfies the selected Maven candidate mode and has at least one
AromaDr finding. This is the recommended filter for repair evaluation.

The repair adapter applies a stricter runtime gate: DeepSeek is called only
when the isolated baseline compiles, passes tests, reaches AromaDr, and has at
least one AromaDr finding. AromaDr findings are then authoritative for repair
feedback and acceptance.

`projects.csv` also records Maven return codes and short problem labels. A
return code of `124` means the Maven command timed out.
