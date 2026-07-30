# DeepSeek V3 100-Candidate Extension Protocol

Protocol version: `deepseek-v3`

Freeze date: 2026-07-31

## Purpose

This protocol defines an independent 57-candidate extension of the completed
v1 and v2 evaluations. The combined formal denominator will be exactly 100:
17 v1 candidates, 26 v2 candidates, and 57 v3 candidates.

The v3 cohort was selected using an advisor-provided DataTD benchmark workbook
that records projects whose tests passed in a recent evaluation, their exact
Git commits, and required Java versions. The workbook is an unpublished local
screening input and is not included in repository artifacts.

No v3 candidate was selected using a DeepSeek response or repair outcome.

## Frozen Cohort

- Candidates: 57
- Projects represented: 23
- Maximum files from one project: 4
- Java 8: 7 candidates
- Java 11: 27 candidates
- Java 17: 23 candidates
- Authoritative AromaDr findings before repair: 227
- Duplicate v3 project/test identities: 0
- Overlap with v1 or v2 project/test identities: 0
- Candidate CSV SHA-256:
  `dfb8e319777a17033d3d9fbcbb0e082c9c57a3cb882a89dc6a70165e3c0e274e3`
- Path-neutral manifest SHA-256:
  `7ed98cfdc141ea39f3d7b885d71bb46be6ec3430b86c54235a22d0b7e81f1570`
- Java 8 input SHA-256:
  `a06caaf55506e2523e07ce1b1f100f4765a82638a7ca13c52f248498c2a2081f`
- Java 11 input SHA-256:
  `9fc3452147c50364664e0fcebbb1c4ff4e03d43c54a8f31385c60f71f2dcc5bb`
- Java 17 input SHA-256:
  `8a8cfcbc17bdd220b509cda39629bb6ddbc556d2f5bff9f70bbddb9397ea658f`

## Eligibility and Source Reconstruction

Each candidate passed all of the following before freeze:

1. The project directory and exact benchmark commit exist locally.
2. A complete isolated working tree was reconstructed from local Git objects
   when the extracted DataTD working tree omitted tracked production files.
3. Maven `test-compile` succeeds under the benchmark Java version.
4. The complete Maven test command succeeds.
5. AromaDr is available and reports at least one authoritative finding.
6. The same checks succeed again in the candidate-level isolated copy.
7. The original DataTD working tree remains unchanged.

## Immutable Repair Configuration

- Backend: `deepseek`
- Model: `deepseek-v4-pro`
- Endpoint: OpenAI-compatible DeepSeek Chat Completions API
- Thinking mode: enabled for normal repair
- JSON recovery: one non-thinking request after empty or invalid JSON
- Maximum repair attempts: 2
- Maximum output tokens per request: 16,384
- Maven command order: `test-compile`, then `test`
- Maven timeout per command: 900 seconds
- AromaDr endpoint: `/file-test-smells/detect`
- Acceptance: compilation succeeds, all Maven tests pass, and authoritative
  AromaDr findings equal zero
- Authorized write scope: one isolated Java test file
- Rejected or exceptional proposal: snapshot and rollback
- Original DataTD source: read-only and hash-verified

System prompt SHA-256:
`8e63d9877749dad02be9cadf866a8d53060e9a85a885c99891b186aaa8eca6ab`.

The prompt, feedback semantics, two-attempt rule, and acceptance gate are
unchanged from v1 and v2.

## Context Sent to DeepSeek

For each frozen candidate, requests may include:

- the complete authorized test file
- repair feedback and AromaDr findings
- up to 40,000 characters of the module `pom.xml`
- up to 100,000 characters of read-only `src/main/java` production context

No API key, absolute local path, raw request authorization header, benchmark
workbook, unrelated test project, or original mutable DataTD directory is
included.

## Budget

The user authorized at most CNY 50 of new v3 API cost. The three formal runs
use a combined conservative hard cap of USD 6.00:

- Java 8 group: USD 0.75
- Java 11 group: USD 2.75
- Java 17 group: USD 2.50

The runner reserves cost before every request and stops before a group cap
would be exceeded. Actual calls, token counts, provider-estimated cost, and
remaining budget must be reported.

Two zero-cost conditions are explicitly excluded from formal results:

- baseline-only screening and candidate freeze
- startup or infrastructure failures before any model request

## Formal Inputs

Ignored runtime inputs are stored under `.mvp_runs/deepseek-v3-cohort/`:

- `jdk8_candidates.csv`
- `jdk11_candidates.csv`
- `jdk17_candidates.csv`
- `manifest.json`

Publishable results must be path-neutral and secret-free. Only final result
documents and compact CSV/JSON summaries may be pushed to GitHub.

## Execution Outcome

All 57 frozen candidates were executed under this protocol:

| Java group | Candidates | Accepted | Rolled back | Model calls | Tokens | Cost (USD) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Java 8 | 7 | 5 | 2 | 11 | 116,437 | 0.06228205 |
| Java 11 | 27 | 19 | 8 | 42 | 684,553 | 0.35755998 |
| Java 17 | 23 | 22 | 1 | 34 | 557,278 | 0.28265170 |
| **V3 total** | **57** | **46** | **11** | **87** | **1,358,268** | **0.70249373** |

The automated acceptance rate was 80.7%. Twenty-eight candidates succeeded on
the first proposal and 18 after feedback. Three final proposals failed
compilation; every rejected proposal was rolled back. Authoritative AromaDr
findings fell from 227 before repair to 22 in the last proposed versions
(including rejected proposals); every accepted proposal had zero findings.

The v3 run consumed 11.7% of its conservative USD 6.00 hard cap. It remained
well below the user-authorized CNY 50 ceiling.

The path-neutral result files are published under
`docs/results/deepseek-v3/`. Combined v1+v2+v3 results for exactly 100
candidates are under `docs/results/formal-100/`.
