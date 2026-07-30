# DeepSeek V2 Extension Evaluation Protocol

Protocol version: `deepseek-v2`

Freeze date: 2026-07-30

## Purpose and Scope

This protocol defines an independent extension of the completed
`deepseek-v1` held-out evaluation. The intended extension was 33 new eligible
candidates, bringing the formal total from 17 to 50.

Strict baseline screening found 26 additional eligible candidates. The frozen
extension therefore contains 26 candidates, and the combined formal
evaluation can contain 43 candidates. Candidates that fail a clean baseline
compile or test run are not relabelled as eligible to reach the requested
sample size.

No DeepSeek response or repair outcome was used to select this cohort.

## Cohort Freeze

- Extension candidates: 26
- Projects represented: 10
- Overlap with the 17 `deepseek-v1` candidates: 0
- Duplicate project/test-file identities inside v2: 0
- JDK 21 run group: 24 candidates
- JDK 11 run group: 2 candidates
- Development candidates remain excluded from all formal metrics
- Cohort CSV SHA-256:
  `7557da38127218fcc8f30761eafa8897cc0528d00809a3c4e96b4f20038d4c72`
- Path-neutral manifest SHA-256:
  `f78951d061e50275ada654ef57d5b3ac208a5d5218ae9341ee79bc9ef2a2be50`
- JDK 21 input CSV SHA-256:
  `542f4401b225279d35b7de561534259dd6741eb46c2e81ac05a29faf9ff883d8`
- JDK 11 input CSV SHA-256:
  `52a9f296114f0120ef818198394bce2d68381b2f3e7a772d7161cc9727a2965b`

The ignored runtime artifacts are under
`.mvp_runs/deepseek-v2-cohort/`. The manifest contains project IDs, relative
test paths, source hashes, and baseline AromaDr smell types; it contains no
API key or absolute DataTD path.

## Screening Evidence

The full extracted DataTD corpus contains 1,070 project snapshots. Screening
was expanded across the original candidate pool and additional Java 17,
Java 11, source-complete, source-partial, medium, large, and nested-module
pools. Most snapshots could not satisfy strict eligibility because production
sources or dependencies needed by their tests were absent, or because clean
baseline tests failed.

The 26 frozen candidates are the union of four baseline-passing groups:

- 12 unused candidates from the original AromaDr pool
- 9 candidates from clean Java 17 projects
- 2 candidates from a clean Java 11 project
- 3 candidates from additional source-complete projects

This is dataset-wide discovery and screening, not a claim that every Java test
file in the 30 GB archive was executed. Build feasibility is established
before any model call.

## Immutable Repair Configuration

The v1 repair semantics remain unchanged:

- Backend: `deepseek`
- Endpoint: OpenAI-compatible DeepSeek Chat Completions API
- Model: `deepseek-v4-pro`
- Thinking mode: enabled for normal repair
- JSON recovery: one non-thinking request after empty or invalid JSON
- Maximum repair attempts: 2
- Maximum output tokens per request: 16,384
- Maven command order: `test-compile`, then `test`
- Maven timeout per command: 600 seconds
- AromaDr endpoint: `/file-test-smells/detect`
- Eligibility: baseline compilation and tests pass, AromaDr is available, and
  at least one authoritative AromaDr finding exists
- Acceptance: repaired test compiles, Maven tests pass, and the authoritative
  AromaDr count is zero
- Authorized write scope: one isolated Java test file
- Rejected or exceptional proposal: snapshot and rollback
- Original DataTD project: read-only and hash-verified

System prompt SHA-256:
`8e63d9877749dad02be9cadf866a8d53060e9a85a885c99891b186aaa8eca6ab`.

The v2 label identifies a new frozen cohort and run environment; it does not
authorize prompt tuning against v1 outcomes.

## Budget Boundary

The user authorized at most CNY 30 of new DeepSeek API cost. Formal commands
use a combined conservative cap of USD 4.00:

- JDK 21 group: USD 3.50
- JDK 11 group: USD 0.50

The runner reserves cost before each request and stops before the configured
USD cap would be exceeded. Actual provider-estimated cost, token counts, and
call counts must be reported. If the USD caps could no longer remain within
CNY 30 at execution time, the run must stop before the first request.

## Formal Run Groups

Both groups use the same external Maven repository at
`$env:USERPROFILE\.m2\deepseek-v2-repository`; the path is recorded in raw
environment evidence but removed from publishable artifacts.

```powershell
python -m test_repair_mvp `
  --repair-candidates .mvp_runs\deepseek-v2-cohort\jdk21_candidates.csv `
  --repair-output-dir .mvp_runs\heldout-evaluation-deepseek-v2-jdk21 `
  --repair-maven-repo "$env:USERPROFILE\.m2\deepseek-v2-repository" `
  --coding-backend deepseek `
  --repair-max-attempts 2 `
  --repair-budget-usd 3.50 `
  --repair-limit 24 `
  --repair-timeout-seconds 600
```

```powershell
$env:JAVA_HOME = "<Temurin 11 directory>"
$env:Path = "$env:JAVA_HOME\bin;$env:Path"
python -m test_repair_mvp `
  --repair-candidates .mvp_runs\deepseek-v2-cohort\jdk11_candidates.csv `
  --repair-output-dir .mvp_runs\heldout-evaluation-deepseek-v2-jdk11 `
  --repair-maven-repo "$env:USERPROFILE\.m2\deepseek-v2-repository" `
  --coding-backend deepseek `
  --repair-max-attempts 2 `
  --repair-budget-usd 0.50 `
  --repair-limit 2 `
  --repair-timeout-seconds 600
```

The API key must be injected from an environment variable and must never be
written to commands, logs, manifests, results, diffs, or documentation.

## Execution Outcome

The valid formal runs completed on 2026-07-30:

- 26/26 candidates passed the frozen eligibility gate
- 24/26 repairs were accepted (92.3%)
- 17 were accepted on the first attempt and 7 after feedback
- 82 authoritative AromaDr findings were reduced to 2
- 35 model calls used 253,810 recorded tokens
- Estimated API cost: USD 0.15097848
- Original DataTD files unchanged: yes

Two pre-runs made zero model calls and are excluded: one used a BOM-encoded
CSV, and one omitted `AROMADR_API_URL`. Their ignored directories remain as
diagnostic evidence and contribute neither candidates nor cost to the formal
result.
