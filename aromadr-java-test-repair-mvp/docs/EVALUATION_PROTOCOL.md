# Frozen Held-Out Evaluation Protocol

Protocol version: `deepseek-v1`

Freeze date: 2026-07-30

## Purpose

This document freezes the configuration used after the development cohort.
Candidates 1–10 of the fixed subset are development-only and must not be
included in the held-out repair success rate.

## Immutable Repair Configuration

- Backend: `deepseek`
- Provider endpoint: OpenAI-compatible DeepSeek Chat Completions
- Model: `deepseek-v4-pro`
- Thinking mode: enabled for normal repair
- JSON recovery: one non-thinking request only after empty/invalid JSON
- Maximum repair attempts: 2
- Maximum output tokens per request: 16,384
- Maven command order: `test-compile`, then `test`
- Maven timeout per command: 600 seconds
- AromaDr endpoint: `/file-test-smells/detect`
- Eligibility:
  - baseline test compilation succeeds
  - baseline Maven tests pass
  - AromaDr is available
  - at least one AromaDr finding exists
- Acceptance:
  - repaired test compiles
  - Maven tests pass
  - authoritative AromaDr count is 0
- Lightweight findings: diagnostic only when AromaDr is available
- Authorized write scope: one isolated Java test file
- Rejected/exceptional proposal: snapshot and rollback
- Original DataTD project: read-only and hash-verified

## API Reliability and Budget Policy

- A shared `--repair-budget-usd` is required for formal runs.
- A request is rejected before execution if its conservative reservation would
  exceed the remaining budget.
- HTTP 429/500/502/503 and network timeouts receive at most two retries with
  bounded exponential backoff.
- API keys and authorization headers are never written to artifacts.

## Frozen Hashes

- System prompt SHA-256:
  `8e63d9877749dad02be9cadf866a8d53060e9a85a885c99891b186aaa8eca6ab`
- `agents.py` SHA-256 at freeze:
  `a8aa2f09976e08465f4a016bbd69d4791d8e5758356a8e98bed2248eb2db4faa`
- `feedback.py` SHA-256 at freeze:
  `5329e4f7dbd951fe812c15168b93f77186b4fcc342eef35528fd54aac2254429`
- Fixed subset CSV SHA-256:
  `27be45dbe9f889b1f699becade841eb9277dbfd9de58fc890a8fa2b3bc261f2f`

File hashes include implementation details and may change for
infrastructure-only fixes. The system prompt, evaluator semantics, eligibility,
attempt limit, and acceptance rules must not change after held-out API calls
begin. Any unavoidable infrastructure change must be documented with old/new
hashes and must not use held-out outcome content for prompt tuning.

## Cohort Separation

- Development rows: fixed subset offsets 0–9
- Held-out baseline pool: fixed subset offsets 10–39
- Replacement pool: unused rows from the original 83 AromaDr candidates,
  selected deterministically if the fixed held-out pool yields fewer than 15
  eligible tests

## Formal Run Template

```powershell
python -m test_repair_mvp `
  --repair-candidates .mvp_runs\datatd-repair-subset\candidate_subset.csv `
  --repair-output-dir .mvp_runs\heldout-<batch> `
  --repair-maven-repo ..\datatd\.m2\repository `
  --coding-backend deepseek `
  --repair-max-attempts 2 `
  --repair-budget-usd <approved-budget> `
  --repair-offset <offset> `
  --repair-limit <count> `
  --repair-timeout-seconds 600
```

The held-out list must be fixed from baseline-only results before replacing
`template` with `deepseek`.
