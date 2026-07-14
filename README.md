# Agentic Test Repair

Goal-driven repair of agent-generated Java tests using AromaDr test-smell feedback.

This repository contains an early research prototype developed for a Java/JUnit test-smell project. The direction follows Professor Mattia Fazzini's suggestion to focus on Java programs and to use AromaDr, a language-independent test smell detector, as the primary quality signal.

## What This Prototype Does

The prototype implements a full repair loop:

1. Generate Java/JUnit tests for a target class.
2. Compile and run the generated tests.
3. Send the generated tests to AromaDr for test-smell detection.
4. Let a master evaluator decide whether the tests satisfy the goal.
5. Convert build failures and smell reports into repair feedback.
6. Repair the tests and repeat until the criteria are met or the iteration budget is exhausted.
7. Produce before/after benchmark reports.

## Current Result

With AromaDr running locally through Docker:

```text
Tasks: 3
Accepted: 3
Initial smells: 15
Final smells: 0
Smell delta: 15
Initial passed: 2
Final passed: 3
```

The current deterministic repair logic handles the AromaDr smells observed in the demo benchmark:

- `UnknownTest`
- `MagicNumberTest`
- `AssertionRoulette`
- `ExceptionHandling`

The repository also includes a Maven dataset scanner for extended experiments.
It scans Maven projects, checks whether tests compile and pass, batch-runs
test-smell detection, and produces candidate repair reports.

## Repository Layout

```text
aromadr-java-test-repair-mvp/
  test_repair_mvp/        Python orchestration code
  demo/                   Java/JUnit demo and benchmark projects
  docs/                   Architecture and AromaDr integration notes
  scripts/                Convenience run scripts

docs/proposal/
  Goal-Driven_Test_Repair_Proposal_Improved.docx
  Goal-Driven_Test_Repair_Proposal_Improved.html
  build_improved_proposal.py
```

Large local tools and third-party clones are intentionally not committed:

- `tools/` contains local Maven/Docker downloads.
- `external/aromadr/` contains the cloned AromaDr repository.

## Prerequisites

- Java 17+.
- Maven. This project was tested with Apache Maven 3.9.16.
- Docker Desktop if you want to run the real AromaDr service.
- AromaDr service running at `http://localhost:3000`.

Clone AromaDr separately when needed:

```bash
git clone https://github.com/publiosilva/aromadr.git external/aromadr
```

Start AromaDr with Docker:

```bash
docker run -d --name aromadr -p 3000:3000 -p 8000:8000 publioblenilio/aromadr
```

## Run The Prototype

Run the local benchmark with the lightweight fallback detector:

```bash
cd aromadr-java-test-repair-mvp
python3 -m test_repair_mvp --benchmark demo/config/benchmark.json --run-dir .mvp_runs/benchmark
```

Run the benchmark with real AromaDr:

```bash
cd aromadr-java-test-repair-mvp
AROMADR_API_URL=http://localhost:3000 scripts/run_benchmark_with_aromadr.sh
```

Scan a Maven dataset and generate candidate reports:

```bash
cd aromadr-java-test-repair-mvp
AROMADR_API_URL=http://localhost:3000 python3 -m test_repair_mvp --scan-dataset demo/dataset_sample --dataset-report-dir .mvp_runs/dataset-scan-sample-aromadr
```

Reports are written under:

```text
aromadr-java-test-repair-mvp/.mvp_runs/
```

Those generated reports are useful locally, but they are not committed to keep the repository clean.

## Documentation

- [MVP README](aromadr-java-test-repair-mvp/README.md)
- [Architecture](aromadr-java-test-repair-mvp/docs/ARCHITECTURE.md)
- [AromaDr Integration](aromadr-java-test-repair-mvp/docs/AROMADR_INTEGRATION.md)
- [Dataset Scanning](aromadr-java-test-repair-mvp/docs/DATASET_SCANNING.md)
- [Proposal HTML](docs/proposal/Goal-Driven_Test_Repair_Proposal_Improved.html)

## Next Steps

- Replace the deterministic template repair agent with a real coding-agent backend.
- Use the dataset scanner to evaluate DataTD or another Maven project dataset.
- Add JaCoCo coverage metrics.
- Add PIT mutation score as a stretch evaluation metric.
- Expand repair strategies as more AromaDr smell categories appear.
