# DataTD Results

Date: 2026-07-31

## Scope

This project uses a controlled sample from DataTD rather than claiming a full
30 GB, all-project evaluation. The final formal sample contains 100 strictly
eligible candidates across three independently frozen protocols. A 40-project
Windows batch initially produced 83
AromaDr-eligible candidate rows. A deterministic 40-file subset covered all ten
observed AromaDr smell types and limited each project to at most two files.

The first ten subset rows were development data. Candidates 11–40 were screened
without API calls. Because they produced only 11 eligible tests, six additional
eligible replacements were selected deterministically from unused rows in the
83-candidate pool. This formed the 17-test v1 cohort. V2 added 26 candidates.
V3 used an advisor-provided benchmark list, exact benchmark commits, and
advisor-specified Java versions to add 57 more candidates.

The advisor workbook itself is a local screening input and is not published.
When extracted DataTD directories omitted tracked production files, complete
isolated worktrees were reconstructed from the exact local Git commit before
baseline validation.

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

## Final Combined Cohort

| Metric | Result |
| --- | ---: |
| Eligible repair attempts | 100 |
| Accepted | 85 |
| Rejected and rolled back | 15 |
| Success rate | 85.0% |
| First-attempt accepted | 55 |
| Feedback-retry accepted | 30 |
| Initial AromaDr findings | 484 |
| Findings in last proposals | 30 |
| Model calls | 146 |
| Tokens | 1,838,056 |
| Estimated API cost | USD 0.99152858 |
| Original DataTD files changed | 0 |

The v3 extension spans Java 8, 11, and 17 and contributes 57 candidates from
23 project/module IDs. Compact path-neutral v3 and combined results are in
`docs/results/deepseek-v3/` and `docs/results/formal-100/`.

All 30 remaining findings were measured in proposals that failed the frozen
gate and were subsequently rolled back; accepted proposals had zero findings.

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
