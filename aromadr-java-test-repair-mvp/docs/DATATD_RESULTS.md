# DataTD Results

Date: 2026-07-30

## Scope

This project uses a controlled sample from DataTD rather than claiming a full
30 GB, all-project evaluation. A 40-project Windows batch produced 83
AromaDr-eligible candidate rows. A deterministic 40-file subset covered all ten
observed AromaDr smell types and limited each project to at most two files.

The first ten subset rows were development data. Candidates 11–40 were screened
without API calls. Because they produced only 11 eligible tests, six additional
eligible replacements were selected deterministically from unused rows in the
83-candidate pool. The final held-out cohort contained 17 tests.

## Dataset Preparation

In the analyzed 40-project batch:

- AromaDr-smelly test files: 102
- AromaDr findings: 807
- AromaDr repair candidates: 83
- Fixed diverse subset: 40 files from 29 projects
- Held-out baseline pool: subset candidates 11–40
- Frozen held-out repair cohort: 17 candidates from 11 projects

Candidate eligibility was stricter at execution time:

1. Maven `test-compile` succeeds.
2. Maven `test` succeeds.
3. AromaDr is reachable.
4. The candidate contains at least one AromaDr finding.

## Development Cohort

The first ten fixed-subset candidates were used to stabilize the runner:

| Metric | Result |
| --- | ---: |
| Screened | 10 |
| Baseline compiled | 8 |
| Eligible | 4 |
| Accepted repairs | 4 |
| AromaDr findings | 136 to 0 |
| Model calls | 6 |
| Recorded tokens | 93,651 |
| Estimated cost | USD 0.0606 |

These results are not included in the held-out success rate.

## Held-Out Cohort

The held-out list was frozen before its first DeepSeek call. The path-neutral
manifest records project IDs, relative test paths, source hashes, and smell
types. One candidate was rerun under the unchanged protocol after an outer
30-minute timeout and a resume race contaminated its first infrastructure
record.

| Metric | Result |
| --- | ---: |
| Eligible repair attempts | 17 |
| Accepted | 15 |
| Rejected and rolled back | 2 |
| Success rate | 88.2% |
| First-attempt accepted | 10 |
| Feedback-retry accepted | 5 |
| Compile regressions | 1 |
| Test regressions | 1 |
| Initial AromaDr findings | 175 |
| Final findings in accepted repairs | 0 |
| Model calls | 24 |
| Tokens | 225,978 |
| Estimated API cost | USD 0.1381 |
| Aggregate candidate runtime | 2,193 seconds |
| Original DataTD files changed | 0 |

The two rejected proposals were restored from their original snapshots. Their
failed proposal findings are retained for failure analysis but are not applied
to DataTD or counted as successful smell reduction.

## Reproducibility

- Protocol: `deepseek-v1`
- Model: `deepseek-v4-pro`
- Python: 3.12.9
- Java: 21.0.12
- Maven: 3.9.16 used by the harness
- OS: Windows 11
- Maximum repair attempts: 2
- Formal-run budget cap: USD 1.00
- Actual adjusted held-out cost: approximately USD 0.1381
- AromaDr was authoritative for feedback and acceptance.

Small publishable results are in `docs/results/`. Raw repositories, Maven
caches, API logs, and `.mvp_runs` remain local.
